"""Boot entry policy for promoting an already validated PSR build."""
MARKER = 'precision_psr.validated=1'
TITLE = 'Dell Precision 5550 PSR1 (validated)'


def promote_entry(text):
    lines = text.splitlines()
    options = [line for line in lines if line.startswith('options ')]
    if len(options) != 1 or sum(line.startswith('title ') for line in lines) != 1:
        raise ValueError('Expected one title and options line')
    args = options[0].split()[1:]
    expected = ['i915.enable_psr=1', 'i915.psr_safest_params=1',
                'i915.psr_diag=1', 'i915.psr_diag_link_standby=1']
    for flag in expected:
        key = flag.split('=', 1)[0]
        if [arg for arg in args if arg.split('=', 1)[0] == key] != [flag]:
            raise ValueError('Missing or conflicting validated parameter: ' + key)
    if any(arg.startswith('precision_psr.validated=') for arg in args):
        raise ValueError('Source already has a validated marker')
    # Preserve the exact tested hardware/debug options and existing initramfs.
    return '\n'.join(
        'title ' + TITLE if line.startswith('title ') else
        line + ' ' + MARKER if line.startswith('options ') else line
        for line in lines
    ) + '\n'


def exclude_validated_boot(unit):
    condition = 'ConditionKernelCommandLine=!' + MARKER
    if condition in unit.splitlines():
        return unit
    if unit.count('[Unit]') != 1:
        raise ValueError('Expected one Unit section')
    return unit.replace('[Unit]\n', '[Unit]\n' + condition + '\n', 1)


def stock_args_safe(text):
    args = text.split()
    psr = [arg for arg in args if arg.startswith('i915.enable_psr=')]
    return psr == ['i915.enable_psr=0'] and not any(
        arg.startswith(('i915.psr_diag=', 'i915.psr_diag_link_standby=',
                        'i915.psr_safest_params=', 'precision_psr.validated='))
        for arg in args
    )


def default_env_preserved(before, after):
    """grub2-set-default intentionally clears both transient entry fields."""
    transient = {'saved_entry', 'next_entry', 'prev_saved_entry'}
    return (not after.get('next_entry') and not after.get('prev_saved_entry')
            and {k: v for k, v in before.items() if k not in transient}
            == {k: v for k, v in after.items() if k not in transient})
