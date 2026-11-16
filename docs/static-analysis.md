# Static analysis

OwnMachine v1.1.1 adds reviewable automated checks without adding analyzers to the
installed plugin. These checks complement Hermes validation, runtime permission
checks and VM acceptance; they do not prove an installation is secure.

## Running the checks

Use Python 3.12 and Go 1.25 in a development environment:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r ci/analysis-requirements.txt
go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
export PATH="$(go env GOPATH)/bin:$PATH"
python scripts/static-analysis.py --output-dir /tmp/ownmachine-analysis
python scripts/audit-dependencies.py --output /tmp/ownmachine-audit/dependencies.json
```

Output paths are caller-configurable. Use separate output directories per run.
The dependency audit needs network access and resolves dependency ranges; analyzer
installation needs PyPI and the Go module proxy. Scanning itself does not connect
to VMs, read Hermes credentials or alter an installed plugin.

## CI policy

| Check | Scope | Gate |
| --- | --- | --- |
| Ruff | Repository Python, excluding vendored noVNC | F and E9 correctness findings fail |
| Bandit | Plugin, host, viewer, scripts and experiments; no vendored code or test fixtures | Medium/high findings fail; all low findings are retained in a separate report |
| ShellCheck | All tracked shell scripts except vendored code | Every reported level fails |
| actionlint | GitHub workflows | All findings fail |
| zizmor | GitHub workflows, offline analysis | All default findings fail |
| mypy | Config, MCP transport and setup transport | All findings in the initial scope fail |
| OwnMachine AST rules | First-party production Python and experiments | Unreviewed findings and stale exceptions fail |
| pip-audit | Resolved plugin manifest dependencies plus viewer requirements and transitives | Known vulnerabilities or audit errors fail |

All analyzers run even when one fails. Reports are uploaded for 14 days, including
on failure. Tool versions and action commits are pinned. The workflow uses read-only
repository permissions and does not persist checkout credentials or enable caches.
It runs on PRs, integration/release pushes, manual requests and Mondays at 14:23 UTC.
GitHub schedules start only after the workflow reaches the default branch.

CI failures are not bypassed with `continue-on-error`. Branch-protection required
checks are a repository setting: add **Code and security analysis** and **Runtime
dependency audit** after their first reviewed green run. This PR does not alter
branch protection or grant analyzer jobs write permissions.

## Security regression rules

- OM001: explicit allowlisted environments at known SSH/Hermes transport boundaries;
  missing environments, full `os.environ` inheritance and unrecognized expressions fail.
- OM002: shell-enabled subprocess calls and `os.system` require review.
- OM003: literal password-bearing VNC argv lists are refused; use a private file.
- OM004: direct logging of named password/token variables is refused.
- OM005: the audited viewer-access file creation uses `O_CREAT|O_NOFOLLOW` and 0600.
- OM006: the audited shared control directory creation uses explicit 0700.

Negative regression tests introduce insecure examples and verify rejection. These
are bounded AST checks, not interprocedural taint analysis: arbitrary aliases,
reflection, generated shell/Python strings and indirect secret flows still require
review and runtime tests. Refactoring the audited file/directory creation sites
requires updating their rules and tests; removing the known site fails closed.

`ci/security-exceptions.json` contains three exact source-expression fingerprints:
the restricted viewer SSH protocol intentionally returns VNC authentication metadata,
and the owner-only access CLI can explicitly print a URL/token on request. These
are intentional secret delivery, not routine logging. New or changed output needs
review; stale exceptions fail. Each has a written rationale.

## Initial findings and fixes

Initial scan of the v1.1.0 code, before analyzer infrastructure changes:

| Analyzer | Initial results | Disposition |
| --- | --- | --- |
| Ruff | 32 unused imports, 1 unused assignment | Removed unused code; retained one optional-Hermes availability import with a specific explanation |
| Bandit | 206: 194 low, 9 medium, 3 high | Reviewed medium/high sites as described below; low findings remain visible |
| ShellCheck | 2 informational warnings | Explicit conditional for startup attempts; documented host-provided `/etc/os-release` source |
| actionlint | 0 | Clean |
| zizmor | 1 low-confidence/high-severity cache warning | Disabled implicit setup-node package-manager caching |
| mypy | 14 errors in 3 files | Separate string/integer loop variables, explicit missing-pipe checks and safe cleanup; preserved deadline behavior |
| Dependency audit | 0 known vulnerabilities | Resolved Pillow 13.0.0, websockets 15.0.1, PyCryptodome 3.23.0 |

Bandit exceptions are per-line and per-rule, with rationale adjacent to the code:

- Seven XML parses consume local libvirt-generated XML from fixed `virsh` commands,
  rather than guest or network-supplied XML. No new XML dependency was added.
- Two downloads construct HTTPS URLs from pinned upstream sources and verify content
  hashes before use. These are not arbitrary URL-fetch APIs.
- RFB/VNC authentication requires DES. The `Crypto` namespace comes from pinned,
  maintained PyCryptodome, not the retired PyCrypto package. Its challenge exchange
  is inside the restricted viewer SSH channel. Replacing it with AES would break RFB.
- WebSocket handshake SHA-1 is protocol framing, not password hashing or a signature.
  It now explicitly uses `usedforsecurity=False`.

Low-severity inventory includes subprocess imports/execution, PATH-based executable
resolution, XML imports, boolean password-status keys and two intentional exception
handlers during cancelled chat setup. These are review prompts, not 194 confirmed
vulnerabilities. They are **not** all proved safe or silently baselined: review remains
necessary, and new medium/high findings block CI. There is no global `nosec` exclusion.

Dependency results are a point-in-time check of the resolved set, not a claim that
every version permitted by a range is vulnerability-free. Hermes core dependencies,
OS packages, upstream guest binaries and vendored JavaScript require their own
update/review policy. mypy's remaining modules are outside the initial scope, and
untyped function boundaries still limit inference.

The first local pip-audit attempt hit an `ensurepip` crash in the uv-managed Python
build. The local audit then used uv to resolve the complete set and pip-audit with
`--disable-pip --no-deps` on those exact pins; CI exercises normal pip-audit isolated
resolution on setup-python. Neither path disables advisory checks.

## Tool references

[Ruff correctness rules](https://docs.astral.sh/ruff/rules/),
[Bandit](https://bandit.readthedocs.io/),
[ShellCheck](https://www.shellcheck.net/),
[actionlint](https://github.com/rhysd/actionlint),
[zizmor](https://docs.zizmor.sh/),
[mypy](https://mypy.readthedocs.io/),
[pip-audit](https://github.com/pypa/pip-audit).
