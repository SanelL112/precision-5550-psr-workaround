# Sanitized test evidence

The tests used the same laptop and matching Fedora kernel build. The successful experiment retained conservative PSR training timings and other existing local driver options.

| Experiment | Driver verified? | Physical result | Relevant state |
| --- | --- | --- | --- |
| Stock PSR1 | Yes | Dark screen | Nonzero backlight reported |
| Stock PSR1 with conservative timings | Yes | Dark screen | No explanatory PSR/AUX error |
| First diagnostic package | No: kernel rejected XZ options, stock driver loaded later | Dark screen | Invalid diagnostic trial; no custom-driver conclusion |
| Corrected diagnostic, normal link-off policy | Yes: parameter Y and diagnostic messages | Dark screen | standby=0; panel config 0x4/0x5 accepted; no panel PSR error |
| Link-standby behavior change | Yes: both parameters Y and v2 enable message | User confirmed backlight works | standby=1; panel config 0x6/0x7 accepted; active panel self-refresh, error=0 |

Representative successful state:

```text
PSR mode: PSR1 enabled
PSRDIAG-v1 standby=1 active=1 link_ok=1 pause=0
Source PSR/PanelReplay ctl: enabled [0x89f00e29]
Sink PSR status: 0x2 [active, display from RFB]
Sink PSR error status: 0x0
```

The `PSRDIAG-v1` status label identifies the retained instrumentation layer; the `PSRDIAG-v2` kernel message identifies the new behavior override. The two labels in one successful run are expected.

The source-only build and patch reproduction checks passed. Seven boot-entry safety tests and the compression-format test are included in this repository. Recovery behavior also passed ten tests in the original local investigation; those host-test fixtures are not part of this exported repository, so the repository's runnable suite reports eight tests.

No boot identifiers, root filesystem UUIDs, serials, raw firmware data, process lists, private keys or credentials are included. At initial publication, suspend/resume and battery-power outcomes were unverified; subsequent observations are recorded below.

The exported build.sh was subsequently executed against the verified archive on the tested kernel. It completed successfully and produced an i915 module exposing both diagnostic parameters. This build-only verification did not alter the installed driver or boot settings.

## Subsequent battery and suspend observations

After stopping an unused automatically started virtual RDP display, the user reported approximately 5 W total idle draw, compared with their earlier reported 10–11 W. These are user observations across several changes, not a controlled PSR-on/off comparison; the contributions of PSR, virtual-display removal and workload changes have not been isolated.

The user reported one flicker during the battery-triggered switch from about 60 Hz to 47.96 Hz. Logs showed successful internal link training and PSR1 re-enable at the transition, with no matching internal PSR timeout observed. Steady-state flicker has not been established.

An initial suspend attempt failed before sleep because SELinux denied NVIDIA access to its anonymous video-memory backing file. A separate local file-labeling correction resolved that access failure while retaining SELinux enforcing. This machine-specific correction is not part of the i915 patch set. The failure resembles [Fedora issue 2482677](https://bugzilla.redhat.com/show_bug.cgi?id=2482677).

After that correction, one user-triggered s2idle suspend/resume cycle completed with systemd-suspend.service exit status 0/SUCCESS. The user reported no apparent breakage. Post-wake checks confirmed PSR1 enabled, standby=1, panel active self-refresh with error status zero, and the experiment parameter still Y. This is one verified cycle; repeated cycles and longer-term reliability remain unverified.

Three additional user-triggered s2idle cycles subsequently completed successfully, bringing the verified count to four. The three additional request-to-return intervals were approximately 2, 5 and 11 minutes. The user reported no issues. The final systemd result was success, and the final post-wake check again confirmed PSR1, standby=1, active panel self-refresh and error status zero. This adds repeated-cycle evidence on the tested configuration, while broader display-transition and longer-term testing remain outstanding.

The user then completed a charger plug/unplug sequence without issues. Post-test checks showed PSR1 enabled with standby=1 and no panel PSR error. One all-display off/on (DPMS) cycle with a 10-second delay also passed: the user reported no issues, all three outputs were on afterward, and PSR1 remained enabled with standby=1 and the panel actively self-refreshing with error status zero. The recent log scan found no matching internal PSR timeout, eDP failure, GPU hang or underrun. The two external displays were present during verification; a separate physical monitor/dock reconnect test has not yet been reported.

The dock was also the charging source, so the earlier charger disconnect/reconnect sequence covered physical dock removal/reconnection; the user confirmed this. A second one-time boot into the same v2 experimental entry then passed. The user reported no issues, the kernel emitted the v2 experiment-enable message, both diagnostic parameters were Y, and the panel reported PSR1 self-refresh with standby=1 and error status zero. Automatic recovery was cancelled after physical confirmation. The normal boot default was retained. These checks complete the planned initial reboot, dock, DPMS, charger and repeated-suspend tests; sustained day-to-day use and controlled power attribution remain outstanding.

## Persistent default and update handling

Further v2 boots again showed PSR1 enabled with standby=1, and the user confirmed the built-in screen worked. The tested image was then promoted to a separate saved default titled `Dell Precision 5550 PSR1 (validated)`. The original stock boot files were checked against their recorded SHA256 hashes and remained unchanged. The promotion reused the exact tested image and hardware options, adding only the persistent boot marker and changing the menu title. A subsequent normal reboot selected the persistent entry: its marker was present, PSR1/link-standby were active, tracked inputs were intact, the recovery timer was inactive, and the user confirmed the built-in screen worked. The user also reported repeated GNOME display-confirmation dialogs at GDM; the boot log traced these to a separate power helper targeting the dynamic-UID greeter twice. Session-class and greeter guards were installed in those local helpers; next-login confirmation of that separate fix remains outstanding.

Seventeen lifecycle tests passed, covering exact-option preservation, conflicting/missing flag rejection, recovery-unit exclusion, GRUB transient-field handling, update fallback, version ordering, and removal of only unchanged generated entries. Python and shell syntax checks passed. Installed systemd units passed `systemd-analyze verify`, and the installed guard reported all tracked inputs intact. Future package updates have not been performed as a live update simulation; event behavior is covered by the lifecycle tests.

## Automatic maintenance verification

Automatic maintenance was installed with an AC-only timer, local application/notification/login hooks, a one-time trial path, five-minute recovery, and a pre-login stale-image check. Sixteen new workflow tests passed (41 total across the three repository suites), as did Python syntax, desktop-entry validation and systemd unit checks.

A full forced build was executed against the current kernel and the cached, signature-verified Fedora source RPM. An initial extraction attempt failed safely because the RPM payload used `./`-prefixed archive names; that handling was corrected before rerunning. The second run applied both patches with fuzz disabled, compiled successfully, checked the module ABI and dependencies, signed with the enrolled local key, generated an isolated initramfs, and verified the embedded driver bytes. The run took approximately 3 minutes 29 seconds with two jobs and reported peak memory use of 2.4 GiB. A normal maintenance pass then reported the existing validated build intact. The working boot default was retained and no trial/reboot was scheduled.

The current-kernel build pipeline has passed; downloading a newly released source package, a future kernel version, offline-update recovery, and the new GUI trial/confirmation path still need real update validation. Mocked tests cover fallback and trial decisions; they are not physical backlight validation for future kernels.
