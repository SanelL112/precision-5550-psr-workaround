# Automatic PSR rebuilds with local screen confirmation

The tested host now checks every 15 minutes while on AC power. A normal application update needs no PSR action. For a new stock kernel, or changes to tracked kernel/GPU inputs, the worker obtains the exact Fedora source RPM and development files, verifies the source RPM with the system RPM keyring, applies the bundled patches without fuzzy matching, builds i915, and signs it with the already enrolled local akmods key. It stages a separate image and BLS entry. Stock modules/images are never replaced. A separate check ordered before the login screen handles stale persistent images after offline updates by selecting stock Fedora and requesting a recovery reboot; it is not triggered by live desktop file changes. Compilation is limited to two jobs and the service has CPU, memory and time limits.

This is custom integration, not an akmods package or an upstream driver release. A clean build is not proof that the physical backlight works. The workflow requires no assistant for a compatible routine update:

1. Update normally. Stock PSR-disabled Fedora remains the fallback, and new kernels use stock until confirmed.
2. When notified, open **PSR Updates** from the application launcher and choose **Prepare test**. Reboot when ready.
3. After login, confirm **Screen works**. The app authenticates locally and promotes that exact build to the saved default. If it is dark or left unconfirmed, the five-minute recovery timer reboots into stock Fedora. GRUB consumes the trial selection only once.

No automatic trial/reboot occurs merely because a build succeeded. The physical-screen check is required once per candidate, rather than involving an assistant. A confirmation prompt is shown only during a trial; ordinary logins remain quiet. Tests of resume/docking and longer-term behavior are still useful after driver changes.

If source packages are unavailable, signing trust is missing, files change during a build, NVIDIA has not finished building, disk space is low, or the patch/API is incompatible, the worker reports an error without enabling the candidate. Later checks retry. A future incompatible kernel can still require patch maintenance; this system cannot guarantee that every future i915 change will build or behave correctly. It never edits failed patches automatically or disables Secure Boot.

Commands:

```bash
precision-psr-update status
sudo precision-psr-update build
sudo precision-psr-update test
sudo precision-psr-update confirm
sudo precision-psr use-stock
```

The GUI performs test/confirm through pkexec and asks separately before rebooting. The CLI test action only schedules a one-time trial. The CLI confirm action must be used only after physically verifying the screen. The recover action is for the trial timer and can reboot an unconfirmed trial.

The source `install.py` requires an existing validated host configuration from the lifecycle integration, enrolled akmods signing credentials, Fedora build tools, and a working stock PSR-disabled BLS entry. It installs only the system component; the desktop launcher, login hook/autostart and user notification timer must also be installed for the target user. The tested Hyprland host uses a custom `hyprland.start` hook, because this session does not automatically run GNOME's XDG autostart entries. Do not copy signing credentials or generated host metadata from another machine.

Status: `/var/lib/precision-psr-auto/status.json`. Service logs: `journalctl -u precision-psr-build.service`. Images and candidate metadata are owned by root. Cleanup removes only registered, unchanged candidates, preserving the validated/default/next entries, newest candidate, and candidates for the currently running kernel.

Run the 16 workflow tests:

```bash
python3 -m unittest discover -s automatic -v
```

The tests cover signature requirements, pre-login fallback, one-time selection with a stock persistent default, existing one-time boot preservation, stale candidate rejection, trial marker validation, confirmation/recovery guards, watch-path validation, and safe cleanup. An actual future Fedora kernel upgrade and the new GUI trial/confirmation path have not yet been exercised end to end.

The full build/sign/stage pipeline was executed successfully on the current validated kernel: source verification and strict patching, compilation, ABI/dependency checks, enrolled-key signing, kernel-compatible compression, separate initramfs creation and embedded-module byte verification all passed. This took about 3½ minutes with two build jobs, with a reported peak memory use of 2.4 GiB. The existing boot selection was retained. The new source-download path and a future kernel version still require real update validation.
