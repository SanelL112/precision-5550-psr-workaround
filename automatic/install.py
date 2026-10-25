#!/usr/bin/python3
"""Install automatic maintenance without selecting a boot or rebooting."""
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEST = Path('/usr/local/lib/precision-psr-auto')


def run(*args):
    subprocess.run(list(map(str,args)),check=True)


def install(src,dest,mode):
    dest.parent.mkdir(parents=True,exist_ok=True)
    run('install','-o','root','-g','root','-m',oct(mode)[2:],src,dest)


def main():
    if os.geteuid():raise SystemExit('Requires sudo')
    if not Path('/etc/precision-psr-managed.json').is_file():
        raise SystemExit('A validated local PSR installation is required first')
    if DEST.exists():raise SystemExit('Automatic maintenance already exists')
    saved=subprocess.check_output(['grub2-editenv','list'])
    DEST.mkdir(mode=0o755)
    for name in ['auto.py','gui.py']:
        install(HERE/name,DEST/name,0o644)
    for src,name in [(ROOT/'lifecycle/precision-psr','manager.py'),(ROOT/'tools/boot_entry.py','boot_entry.py'),(ROOT/'tools/module_pack.py','module_pack.py')]:
        install(src,DEST/name,0o644)
    for src in (ROOT/'patches').glob('*.patch'):
        install(src,DEST/'patches'/src.name,0o644)
    install(HERE/'precision-psr-update',Path('/usr/local/sbin/precision-psr-update'),0o755)
    units=[]
    for name in ['precision-psr-build.service','precision-psr-build.timer','precision-psr-auto-recover.service','precision-psr-auto-recover.timer','precision-psr-boot-check.service']:
        dest=Path('/etc/systemd/system')/name
        install(HERE/name,dest,0o644);units.append(dest)
    install(HERE/'display-manager-psr.conf',Path('/etc/systemd/system/display-manager.service.d/precision-psr.conf'),0o644)
    install(HERE/'psr-updates.desktop',Path('/usr/local/share/applications/psr-updates.desktop'),0o644)
    base=Path('/var/lib/precision-psr-auto');base.mkdir(mode=0o755,exist_ok=True)
    (base/'sources').mkdir(mode=0o755,exist_ok=True)
    run('restorecon','-RF',DEST,'/usr/local/sbin/precision-psr-update')
    run('systemd-analyze','verify',*units)
    run('systemctl','daemon-reload')
    run('systemctl','enable','precision-psr-build.timer','precision-psr-auto-recover.timer')
    run('systemctl','start','precision-psr-auto-recover.timer')
    run('/usr/local/sbin/precision-psr-update','build')
    run('systemctl','start','precision-psr-build.timer')
    if subprocess.check_output(['grub2-editenv','list']) != saved:
        raise RuntimeError('Boot selection unexpectedly changed')
    print('Automatic PSR maintenance installed. No boot selection changed; no reboot requested.')

if __name__=='__main__':main()
