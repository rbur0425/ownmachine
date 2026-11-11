# Read-only native stability checks

The operator soak runner repeatedly exercises the native Hermes transport without
clicking, typing, changing control or restarting the VM. Run it with Python from
the Hermes installation, using the configured SSH alias and the **same underlying
control directory** as all other users of this VM:

```sh
python scripts/ownmachine-soak.py \
  --host-alias ownmachine-host --vm-name ownmachine \
  --control-dir /absolute/path/to/shared-control-directory \
  --samples 30 --interval-seconds 2 \
  --output /absolute/path/to/new-private-report.json
```

With Docker, use the container paths and Hermes Python environment. The control
database must already exist; the runner refuses to initialize missing state.
It takes the normal exclusive native session lock, so run it while the agent is
idle. The independent human browser viewer can remain connected and usable.
It neither reserves human control nor enables agent control. A change to the
controller or generation stops the run without reverting the operator's choice.

Each sample lists apps and windows. Add `--capture` to replace the window listing
with a native desktop PNG capture. This exercises the signed driver's actual
Screen Recording/capture-consent path. It requires the existing manual grants;
the script never approves a permission prompt. Captures and application/window
contents are never written to the report or printed. Images live briefly in
memory and are discarded after basic capture validation.

## Bounds and results

- `--samples`: 1–10000, default 30.
- `--interval-seconds`: 0.1–300, default 2, delay **between** samples. Requests do
  not overlap and there is no catch-up burst. Total elapsed time also includes
  startup, request latency and cleanup.
- `--connect-timeout-seconds` and `--action-timeout-seconds`: 1–120, default 15/30,
  as for native setup. Multi-request startup has more than one request bound.
- `--output`: a new file outside source with an existing parent. Existing files
  and symlinks are refused; the report is created with mode 0600.
- Ctrl-C records `interrupted` and closes the native session. Exit 0 means all
  requested samples completed, 1 means failure/stopped, and 130 means interrupted.

The report contains requested/completed counts, elapsed time, status, capture
mode and per-sample minimum/maximum/p50/p95 seconds. Percentiles use nearest-rank
ordering. Sample latency includes the app listing plus the window read or desktop
capture; it is not isolated screenshot encoding time or viewer frame rate.
No host identity, SSH errors, access token, screenshot, app name, window title or
input content is emitted. A failure stops the run; it never reconnects and repeats
the failed sample automatically. Read-only completion is not GUI semantic success.

A missing lease, unavailable provider, busy native session, failed read, control
change or interrupt produces an incomplete report. Use native doctor and the
[recovery guide](recovery.md) to investigate. Do not delete the lease or force a
control transfer just to make a stability run pass. Reports are evidence of the
requested duration/workload only, not a general uptime guarantee.

For a longer operator-invoked run, choose more samples and an interval appropriate
to the host's load. For example, 901 samples with a two-second delay take at least
30 minutes plus read/setup time. Capturing at that rate can consume meaningful
CPU/network resources. This command does not claim to measure browser latency,
write safety under a real lost GUI reply, restart persistence or firewall rules.
Those remain separate acceptance checks.

## Recorded live run

The Hermes container completed 60 native app-list-plus-desktop-capture samples
with a two-second delay between samples: 133.828 seconds elapsed, zero failed
samples and zero GUI writes. Sample latency was 0.250 seconds p50, 0.306 seconds
p95, 0.189 seconds minimum and 0.319 seconds maximum. The run completed without
a controller/generation change; captures were discarded rather than saved.
This is a roughly two-minute hardware check, not a 30-minute stability claim.

All 148 automated tests completed: macOS passed 135 with 13 Hermes-only skips;
Hermes passed 143 with five macOS-only skips. Plugin validation passed. Tests
cover missing state, busy sessions, interruption, sanitized errors, no retries,
control-change stopping, capture opt-in and private non-overwriting reports.

### Extended hardware run

The subsequent read-only hardware run completed all 901 requested captures over
2023.311 seconds (33 minutes 43 seconds), with zero failed samples and zero GUI
writes. App-list-plus-capture latency was 0.243 seconds p50, 0.304 seconds p95,
0.184 seconds minimum and 0.402 seconds maximum. The controller/generation did
not change during the run, and the independent noVNC viewer stayed usable under
human control. Images were discarded; only sanitized timing/status evidence was
retained outside source. This completes the extended **read-only** stability
check, not a sustained GUI-write or website-authentication test.
