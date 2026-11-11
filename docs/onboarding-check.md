# Check onboarding readiness

Run the unified check from the source checkout on the **viewer machine as its
owner**, using the viewer's Python environment and its actual shared control
directory. This command combines the existing native and viewer doctors; it does
not provision, repair, start or restart anything.

```sh
"$HOME/.local/share/ownmachine-viewer-venv/bin/python" scripts/ownmachine-check.py \
  --host-alias ownmachine-host --vm-name ownmachine \
  --control-dir "$HOME/.local/state/ownmachine/control"
```

Replace the alias, VM and directory with your configuration. The alias must use
verified SSH keys and the restricted OwnMachine host relay. With Docker, use the
host bind-mount path to the shared control directory. The host check proves
access from its own process environment: it cannot prove the Hermes container
has the same SSH configuration, dependencies or mount. Also run
`hermes computer-use doctor` inside the actual Hermes environment.

The default checks native configuration, control state, host/guest readiness,
permissions and MCP discovery, then viewer authentication, control state and
streaming prerequisites. Both components are checked even if one fails, so a
broken guest does not hide an independently broken viewer. The first failure and
its remedy appear at the top of the human-readable output. Failures return exit
1; successful automatic checks return 0, possibly with warnings.

Intentional human reservation or paused control is a warning, not an instruction
to force agent access. An uncertain write remains a failure requiring inspection
and explicit acknowledgement. This command never transfers control or clears it.

## Options

- `--scope native`: check only native readiness, for a setup without a browser
  viewer or from inside Hermes. The report explicitly says the viewer was not
  checked. Manual browser checks remain listed for users who later add a viewer.
- `--probe-vnc`: explicitly add the viewer doctor's shared RFB authentication
  handshake. It requests no framebuffer and sends no input. Requires all checks;
  it cannot be combined with native-only scope.
- `--connect-timeout-seconds` and `--action-timeout-seconds`: configure the
  underlying connection/request bounds (1–120). Multiple sequential checks may
  take longer than a single timeout; this is not an overall runtime deadline.
- `--json`: emit a structured report with component-prefixed checks, pass/warn/fail
  counts, the first failure and the outstanding manual checks. It contains no
  access token, desktop data, configured endpoint or raw upstream exception.

The standard-library native checks do not require Hermes to be installed in the
viewer environment. The optional VNC handshake requires the viewer dependencies.
No extra dependency or capability is added to the installable plugin.

## What a passing report does not establish

The output always lists manual checks as unverified: real browser input, external
firewall coverage (including after physical host reboot), and saved-work guest
restart persistence. Those require deliberate operator tests. A successful local
HTTP check does not test your browser's SSH tunnel. A ready guest does not prove
a full agent task succeeds. The tool does not record or accept manual check marks
and cannot certify a release, clean-Mac installation or another deployment.

Use the [access helper](viewer-access.md) to obtain the current private link and
local tunnel command. For detailed recovery, consult the [viewer recovery guide](recovery.md)
and [native setup](native-provider.md). Save work before separately requesting
any lifecycle test. Do not reset the lease, bypass macOS permissions or weaken
SSH verification to make a diagnostic report pass.
