#!/usr/bin/env bash
# Build only. This script does not sign, install, select a boot, or reboot.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $# != 1 ]]; then
    echo "Usage: $0 /path/to/linux-7.2.11.tar.xz" >&2
    exit 2
fi
archive=$(realpath -- "$1")
kernel_release=$(uname -r)
if [[ $kernel_release != 7.2.11-200.fc44.x86_64 ]]; then
    echo 'This recipe is validated only for kernel 7.2.11-200.fc44.x86_64.' >&2
    echo 'Port and retest the patches/build recipe before using another kernel.' >&2
    exit 1
fi
expected=223bb02226cf116e5e6babe25ffd420589db568154616765889287299775cdbf
actual=$(sha256sum -- "$archive")
if [[ ${actual%% *} != "$expected" ]]; then
    echo 'Source archive differs from the verified Fedora source used for this test.' >&2
    exit 1
fi
kernel_build=/lib/modules/$kernel_release/build
[[ -f $kernel_build/Module.symvers ]] || { echo 'Matching kernel-devel is required.' >&2; exit 1; }
mkdir -p -- "$repo_root/build"
work=$(mktemp -d "$repo_root/build/work.XXXXXX")
tar -xJf "$archive" -C "$work" -- \
    linux-7.2.11/drivers/gpu/drm/i915 \
    linux-7.2.11/drivers/platform/x86/intel_ips.h
source_root=$work/linux-7.2.11
for patch_file in "$repo_root"/patches/*.patch; do
    patch --batch --forward -d "$source_root" -p1 -i "$patch_file"
done
mkdir -p -- "$source_root/include/trace"
make -C "$kernel_build" \
    M="$source_root/drivers/gpu/drm/i915" \
    KCFLAGS="-I$source_root/include/trace" -j4 modules
module=$source_root/drivers/gpu/drm/i915/i915.ko
modinfo -p "$module" | sed -n '/psr_diag/p'
printf '\nUnsigned build output: %s\n' "$module"
printf 'No installation or boot settings were changed.\n'
