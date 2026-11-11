# Native Hermes provider (development preview)

Tested with Hermes 0.23.1, Cua Driver 0.44.0 and Lume 0.7.0. The provider runs
on Linux or macOS with OpenSSH. It implements the synchronous ComputerUseBackend
contract without modifying Hermes core. Standard permission mode is supported;
bounded and unrestricted are refused. Hermes's own action approvals remain active.

## Enable the private transport

Complete [guest provisioning](vm-setup.md) and all guided permission checks first.
Inside the guest, as its desktop user, run from this checkout:

```sh
bash scripts/install-guest-mcp.sh
```

The per-user launcher checks the pinned driver version and requires an already
running standard-mode signed daemon. It neither starts a daemon nor changes TCC
or authorization settings. To start the installed signed app when needed:

```sh
open -g -a /Applications/CuaDriver.app --args serve --no-permissions-gate
```

Copy the updated `host/ownmachine_host.py` to the host relay installation described
in [host setup](host-setup.md). In the operator-owned host JSON, keep the selected
VM and verified guest SSH alias and add `"enable_mcp": true`. MCP is disabled by
default. The forced command now also accepts exactly
`ownmachine-host mcp --vm YOUR_CONFIGURED_VM`. It resolves that running VM's current
address through Lume, then execs key-authenticated SSH to the fixed guest launcher.
No arbitrary destination, command, VM creation, or VNC secret is accepted or emitted.

## Select the provider

Install only `plugin/` under the active Hermes home's `plugins/ownmachine`. The
current Hermes category-provider loader requires `plugins.isolation: in_process`;
this is a profile-wide setting, so use a dedicated profile/home if other plugins
need host isolation. A separate Hermes home can select OwnMachine with a private
config file and its own plugin installation, then run with
`HERMES_HOME=/absolute/path/to/that/home hermes ...`. Configure:

```yaml
plugins:
  isolation: in_process
  entries:
    ownmachine:
      enabled: true
      settings:
        host_alias: ownmachine-host
        vm_name: ownmachine
        control_dir: /absolute/operator-owned/shared-control-directory
        connect_timeout_seconds: 15
        action_timeout_seconds: 30
computer_use:
  backend: ownmachine
  permission_mode: standard
```

All profiles and processes targeting this VM **must share the same control_dir**.
The directory is outside source and holds only the control database/session lock.
There is no default that silently isolates different profiles' control gates.
One native backend session holds the exclusive session lock until it closes.
SSH identities remain in operator configuration; the plugin does not read key files.

Run `hermes computer-use doctor` in that profile. It now reports individual readiness checks and recovery advice, including
host/guest state, permissions, control state and a real MCP initialize/tools-list
exchange. See [community setup and recovery](community-setup.md). Screenshots and desktop input are
not part of doctor. The CLI expects your normal model/vision settings for a full
agent chat; the transport and provider do not supply model credentials.

## Give and take control

New control state is paused. From the source checkout, run as the trusted operator:

```sh
python scripts/ownmachine-control.py --control-dir /absolute/operator-owned/shared-control-directory status
python scripts/ownmachine-control.py --control-dir /absolute/operator-owned/shared-control-directory agent
python scripts/ownmachine-control.py --control-dir /absolute/operator-owned/shared-control-directory human
python scripts/ownmachine-control.py --control-dir /absolute/operator-owned/shared-control-directory paused
```

These commands are not registered as agent tools. A transfer waits for any active
write, increments the generation, and invalidates prior targets. After returning
control to the agent, it must capture before sending input. After a failed or
interrupted write, inspect the guest before transferring control: the transfer
acknowledges the uncertain outcome. Never assume timed-out input did not happen.

This is a trusted single-operator gate, not a remote authentication boundary.
A process with the SSH identity can run MCP directly outside this provider, and
an operator can configure a different control directory. The local VM viewer is
also a trusted operator surface; browser input also requires the human lease on the server.

## Supported behavior and limitations

- Desktop PNG capture (`app: screen`), exact-window PNG/AX capture, and app/window lists.
- Numbered SoM images and one-based AX indices mapped to opaque driver snapshot
  tokens. Pillow, normally supplied by Hermes, draws labels; without it the
  provider explicitly returns vision plus the AX tree, without claiming overlays.
- Left/right/double clicks, text, key combinations, scroll, AX set_value, and app
  selection/focus. An AX node need not support AXPress; inspect and choose a pixel
  action when appropriate. There is no automatic fallback that repeats an input.
- Pixel coordinates are in the returned screenshot. AX bounds are translated to
  that window-local image space where provable. AX-only captures cannot ground
  pixel input. A failed capture disarms the old target.
- Drag, middle-click and modified pointer gestures return `unsupported_action`.
- Structured driver effects and escalation advice are retained. Transport success
  is not semantic success; verify `unverifiable` actions with a fresh capture.
- MCP frames, I/O time and discovery pagination are bounded. No CLI fallback or
  automatic write retry exists. A later explicit read may reconnect, but cannot
  clear a pending failed-write marker. Unknown/failed writes require operator review.
- Closing the backend closes SSH/MCP and releases the local session lock; it does
  not stop the VM or the signed desktop daemon. See [viewer/lifecycle setup](viewer-lifecycle.md) for the optional driver login
  launcher, lifecycle controls, interactive browser desktop and control transfers.

## Verification recorded for this change

The real Hermes provider loader and `computer_use` handler were exercised in a
separate test profile with standard approvals, not by replacing Hermes dispatch.
The native tool created a fresh TextEdit document, converted it to plain text,
typed an acceptance message, and saved a named `.txt` file using its GUI Save
sheet. AX readback and the final screenshot confirmed the content and saved title.
No model was used to author the test sequence. The test home's auxiliary vision
credentials were absent, so screenshot analysis by an LLM was not verified; PNG
capture itself succeeded and was inspected directly. Guest SSH could stat the
saved file but macOS denied reading Documents through SSH; that restriction was
not bypassed.

The backend also passed live AX menu click, pixel click, scroll delivery,
read reconnect, and paused/human/stale-generation refusal checks. The driver
reported click/scroll delivery as unverifiable; these are not claims of a semantic
scroll effect on a short document. Fake-peer tests cover EOF, timeout, oversized
frames, mismatched IDs, and absence of replay. Contract tests run against the
installed Hermes ABC and cover tokens, verdicts, exclusive session ownership,
failed-write markers and disarmed targets. Captures and deployment identities
are stored outside the repository.

Final validation: 54 tests discovered. Local macOS passed 45 and skipped nine
Hermes-contract tests because Hermes is not installed there. The Hermes container
passed 49 and skipped five macOS-only onboarding tests. Together these runs
exercise every test. The installed plugin passed Hermes validation and the native
profile's doctor completed its MCP handshake. Control was left paused afterward.

## Window targeting and operator review

The pinned Cua 0.44.0 contract defines larger `z_index` values as nearer the
front. OwnMachine selects the highest known index among visible/current-space
candidates, consistently for capture and focus. Multiple candidates with unknown
or tied front ordering require an explicit window ID. Array order is not evidence
of stacking. See the [pinned upstream contract](https://github.com/trycua/cua/blob/cua-driver-rs-v0.44.0/libs/cua-driver/rust/Skills/cua-driver/WORKFLOW.md).

Capture the desktop or intended window before launching/focusing or sending
input. AX text areas may not support AXPress: choose `set_value` for an exposed
writable value or a freshly grounded pixel action when appropriate. A failed
mutating action retains the pending marker; neither the agent nor a fallback
route may retry until the operator inspects and acknowledges it. A follow-up
blocked by that marker explicitly reports that no new action was dispatched.
