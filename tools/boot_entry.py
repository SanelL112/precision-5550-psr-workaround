"""Generate a separate diagnostic boot, retaining the distribution kernel."""

def make_entry(original, image):
    if not image.startswith('/initramfs-') or '/' in image[1:]:
        raise ValueError('Unexpected diagnostic image name')
    lines = original.splitlines()
    options = [line for line in lines if line.startswith('options ')]
    inits = [line for line in lines if line.startswith('initrd ')]
    titles = [line for line in lines if line.startswith('title ')]
    if len(options) != 1 or len(inits) != 1 or len(titles) != 1:
        raise ValueError('Expected exactly one title, options and initrd')
    init_parts = inits[0].split()
    if len(init_parts) < 2 or init_parts[2:] not in ([], ['$tuned_initrd']):
        raise ValueError('Unexpected multiple initrd images')
    args = options[0].split()[1:]
    if args.count('i915.enable_psr=0') != 1:
        raise ValueError('Normal boot must disable PSR')
    changes = {'i915.enable_psr': '1', 'i915.psr_safest_params': '1',
               'i915.psr_diag': '1', 'i915.psr_diag_link_standby': '1', 'drm.debug': '0x106', 'log_buf_len': '8M'}
    args = [arg for arg in args if arg.split('=', 1)[0] not in changes]
    args += [f'{key}={value}' for key, value in changes.items()]
    result = []
    for line in lines:
        if line.startswith('title '):
            line = 'title Precision 5550 PSR1 link-standby test v2 (4-minute recovery)'
        elif line.startswith('initrd '):
            line = 'initrd ' + ' '.join([image] + init_parts[2:])
        elif line.startswith('options '):
            line = 'options ' + ' '.join(args)
        result.append(line)
    return '\n'.join(result) + '\n'
