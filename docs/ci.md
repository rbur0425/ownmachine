# Automated validation

The Gitea Actions workflow runs tests and package checks on pushes to `develop`/`main`,
same-repository PRs into those branches, and manual
dispatch. It does not connect to the Mac, capture a desktop, run the soak tool,
change runtime configuration or deploy anything.

## Configure a runner and job image

Use a trusted Gitea runner with Docker job support. Configure these **repository
variables**, not source-code constants:

| Variable | Meaning |
| --- | --- |
| `OWNMACHINE_CI_RUNNER` | Runner label; defaults to `ubuntu-latest`. |
| `OWNMACHINE_CI_IMAGE` | Trusted job image with Python 3.10+, Hermes and its provider dependencies, Git, Bash and Node. Prefer an immutable image digest. |
| `OWNMACHINE_CI_PYTHON` | Python interpreter in that image; defaults to `python3`. Must import the installed Hermes public backend contract. |

The fallback image is only a bootstrap environment; the required Hermes check
fails if Hermes is absent. Missing Hermes never silently converts the required
job into a passing suite with all native contract tests skipped.

An optional image wrapper is provided:

```sh
docker build --build-arg HERMES_BASE_IMAGE=YOUR_TRUSTED_HERMES_IMAGE \
  -f ci/Dockerfile -t YOUR_CI_IMAGE ci
```

Use an image built from trusted Hermes source/dependencies, not `docker commit`
of a running agent with credentials. Do not mount the live Hermes home, SSH keys,
VM storage, control directory or host Docker socket into job containers. The
wrapper resets startup so CI does not launch an agent gateway. The CI command
uses temporary isolated Hermes homes and never initializes the real control gate.
The image must be available to the selected runner; local image names are useful
only when it uses the same Docker daemon. Supply your registry/digest as needed.

The checked-out action is pinned to an upstream commit and disables persisted
Git credentials. The workflow requests read-only repository permissions. Fork PR
jobs are deliberately skipped on the shared trusted runner: review them in an
isolated disposable runner before enabling untrusted contributions. The job condition is not an isolation boundary against modified workflow code.
Before accepting public contributions, also enforce server-side workflow approvals
and use disposable isolated runners for untrusted code. Runner
administrators remain responsible for isolation and access to their Docker daemon.
See [Gitea runner guidance](https://docs.gitea.com/runner/) for deployment choices.

## What the gate checks

Run the same gate manually from a clean, committed checkout:

```sh
YOUR_HERMES_PYTHON scripts/ci-check.py --require-hermes
```

It runs the complete unittest suite, checks whitespace, builds the same exact
commit twice, verifies both bundles and compares their bytes. It then unpacks
verified regular files into private temporary directories, installs a fresh
Hermes home from the source artifact, checks that the project license survives installation, and validates the source plugin, plugin
artifact and fresh-home package. Missing Hermes or any command failure fails
the gate. Temporary artifacts/homes are deleted after the check.

Without `--require-hermes`, local contributors can run the portable checks on a
machine without Hermes; the JSON summary explicitly reports that native contract
and package validation were unavailable. This mode is not the required CI gate.
Platform-specific macOS onboarding tests still require a separate Mac run; a green
Linux job is not full cross-platform or hardware acceptance.

No release files are uploaded, tagged or published by this workflow. The final
JSON summary identifies the exact source commit and completed checks. Logs contain
only synthetic fixture data and packaging diagnostics; keep hardware reports out
of CI artifacts. The tested Gitea status context is `Validation / hermes (pull_request)`.
It is required on this repository’s protected integration and release branches;
direct and force pushes remain prohibited. Other installations should verify
their actual reported context before adding the requirement.

## Why some tests skip, and where they run

The suite spans two environments. A successful run is not a claim that its
skipped tests passed:

| Test group | macOS without Hermes | Linux with Hermes |
| --- | --- | --- |
| Native provider contract (18 tests) | Skipped: Hermes public provider contract unavailable | Required to run |
| Native subprocess recovery (4 tests) | Skipped: same Hermes dependency | Required to run |
| Permission-guide installation/startup (10 tests) | Required to run using macOS plutil | Skipped: macOS utilities/LaunchAgent format unavailable |
| Other tests | Required to run | Required to run |

These counts describe the currently listed groups, not permanent totals. The
reviewable `ci/test-platforms.json` lists each platform-dependent test by full
identifier. When adding or renaming a platform test, update that file in the same
PR and verify it in the environment where it must run. Missing listed tests fail
the gate, so deleting or accidentally failing to discover one does not silently
reduce coverage. Skips require both the listed identifier and exact documented
reason. New skips, changed reasons and `expectedFailure` tests fail the gate.

Run the platform-aware test gate from any directory:

```sh
python3 /absolute/path/to/ownmachine/scripts/check-tests.py
```

On the Hermes test image use `--require-hermes`. That mode fails if Hermes is
missing, even if all native tests would otherwise be expected local skips. It
also refuses native test skips when the contract is available. macOS permission
tests may skip only off macOS. There is no flag to ignore unexpected skips.

Verbose unittest output goes to stderr; stdout contains a JSON summary with
actual passed count, failures/errors, each skipped test and category, missing
listed tests, platform and Hermes availability. An unfamiliar skip's raw reason
is omitted from the JSON summary. Normal unittest stderr remains a development
log, so fixtures must not contain live secrets. Both commands return nonzero on
policy violations or test failures. The full `ci-check.py` gate embeds this
coverage summary alongside package validation results.

The Linux Actions job provides required Hermes coverage. Run the macOS gate
separately for permission-guide coverage before merging changes to that flow.
This does not create a macOS runner or replace live VM acceptance; a green Linux
job alone still does not establish that the Mac-only tests passed.

The disposable fresh-home check also exercises the offline upgrader against a
synthetic prior-version package and receipt. It verifies configuration bytes are
preserved, compares the upgraded plugin to the verified artifact, and validates
it with Hermes. No running home or process is upgraded.

The CI job also runs `node tests/viewer-pointer.mjs` to exercise the vendored
noVNC mouse handler for zero-mask presses, releases and ordinary button chords.
Node is already required by the CI image; this separate browser regression does
not change the Python platform-skip matrix. Run it locally after viewer edits.

## Public GitHub validation

The GitHub workflow runs the offline gate on isolated hosted Linux and macOS
runners with Python 3.12 and Node 22. It validates the explicit platform skip
policy, repeatable bundles, extracted fresh-home installation and synthetic
upgrade fixtures. These jobs do not install Hermes and therefore do not claim
native-provider contract coverage. Release validation additionally runs
`ci-check.py --require-hermes` in a trusted Hermes environment and validates the
exact packaged plugin. Neither CI route performs live desktop acceptance.
