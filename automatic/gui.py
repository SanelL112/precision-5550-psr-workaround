#!/usr/bin/python3
"""Local PSR update notification and physical-screen confirmation."""
import json
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys

CLI = '/usr/local/sbin/precision-psr-update'
STATE = Path('/var/lib/precision-psr-auto/status.json')
SEEN = Path.home() / '.local/state/precision-psr/last-notified'


def dialog(*args):
    return subprocess.run(['zenity', *args]).returncode == 0


def privileged(action):
    result = subprocess.run(['pkexec', CLI, action], capture_output=True, text=True)
    if result.returncode:
        dialog('--error', '--title=PSR Updates', '--text=' + (result.stderr or result.stdout)[-1500:])
        return False
    return True


def main():
    args = Path('/proc/cmdline').read_text().split()
    trial = any(a.startswith('precision_psr.trial=') for a in args)
    confirmed = Path('/run/precision-psr-auto-confirmed').exists()
    if trial and not confirmed:
        if dialog('--question', '--title=Confirm PSR screen', '--timeout=180',
                  '--text=Is the laptop’s built-in screen lit and working correctly?\n\nConfirm to keep this PSR build. Without confirmation the laptop will reboot into stock Fedora after five minutes.',
                  '--ok-label=Screen works', '--cancel-label=Use stock Fedora'):
            privileged('confirm')
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {'phase': 'waiting', 'message': 'Automatic maintenance has not run yet.'}
    if '--notify' in sys.argv or '--login' in sys.argv:
        token = state.get('token') or hashlib.sha256(state['message'].encode()).hexdigest()
        if state['phase'] in ('ready', 'error') and (not SEEN.exists() or SEEN.read_text() != token):
            if state['phase'] == 'ready':
                subprocess.run(['notify-send', 'PSR update ready', 'Open “PSR Updates” to test the new signed build. Stock Fedora remains available.'])
            else:
                subprocess.run(['notify-send', 'PSR rebuild postponed', 'Open “PSR Updates” for details. The failed build was not enabled.'])
            SEEN.parent.mkdir(parents=True, exist_ok=True)
            SEEN.write_text(token)
        return
    if state['phase'] == 'ready':
        if dialog('--question', '--title=PSR Updates',
                  '--text=A matching signed PSR build is ready. Test it on the next reboot?\n\nStock Fedora remains the default until you confirm the built-in screen. An unconfirmed trial automatically reboots into stock Fedora.',
                  '--ok-label=Prepare test', '--cancel-label=Later') and privileged('test'):
            if dialog('--question', '--title=PSR Updates', '--text=One-time PSR test prepared. Reboot now?', '--ok-label=Reboot', '--cancel-label=Later'):
                subprocess.run(['systemctl', 'reboot'])
    else:
        dialog('--info', '--title=PSR Updates', '--text=' + state['message'] + '\n\nKernel and GPU changes are checked automatically while on AC power. No assistant is needed for routine rebuilds.')


if __name__ == '__main__':
    lock_path = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid()))) / 'precision-psr-gui.lock'
    with lock_path.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(0)
        main()
