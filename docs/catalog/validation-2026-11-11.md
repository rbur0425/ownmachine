# Current Hermes catalog validation — 2026-11-11

## Scope and revisions

OwnMachine runtime/plugin source is unchanged from v0.6.0
(`8431db09c3abd251ba1f2d18a2f09d127816a119`). This preparation adds documentation
and real viewer screenshots; the draft catalog entry identifies the exact
content commit to review:
`5966a19820aae0b5bb574b26d065cc0ebb9b1365`. The subsequent preparation commit
adds the YAML and this final validation record; it does not change the pinned
plugin, screenshots or runtime. Nothing was submitted to Hermes.

Hermes upstream `main` was resolved and checked out at
`3bcd071226d3d605a2bb3b4f3933e7d583e189d6`. Its Git description was
`v0.23.1+canary.20261111T064456Z-40-g3bcd071226`. This is a pinned development
revision, not a claim that every future Hermes release is compatible.

A separate macOS ARM64 checkout, isolated Hermes homes and upstream's locked
`setup-pm` Python toolchain were used. Python 3.14.9 and uv 0.13.5 came from
Hermes's PM lock. The machine's older uv could not parse the current lock format;
the upstream toolchain resolved that without editing dependency pins or changing
the running Hermes installation. No model credentials or live deployment SSH
configuration were supplied to the validator or offline tests.

## Results

| Check | Result |
| --- | --- |
| `hermes plugins validate /path/to/plugin --install-deps` | Passed |
| Manifest, compatibility spec, configuration and environment declarations | Passed |
| Loadable entrypoint and isolated capability probe | Passed |
| Declared tools/hooks/middleware and built-in tool collisions | Passed |
| Python dependencies | None declared |
| OAuth declaration | None |
| Security scanner | Safe |
| Runtime overrides of Hermes core | None detected |
| Local `python3 -m unittest discover -s tests -v` | 229 run; 207 passed, 22 expected Hermes-only skips |
| Current-Hermes `python scripts/check-tests.py --require-hermes` on macOS | 229 passed; no skips, failures or errors |
| Upstream catalog schema validator | One draft entry valid |
| Upstream `scripts/ci/catalog_validate_pinned_entries.py` | Passed against a fresh public clone at the exact draft SHA |
| Pinned source confinement, executable-payload and self-updater gates | Passed |
| Pinned screenshot URLs | Both downloaded publicly and matched reviewed local bytes |
| Pinned root/package licenses | Byte-identical PolyForm Noncommercial 1.0.0 |
| Node viewer pointer regression | Passed |

The validator reports the default plugin-host isolation setting. The documented
native computer-use deployment requires in-process loading; the current-Hermes
suite separately exercises native provider discovery with that configuration.
A capability-probe pass alone is not proof of live VM control.

The pinned-source script ran locally without modification, using the same Hermes
revision and a restricted environment with no SSH agent or GitHub/model tokens.
On macOS its GNU `timeout` dependency was supplied through the tool PATH. Its
fresh-clone result does not substitute for the future upstream Linux CI run.

## Policy and acceptance limits

- The owner confirmed on 2026-11-11 that PolyForm and delegated OpenSSH are
  acceptable. This is owner-reported policy confirmation, not a scanner finding
  or catalog admission; upstream review is still required.
- No browser-vault or login-backend registration exists. No credentials were
  moved into environment variables or files to work around Hermes's rules.
- The screenshot session exercised actual browser input and human/agent handoff,
  then left control paused. It was not a new model-driven desktop benchmark.
- No new host reboot, ALF-only random-port test, cloud Mac test or VM-backup test
  was performed. Existing security preview limitations still apply.

## Reproduce without deployment-specific configuration

Use an isolated checkout of the pinned Hermes revision and its documented locked
PM setup. Select that environment's Python and Hermes CLI, with a fresh
`HERMES_HOME`, and check out OwnMachine at the draft entry's full `sha`:

```sh
hermes plugins validate /path/to/ownmachine/plugin --install-deps
python /path/to/ownmachine/scripts/check-tests.py --require-hermes
python /path/to/hermes/scripts/validate_plugin_catalog.py /path/to/ownmachine.yaml
```

Paths are operator-selected. Validation does not need a real SSH alias, viewer
access token, model credential or running VM. Schema success and local checks
still require upstream admission CI and maintainer review before listing.
