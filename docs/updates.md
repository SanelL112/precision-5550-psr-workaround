# What changes can affect the workaround?

## Kernel updates

The built i915 module targets exactly `7.2.11-200.fc44.x86_64`. Do not copy it into another kernel's module tree. Kernel ABI, internal structures, exported symbols, driver behavior and signing requirements can change. Obtain matching source and kernel-devel, port/review the patches if necessary, rebuild, sign, stage a separate image, and repeat testing.

This repository supplies no automatic rebuild integration. The original normal boot entry and default remained PSR-disabled, and newer normal entries should be inspected rather than assumed to inherit any particular command line. An update can stop using this workaround without implying that the hardware has failed. Enabling PSR on an unpatched driver may reproduce the original dark-screen behavior.

## BIOS, firmware, panel and PSR mode

The tested BIOS was 1.42.0 and the panel was a Sharp SHP 0x14d1. Firmware may change VBT timings or link policy. A replacement panel may have different behavior. The experimental override is deliberately opt-in and checks the machine model and display generation, but does not identify the panel EDID: the model guard is not proof of compatibility with every panel variant.

The change is restricted to PSR1. Changing `enable_psr` to 2 prevents this override from applying. Removing `psr_diag=1` also prevents it from applying. Removing the new module/image, losing signing-key trust, or selecting the normal boot will stop using the experimental path.

One s2idle suspend/resume cycle has passed with post-wake PSR verification. Repeated sleep/wake cycles, display power cycling, external displays, refresh-rate changes and sustained workloads still need testing. The current result is an experimental workaround with initial screen and resume validation, not a permanent upstream fix.

## Power savings

Keeping the main link active can save less than fully powering it down. The working test was not a controlled battery run, and a 5 W idle target is not established. Measure whole-laptop battery discharge under comparable brightness, external-display, application and power-profile conditions before attributing savings to PSR.

## Debugging overhead

The successful build retains diagnostic logging, DRM debugging and conservative training timings. A future production version should isolate those settings, reduce diagnostics, retest screen stability and remeasure power. Disabling diagnostics in this exact experiment also disables the behavior override; do not simply remove that flag and expect the same behavior.
