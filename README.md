# Dell Precision 5550: experimental i915 PSR1 link-standby workaround

A small, opt-in i915 change avoided a dark internal display when enabling PSR1 on one Dell Precision 5550. **Screen operation and four s2idle suspend/resume cycles are confirmed. Longer-term reliability and controlled battery savings are not yet established.** This is a local experiment, not an upstream fix or a supported driver release.

## What changed

[Panel Self Refresh](https://docs.kernel.org/gpu/intel-display/psr.html) lets the panel display its cached frame while the computer reduces display activity. The stock driver used the firmware-selected link-off policy on this machine. PSR1 activation made the internal screen dark even though the driver reported nonzero brightness and the panel reported no PSR errors.

The workaround sets `intel_dp->psr.link_standby=true`. Existing i915 code then sets both:

- `DP_PSR_MAIN_LINK_ACTIVE` in the panel's PSR configuration.
- `EDP_PSR_LINK_STANDBY` in the Intel controller's PSR control register.

The panel can self-refresh while the main link remains active. In the working test, source diagnostics reported `standby=1`, and the panel reported active self-refresh with error status zero. This supports a link-off interaction hypothesis; it does not identify a specific panel firmware defect. Keeping the link active may sacrifice some power savings compared with link-off PSR.

The override defaults off and requires all of: `psr_diag_link_standby=1`, `psr_diag=1`, `enable_psr=1`, display generation 9, source eDP PSR support, and exact DMI strings `Dell Inc.` / `Precision 5550`. It does not enable PSR2 or apply to unrelated machines.

## Tested configuration and observations

| Item | Observed configuration/result |
| --- | --- |
| Laptop | Dell Precision 5550, Intel i7-10750H / Comet Lake Gen9 display |
| Panel | Sharp SHP 0x14d1, LQ156N1 family, 1920x1200 |
| OS/kernel | Fedora 44, `7.2.11-200.fc44.x86_64` |
| BIOS | 1.42.0 |
| Signing | Secure Boot remained enabled; existing enrolled local key |
| Stock PSR1 | Physical screen dark |
| Stock PSR1 + conservative training timings | Physical screen dark |
| Instrumented PSR1, link-off | Driver confirmed loaded; physical screen dark |
| Instrumented PSR1, link-standby | User confirmed working backlight; PSR1 and panel self-refresh verified |
| Battery savings | Not measured in a controlled battery comparison |
| Suspend/resume | Four user-triggered s2idle cycles passed; PSR1 and panel self-refresh verified after the final wake |

The successful test retained `i915.psr_safest_params=1`; normal firmware timings have not been isolated from this result. Other local driver options also remained in place, so this is not a claim that every Precision 5550 configuration will behave identically.

## Contents

- `patches/0001-*`: default-off bounded PSR diagnostics, maximum 96 additional kernel messages per module load.
- `patches/0002-*`: the actual Precision 5550 PSR1 link-standby experiment.
- `build.sh`: reproducible, build-only recipe for the exact tested kernel/source.
- `tools/`: boot-entry generation, kernel-compatible XZ packaging, and trace collection.
- `examples/recovery/`: the four-minute recovery helper and systemd unit examples.
- `tests/`: boot-entry safety and compression regression tests.
- [Build and test details](docs/build-and-test.md), [update behavior](docs/updates.md), [sanitized evidence](docs/test-results.md).

Host-specific installers, credentials, raw logs, boot/root identifiers, signing keys, firmware dumps, kernel archives and compiled modules are not included.

## Build

Obtain the matching Fedora source RPM `kernel-7.2.11-200.fc44.src.rpm` and extract its `linux-7.2.11.tar.xz`. Install the matching kernel-devel and normal kernel-module build dependencies (GCC, make, patch, tar/xz, elfutils-libelf-devel and openssl-devel). The tested compiler was GCC 16.2.1.

```bash
./build.sh /path/to/linux-7.2.11.tar.xz
```

The script checks the running kernel release and exact source archive hash, extracts only required source files, applies both patches and builds i915. It makes no changes to the installed driver or boot settings. Build output is unsigned. Follow [build and test details](docs/build-and-test.md) for signing, isolation and recovery requirements before considering a test boot.

Run the lightweight checks with:

```bash
PYTHONPATH=tools python3 -m unittest discover -s tests -v
bash -n build.sh
```

## Will updates break it?

A custom module is specific to its kernel build. A new kernel requires a new matching build and a fresh test; this repository's recipe intentionally rejects other kernels. BIOS/panel firmware changes, panel replacement, PSR2, and suspend/resume can affect behavior and need validation. Ordinary unrelated application changes have not been shown to invalidate the workaround.

The tested installation uses a separate diagnostic initramfs and GRUB entry. The normal Fedora kernel, module, initramfs, and default boot were kept unchanged with PSR disabled. There is no automatic rebuild, DKMS/akmods package, or permanent PSR enablement here. A normal reboot therefore does not preserve the experimental workaround unless that test entry is selected again. See [update behavior](docs/updates.md).

## Sources and license

The implementation was checked against the matching Fedora kernel source. Useful upstream references: [i915 documentation](https://docs.kernel.org/gpu/i915.html), [module signing](https://docs.kernel.org/admin-guide/module-signing.html), and [kernel XZ requirements](https://cdn.kernel.org/doc/html/latest/staging/xz.html).

New repository tooling is MIT licensed. Modified i915 files retain their upstream MIT notices; see [LICENSE](LICENSE). Linux source and signed binaries are not redistributed here.
