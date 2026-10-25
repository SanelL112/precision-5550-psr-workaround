# Validated boot lifecycle helpers

These helpers select an already tested, signed, kernel-specific PSR image as a saved GRUB default, and detect when that image no longer matches the installed kernel/GPU files. They do not build or install patches automatically.

The host-specific installer and generated configuration are deliberately omitted. These files are reference tooling, not a portable one-command installer. `precision-psr` requires a root-owned `/etc/precision-psr-managed.json` containing the validated kernel release, BLS entry ID, artifact SHA256 hashes, update-input SHA256 hashes, and optional enrolled signing certificate path. Do not copy another machine's configuration or signing key.

The local installation also generates a systemd path unit watching those inputs. `precision-psr-guard.service` checks them at boot. The kernel-install hook records add/remove events, chooses a stock PSR-disabled default for newer kernels, and retires its unchanged generated BLS entry if its kernel is removed. A changed kernel, initramfs, NVIDIA module, signing certificate, or boot configuration requires review and a refreshed build/test. The guard changes the next boot default; it does not reload the running display driver.

`boot_config.py` preserves the exact tested kernel options and image when generating a persistent entry. Its `precision_psr.validated=1` marker is excluded from the four-minute test recovery/audit units. Stock entries retain `i915.enable_psr=0`.

Commands on a configured host:

```bash
sudo precision-psr status
sudo precision-psr use-stock
sudo precision-psr use-validated
```

Changing the default does not reboot. Selecting the validated entry is refused if tracked files or signing trust have changed. Future kernels require matching source/development files, patch review, compilation, signing, a separate image, and screen/resume tests before promotion. This integration does not pin an old kernel against security updates.

Run the lifecycle tests independently:

```bash
python3 -m unittest discover -s lifecycle -v
```
