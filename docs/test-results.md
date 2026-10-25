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

No boot identifiers, root filesystem UUIDs, serials, raw firmware data, process lists, private keys or credentials are included. Suspend/resume and battery-power outcomes remain unverified.

The exported build.sh was subsequently executed against the verified archive on the tested kernel. It completed successfully and produced an i915 module exposing both diagnostic parameters. This build-only verification did not alter the installed driver or boot settings.
