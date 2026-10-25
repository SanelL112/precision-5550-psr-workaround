#!/usr/bin/python3
"""Build isolated, signed PSR candidates; require local screen confirmation."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import manager as m
from boot_entry import make_entry
from module_pack import compress_module

BASE = Path('/var/lib/precision-psr-auto')
STATE = BASE / 'status.json'
CANDIDATE = BASE / 'candidate.json'
CONFIRMED = Path('/run/precision-psr-auto-confirmed')
HERE = Path(__file__).resolve().parent
KEY = Path('/etc/pki/akmods/private/private_key.priv')
CERT = Path('/etc/pki/akmods/certs/public_key.der')
TRIAL = 'precision_psr.trial='


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def out(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.chmod(mode)
    tmp.replace(path)


def report(phase, message, **extra):
    save(STATE, dict(phase=phase, message=message, time=time.time(), **extra))
    print(message, flush=True)


def field(text, name):
    return m.entry_field(text, name)


def trial_token(cmdline):
    tokens = [a[len(TRIAL):] for a in cmdline.split() if a.startswith(TRIAL)]
    if not tokens:
        return None
    if len(tokens) != 1 or not re.fullmatch(r'[a-f0-9]{24}', tokens[0]):
        raise ValueError('Invalid trial boot marker')
    return tokens[0]


def clear_trial(text):
    return '\n'.join('options ' + ' '.join(a for a in line.split()[1:] if not a.startswith(TRIAL))
                     if line.startswith('options ') else
                     'title Dell Precision 5550 PSR1 (validated)' if line.startswith('title ') else line
                     for line in text.splitlines()) + '\n'


def inputs(kernel, normal):
    paths = [normal, Path('/boot/initramfs-' + kernel + '.img'), Path('/boot/vmlinuz-' + kernel),
             Path('/etc/kernel/cmdline'), Path('/etc/default/grub'), CERT]
    paths.append(Path(out('modinfo', '-k', kernel, '-n', 'i915')).resolve())
    # Never assemble an image with old NVIDIA binaries while akmods is pending.
    for name in ['nvidia', 'nvidia_modeset', 'nvidia_drm', 'nvidia_uvm']:
        module = Path(out('modinfo', '-k', kernel, '-n', name))
        if out('modinfo', '-F', 'vermagic', module).split()[0] != kernel:
            raise RuntimeError('NVIDIA build is not ready for ' + kernel)
        paths.append(module)
    return {str(p): sha(p) for p in paths}


def verify_source_rpm(path):
    result = subprocess.run(['rpmkeys', '--checksig', '--verbose', str(path)],
                            capture_output=True, text=True, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode or not any('signature' in line.lower() and line.strip().endswith(': OK')
                                    for line in result.stdout.splitlines()):
        raise RuntimeError('Source RPM has no verified signature from the system keyring')


def source_tree(kernel, work):
    srpm = out('rpm', '-q', '--qf', '%{SOURCERPM}', 'kernel-core-' + kernel)
    if not re.fullmatch(r'kernel-[A-Za-z0-9_.+-]+\.src\.rpm', srpm):
        raise RuntimeError('Unexpected Fedora source RPM name')
    cache = BASE / 'sources'
    cache.mkdir(exist_ok=True)
    rpm = cache / srpm
    if not rpm.exists():
        run('dnf', 'download', '--srpm', '--destdir=' + str(cache), 'kernel-core-' + kernel)
    verify_source_rpm(rpm)
    version, release = out('rpm', '-qp', '--qf', '%{VERSION} %{RELEASE}', rpm).split()
    if kernel != version + '-' + release + '.' + os.uname().machine:
        raise RuntimeError('Source package does not match installed kernel')
    archive_name = 'linux-' + version + '.tar.xz'
    rpm_proc = subprocess.Popen(['rpm2cpio', str(rpm)], stdout=subprocess.PIPE)
    try:
        run('cpio', '-id', '--quiet', '--no-absolute-filenames', archive_name, './' + archive_name, cwd=work, stdin=rpm_proc.stdout)
    finally:
        rpm_proc.stdout.close()
    if rpm_proc.wait() != 0:
        raise RuntimeError('Source RPM extraction failed')
    archive = work / archive_name
    if not archive.is_file():
        raise RuntimeError('Expected kernel archive is absent')
    root_name = 'linux-' + version
    run('tar', '-xJf', archive, '-C', work, '--', root_name + '/drivers/gpu/drm/i915',
        root_name + '/drivers/platform/x86/intel_ips.h')
    root = work / root_name
    # No fuzzy application or automated patch editing across incompatible APIs.
    for patch in sorted((HERE / 'patches').glob('*.patch')):
        run('patch', '--batch', '--forward', '--fuzz=0', '-d', root, '-p1', '-i', patch)
    (root / 'include/trace').mkdir(parents=True)
    return root


def prune():
    """Remove only registered, unchanged candidates no longer needed for boot."""
    registry = BASE / 'candidates'
    config = json.loads(m.CONFIG.read_text())
    latest = json.loads(CANDIDATE.read_text()) if CANDIDATE.exists() else {}
    protected = {config['entry'], latest.get('entry')}
    env = out('grub2-editenv', 'list').splitlines()
    protected.update(line.split('=', 1)[1] for line in env if line.startswith(('saved_entry=', 'next_entry=')))
    for record in registry.glob('*.json'):
        data = json.loads(record.read_text())
        if data['entry'] in protected or data['kernel'] == os.uname().release:
            continue
        entry = m.ENTRIES / (data['entry'] + '.conf')
        image = Path(data['image'])
        if any(path.exists() and sha(path) != data['artifacts'].get(str(path)) for path in [entry, image]):
            continue
        entry.unlink(missing_ok=True)
        image.unlink(missing_ok=True)
        record.unlink()


def build(force=False):
    if trial_token(Path('/proc/cmdline').read_text()):
        raise RuntimeError('Confirm or recover the running trial before another build')
    prune()
    config = json.loads(m.CONFIG.read_text())
    stock_id = m.newest_stock()
    normal = m.ENTRIES / (stock_id + '.conf')
    text = normal.read_text()
    kernel = field(text, 'version')
    if not kernel or not re.fullmatch(r'[A-Za-z0-9_.+-]+', kernel):
        raise RuntimeError('Invalid stock kernel version')
    if not force and kernel == config['kernel'] and not m.maintenance_errors(config):
        report('validated', 'Current validated PSR build is intact.', kernel=kernel)
        return
    if not (Path('/usr/src/kernels') / kernel / 'Module.symvers').is_file():
        # Install only the exact development files, never upgrade or replace kernels here.
        run('dnf', '-y', 'install', 'kernel-devel-' + kernel)
    check = subprocess.run(['mokutil', '--test-key', str(CERT)], capture_output=True, text=True,
                           env={**os.environ, 'LC_ALL': 'C'})
    if 'is already enrolled' not in check.stdout:
        raise RuntimeError('Signing certificate needs enrollment; stock boot retained')
    key_public = subprocess.check_output(['openssl', 'pkey', '-in', str(KEY), '-pubout'])
    cert_public = subprocess.check_output(['openssl', 'x509', '-inform', 'DER', '-in', str(CERT), '-pubkey', '-noout'])
    if key_public != cert_public:
        raise RuntimeError('Signing key does not match the enrolled certificate')
    before = inputs(kernel, normal)
    if CANDIDATE.exists() and not force:
        old = json.loads(CANDIDATE.read_text())
        if old['kernel'] == kernel and old['update_inputs'] == before and not m.maintenance_errors(old):
            report('ready', 'A signed PSR candidate is ready for a local screen test.', kernel=kernel, token=old['token'])
            return
    if shutil.disk_usage('/boot').free < 350 * 1024**2:
        raise RuntimeError('Less than 350 MiB free in /boot; stock boot retained')
    report('building', 'Building a matching signed PSR candidate; the existing boot default is unchanged.', kernel=kernel)
    with tempfile.TemporaryDirectory(prefix='build-', dir=BASE) as tmp:
        work = Path(tmp)
        root = source_tree(kernel, work)
        run('make', '-C', '/usr/src/kernels/' + kernel, 'M=' + str(root / 'drivers/gpu/drm/i915'),
            'KCFLAGS=-I' + str(root / 'include/trace'), '-j2', 'modules')
        module = root / 'drivers/gpu/drm/i915/i915.ko'
        if out('modinfo', '-F', 'vermagic', module).split()[0] != kernel:
            raise RuntimeError('Wrong module ABI')
        params = out('modinfo', '-p', module)
        if 'psr_diag_link_standby:' not in params or 'psr_diag:' not in params:
            raise RuntimeError('Missing PSR workaround parameters')
        stock_path = out('modinfo', '-k', kernel, '-n', 'i915')
        if out('modinfo', '-F', 'depends', module) != out('modinfo', '-F', 'depends', stock_path):
            raise RuntimeError('Module dependencies differ from the matching Fedora driver')
        run('strip', '--strip-debug', module)
        run('/usr/src/kernels/' + kernel + '/scripts/sign-file', 'sha256', KEY, CERT, module)
        if not out('modinfo', '-F', 'signer', module):
            raise RuntimeError('Module signing failed')
        token = hashlib.sha256((sha(module) + json.dumps(before, sort_keys=True)).encode()).hexdigest()[:24]
        image = Path('/boot/initramfs-' + kernel + '-psr-auto-' + token + '.img')
        entry_id = stock_id + '-psr-auto-' + token
        entry = m.ENTRIES / (entry_id + '.conf')
        if image.exists() or entry.exists():
            raise RuntimeError('Candidate name already exists; refusing to overwrite a boot image')
        stock_module = Path(out('modinfo', '-k', kernel, '-n', 'i915')).resolve()
        if stock_module.suffix != '.xz':
            raise RuntimeError('Unsupported stock module compression; stock boot retained')
        overlay = work / 'overlay'
        embedded_path = stock_module.relative_to('/')
        target = overlay / embedded_path
        target.parent.mkdir(parents=True)
        target.write_bytes(compress_module(module.read_bytes()))
        # Create image before its BLS entry; no installed stock module is replaced.
        try:
            run('dracut', '--force', '--nostrip', '--force-drivers', 'i915', '--include', overlay, '/', image, kernel)
            embedded = subprocess.check_output(['lsinitrd', '-f', str(embedded_path), str(image)])
            if hashlib.sha256(embedded).hexdigest() != sha(target):
                raise RuntimeError('Staged module differs from the signed build')
            if inputs(kernel, normal) != before:
                raise RuntimeError('Kernel/GPU files changed during the build; retry later')
            content = make_entry(text, '/' + image.name)
            content = content.replace('title Precision 5550 PSR1 link-standby test v2 (4-minute recovery)',
                                      'title Dell Precision 5550 PSR1 update trial')
            content = '\n'.join(line + ' precision_psr.validated=1 ' + TRIAL + token
                                if line.startswith('options ') else line for line in content.splitlines()) + '\n'
            with entry.open('x') as file:
                file.write(content)
            entry.chmod(0o600)
            candidate = dict(kernel=kernel, entry=entry_id, normal_entry=stock_id, certificate=str(CERT),
                             token=token, image=str(image), update_inputs=before,
                             artifacts={str(entry): sha(entry), str(image): sha(image),
                                        '/boot/vmlinuz-' + kernel: sha('/boot/vmlinuz-' + kernel)})
            save(BASE / 'candidates' / (token + '.json'), candidate, 0o600)
            save(CANDIDATE, candidate, 0o600)
        except BaseException:
            entry.unlink(missing_ok=True)
            image.unlink(missing_ok=True)
            raise
    report('ready', 'A signed PSR candidate is ready for a local screen test.', kernel=kernel, token=token)


def candidate():
    data = json.loads(CANDIDATE.read_text())
    errors = m.maintenance_errors(data)
    if errors:
        raise RuntimeError('; '.join(errors))
    return data


def test():
    data = candidate()
    env = out('grub2-editenv', 'list').splitlines()
    if any(line.startswith('next_entry=') and line != 'next_entry=' for line in env):
        raise RuntimeError('Another one-time boot is already selected')
    # GRUB consumes next_entry once; the ordinary default stays stock until confirmed.
    m.set_default(m.newest_stock())
    run('grub2-reboot', data['entry'])
    if 'next_entry=' + data['entry'] not in out('grub2-editenv', 'list').splitlines():
        raise RuntimeError('Could not verify the one-time trial')
    report('scheduled', 'One-time PSR trial selected. Reboot when ready; confirm the screen locally after login.',
           kernel=data['kernel'], token=data['token'])


def watch_unit(config):
    paths = set(config['update_inputs'])
    paths.add(str(CERT.parent))
    for path in list(paths):
        if '/nvidia/' in path:
            paths.add(str(Path(path).parent))
    if any(not re.fullmatch(r'[A-Za-z0-9_./:+-]+', p) for p in paths):
        raise ValueError('Unexpected watched path')
    return ('[Unit]\nDescription=Watch validated PSR update inputs\n'
            'ConditionPathExists=/etc/precision-psr-managed.json\n\n[Path]\n' +
            ''.join('PathChanged=' + p + '\n' for p in sorted(paths)) +
            'Unit=precision-psr-guard.service\n\n[Install]\nWantedBy=multi-user.target\n')


def confirm():
    data = candidate()
    token = trial_token(Path('/proc/cmdline').read_text())
    if token != data['token'] or os.uname().release != data['kernel']:
        raise RuntimeError('Not running the prepared trial')
    mode = Path('/sys/kernel/debug/dri/0000:00:02.0/i915_edp_psr_status').read_text()
    if 'PSR mode: PSR1 enabled' not in mode or 'standby=1' not in mode:
        raise RuntimeError('Expected PSR1 link-standby state is missing')
    # Preserve prior known-good configuration for manual recovery; stock stays untouched.
    backup = BASE / ('previous-config-' + str(time.time_ns()) + '.json')
    shutil.copyfile(m.CONFIG, backup)
    backup.chmod(0o600)
    entry = m.ENTRIES / (data['entry'] + '.conf')
    entry.write_text(clear_trial(entry.read_text()))
    data['artifacts'][str(entry)] = sha(entry)
    data['title'] = 'Dell Precision 5550 PSR1 (validated)'
    save(m.CONFIG, data)
    save(CANDIDATE, data, 0o600)
    save(BASE / 'candidates' / (token + '.json'), data, 0o600)
    unit = Path('/etc/systemd/system/precision-psr-guard.path')
    unit.write_text(watch_unit(data))
    run('systemctl', 'daemon-reload')
    run('systemctl', 'restart', 'precision-psr-guard.path')
    CONFIRMED.touch()
    run('systemctl', 'stop', 'precision-psr-auto-recover.timer')
    m.set_default(data['entry'])
    prune()
    report('validated', 'Screen confirmed. The matching PSR build is now the default.', kernel=data['kernel'], token=token)


def boot_check():
    args = Path('/proc/cmdline').read_text().split()
    if 'precision_psr.validated=1' not in args or trial_token(' '.join(args)):
        return
    config = json.loads(m.CONFIG.read_text())
    if m.maintenance_errors(config):
        m.set_default(m.newest_stock())
        report('fallback', 'Updated boot inputs detected before login; rebooting into stock Fedora.')
        run('systemctl', '--no-block', 'reboot')


def recover():
    token = trial_token(Path('/proc/cmdline').read_text())
    if not token or CONFIRMED.exists():
        return
    # No one-time boot selection is needed: test() already retained a stock default.
    m.set_default(m.newest_stock())
    report('recovered', 'Unconfirmed PSR trial: returning to a stock PSR-disabled boot.', token=token)
    if not CONFIRMED.exists():
        run('systemctl', 'reboot')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'status', 'test', 'confirm', 'recover', 'boot-check'])
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.action == 'status':
        print(STATE.read_text() if STATE.exists() else 'Automatic maintenance has not run yet.')
        return
    if os.geteuid():
        raise SystemExit('Run with sudo or use the PSR Updates application')
    if out('cat', '/sys/class/dmi/id/sys_vendor') != 'Dell Inc.' or out('cat', '/sys/class/dmi/id/product_name') != 'Precision 5550':
        raise SystemExit('This integration is restricted to Dell Precision 5550')
    BASE.mkdir(mode=0o755, parents=True, exist_ok=True)
    with (BASE / 'maintenance.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args.action == 'build':
                build(args.force)
            else:
                globals()[args.action.replace('-', '_')]()
        except Exception as exc:
            # A failure never enables a candidate or rewrites stock driver files.
            if args.action == 'build':
                report('error', 'PSR rebuild postponed: ' + str(exc))
            raise


if __name__ == '__main__':
    main()
