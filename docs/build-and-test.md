# Building and testing the experiment

## Exact source and build

The verified Fedora source RPM was `kernel-7.2.11-200.fc44.src.rpm`.

- Source RPM SHA256: `08c2ba8240dd40bf2c52e36f62a71c05f8353cca5da762b2a6b914d0d09dd08d`
- Extracted `linux-7.2.11.tar.xz` SHA256: `223bb02226cf116e5e6babe25ffd420589db568154616765889287299775cdbf`

`build.sh` reproduces the external-module build using the matching installed kernel-devel, Module.symvers and compiler. The empty source `include/trace` directory supplies a source-relative include search path for the existing i915 trace headers. `drivers/platform/x86/intel_ips.h` is extracted because i915 references it by a relative include. The Fedora patch in the matching RPM did not modify this i915 subtree.

Both patches were separately applied to pristine matching source and reproduced the exact three modified files compiled for the successful test. Kernel patch style checking reported no code errors or warnings. Standalone BTF generation was skipped because vmlinux was not available; the tested driver loaded successfully with the distribution kernel.

## Signing and compression

Use an enrolled module-signing certificate. The original test reused an already enrolled akmods key, without disabling Secure Boot or enrolling a new key. Keep the private key outside this repository. Strip debug symbols before signing; modifying signed bytes afterwards invalidates the signature. See the [kernel signing documentation](https://docs.kernel.org/admin-guide/module-signing.html).

Compress the signed copy using:

```bash
python3 tools/pack-module.py /path/to/signed/i915.ko /path/to/staging/i915.ko.xz
```

This creates a new output file using CRC32 and a 1 MiB LZMA2 dictionary. Python's default CRC64 XZ stream was rejected by the tested kernel before module initialization. Userspace decompression and matching archive hashes alone did not catch that incompatibility. A signed probe verified that CRC64 returned EINVAL while the corrected stream reached the probe's expected ECANCELED initialization result. No probe remained loaded. See [kernel XZ requirements](https://cdn.kernel.org/doc/html/latest/staging/xz.html).

## Isolated boot image

There is no portable installer in this repository. The original host-specific staging process:

1. Recorded hashes of the normal BLS entry, distribution kernel, normal initramfs and installed i915 module, plus the GRUB default/environment.
2. Put the signed compressed driver into a staging overlay at its normal module path.
3. Built a separate initramfs with dracut `--nostrip --force-drivers i915 --include <overlay> /`.
4. Extracted the embedded module with `lsinitrd -f` and checked its compressed bytes against the staged file and its decompressed bytes against the signed module.
5. Created a separate BLS entry with the distribution kernel, new initramfs, and flags below, preserving root/storage parameters and Fedora's `$tuned_initrd`/`$tuned_params` placeholders.
6. Installed and verified independent recovery and trace services; rechecked normal file hashes and GRUB selection unchanged.
7. Selected the test only for one boot, after the user approved restarting.

The boot-entry generator in `tools/boot_entry.py` takes the text of an existing normal PSR-disabled entry and an initramfs path. It returns a separate test entry; callers are responsible for writing a new file and never overwriting their normal entry.

Test flags:

```text
i915.enable_psr=1 i915.psr_safest_params=1 i915.psr_diag=1 i915.psr_diag_link_standby=1 drm.debug=0x106 log_buf_len=8M
```

The original test entry title was **Precision 5550 PSR1 link-standby test v2 (4-minute recovery)**.

## Recovery examples

The files under `examples/recovery` are reference components. Before using them, install the helper root-owned at `/usr/local/sbin/precision-psr-test` and create root-owned `/etc/precision-psr-test.json` identifying an existing, verified PSR-disabled normal BLS entry. Install and enable the supplied timer/service, and verify that they skip normal boots. The timer uses OnBootSec=4min and is independent of successful graphical login.

The helper verifies that the normal entry contains `i915.enable_psr=0`, selects it for one boot, checks that GRUB accepted the selection, and requests a reboot. The helper's `confirm` action cancels recovery only after a person confirms the physical screen works. `recover` returns to normal manually. The timer depends on functioning userspace and cannot recover a complete kernel hang; retain a normal boot option.

`tools/precision-psr-trace` records source/panel status every two seconds and periodically saves kernel logs. Its service example is in `examples/recovery`. It checks both diagnostic parameters and requests recovery if the experimental driver did not load. It expects the helper and normal-entry config described above. Neither the trace helper nor units install or enable themselves.

## Runtime verification

The parameters are root-readable:

```bash
sudo cat /sys/module/i915/parameters/psr_diag_link_standby
sudo journalctl -k -b --grep='PSRDIAG-v2'
sudo cat /sys/kernel/debug/dri/0000:00:02.0/i915_edp_psr_status
```

Expect `Y`, the v2 experiment-enabled message, and PSR1 enabled with `standby=1`. Physical screen confirmation is still essential. Continue with sustained display use, user-approved suspend/resume testing, and a controlled battery comparison. A successful boot alone establishes none of those later results.
