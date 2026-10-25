# What changes can affect the workaround?

## Kernel updates

The built i915 module targets exactly `7.2.11-200.fc44.x86_64`. Do not copy it into another kernel's module tree. Kernel ABI, internal structures, exported symbols, driver behavior and signing requirements can change. Obtain matching source and kernel-devel, port/review the patches if necessary, rebuild, sign, stage a separate image, and repeat testing.

The tested host now has a saved default named **Dell Precision 5550 PSR1 (validated)**, using the existing tested image and exact tested options. Its persistent marker excludes it from the four-minute diagnostic recovery timer. The stock kernel, module, image and recovery entry remain unchanged, and `/etc/kernel/cmdline` explicitly disables PSR for future stock entries.

The installed kernel-install hook switches newer kernel updates to stock PSR-disabled boots rather than pinning the old experimental kernel. A boot-time check and systemd path watcher detect changes to tracked images, NVIDIA modules, signing certificate and boot configuration; if the validated entry is selected, they fall back to a usable stock default. The live path watcher changes the next default, not the running driver. A separate check before the login screen detects stale persistent images after offline updates and requests a recovery reboot into stock Fedora. The separate [automatic worker](../automatic/README.md) now attempts matching-source rebuilds and signing while on AC power. It stages a candidate without enabling it; the local PSR Updates app handles one-time testing and screen confirmation. It does not automatically rewrite incompatible patches. BIOS/panel changes still need manual review.

After kernel or GPU-driver updates, run:

```bash
sudo precision-psr status
```

For a compatible routine update, the worker performs the rebuild/sign/stage steps. Open **PSR Updates** when notified, prepare a one-time trial, reboot, and confirm that the built-in screen works. No assistant is required. If the worker reports an incompatible source/API change, patch maintenance is still necessary before another build can be tested. Do not force the stale image back into use. To select stock recovery without rebooting, run `sudo precision-psr use-stock`. `sudo precision-psr use-validated` refuses tracked-file/signing-trust mismatches, but is not a substitute for validating a future build. The [lifecycle reference tools](../lifecycle/README.md) are included; the host-specific installer and configuration are omitted.

An update can stop using this workaround without implying that the hardware has failed. Enabling PSR on an unpatched driver may reproduce the original dark-screen behavior.

## BIOS, firmware, panel and PSR mode

The tested BIOS was 1.42.0 and the panel was a Sharp SHP 0x14d1. Firmware may change VBT timings or link policy. A replacement panel may have different behavior. The experimental override is deliberately opt-in and checks the machine model and display generation, but does not identify the panel EDID: the model guard is not proof of compatibility with every panel variant.

The change is restricted to PSR1. Changing `enable_psr` to 2 prevents this override from applying. Removing `psr_diag=1` also prevents it from applying. Removing the new module/image, losing signing-key trust, or selecting the normal boot will stop using the experimental path.

Four s2idle suspend/resume cycles have passed with post-wake PSR verification. One all-display power-off/on cycle and the user-reported charger transition sequence also passed, with PSR verified afterward. The user confirmed the charging-cable test also disconnected/reconnected the dock, and a second experimental boot passed with the driver and PSR state verified. Sustained day-to-day use and controlled power attribution remain outstanding. The current result is an experimental workaround with initial screen and resume validation, not a permanent upstream fix.

## Power savings

Keeping the main link active can save less than fully powering it down. The working test was not a controlled battery run, and a 5 W idle target is not established. Measure whole-laptop battery discharge under comparable brightness, external-display, application and power-profile conditions before attributing savings to PSR.

## Debugging overhead

The successful build retains diagnostic logging, DRM debugging and conservative training timings. A future production version should isolate those settings, reduce diagnostics, retest screen stability and remeasure power. Disabling diagnostics in this exact experiment also disables the behavior override; do not simply remove that flag and expect the same behavior.
