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
