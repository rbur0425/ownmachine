# Browser viewing and VM lifecycle (development preview)

Complete [required identity and firewall setup](security-isolation.md) first.
The viewer key is separate from Hermes; access tokens live outside shared state.
Legacy frames mode is not available through the hardened viewer CLI.

To retrieve the current private link/token or generate a loopback tunnel command,
use the [viewer access helper](viewer-access.md).

The default viewer now uses [noVNC streaming](streaming.md). Follow that guide
for direct keyboard/mouse input, the host firewall prerequisite and viewer
dependencies. The screenshot/input-composer details below describe the optional
historical frame-mode implementation and earlier acceptance evidence; it is not
a supported CLI deployment under the split-key policy.

OwnMachine includes a private browser desktop with click, text, keyboard and scroll
controls, plus pause/resume, human reservation and VM start/shutdown/restart.
Frames come from a separate guest MCP session, by default once per second.
Input uses that same private MCP connection; VNC remains disabled. This is a
periodically refreshed remote desktop, not a high-frame-rate video stream.

## Guest prerequisites

Complete the native-provider and guided-permission setup. Run the updated MCP
installer as the guest desktop user:

```sh
bash scripts/install-guest-mcp.sh
```

It installs an Aqua LaunchAgent to reopen the signed driver at graphical login.
The guest must have a logged-in desktop; this does not bypass login or TCC. There
is no KeepAlive relaunch loop. The existing signed daemon must use standard mode.

Explicitly install the shutdown helper inside the guest as an operator:

```sh
sudo bash scripts/install-guest-lifecycle.sh YOUR_GUEST_ACCOUNT
```

This validates and installs a sudoers rule granting that account only
`/sbin/shutdown -h now` without a password. It installs a fixed per-user wrapper;
no password is stored in source or plugin state. Revoke this capability by
removing `/etc/sudoers.d/ownmachine-shutdown` as root. The runtime plugin never runs
this installer. Shut down ends applications; save work first.

## Host opt-in

Update the installed host relay. Add `"enable_lifecycle": true` to its private
`~/.config/ownmachine/host.json`, keeping the configured guest SSH alias and VM name.
Optional `"display_mode": "native"` opens the host's native viewer on startup;
the default is `"none"`. VNC remains disabled unless explicitly enabled through
the separate [streaming setup](streaming.md), regardless of display mode.

The forced command accepts exactly `start`, `stop` or `restart` for the one
configured VM. Lifecycle is disabled without this opt-in. It will not create,
pull, delete, clone or target an arbitrary VM. Start is idempotent for a running
VM. Stop requests shutdown over verified key-authenticated guest SSH and waits
for Lume to report stopped. **There is no force-stop fallback.** In particular it
does not use `lume stop`, whose normal timeout can force power off. A refused or
unconfirmed shutdown leaves the local control gate pending for operator review.

## Run the viewer

On the machine that holds the Hermes-side SSH identity, run from this checkout:

```sh
python3 viewer/server.py \
  --viewer-mode vnc \
  --host-alias ownmachine-viewer-host \
  --vm-name ownmachine \
  --control-dir /absolute/path/to/the/shared-control-directory
```

Use the **same underlying control directory** as the native provider. In Docker,
use the host path corresponding to that mounted directory; the paths may differ
inside/outside the container but must refer to the same files. Run as the same
UID, with access to its own verified SSH alias. The viewer uses only Python's
standard library and the OwnMachine modules. Only one viewer may own a control
directory at once. For an optional user service and the limits of login/boot startup, follow
[persistent installation](permanent-installation.md).

The server always binds `127.0.0.1`; there is no public-bind option. By default,
port 0 asks the OS to atomically assign a free ephemeral port. This avoids both
fixed-port collisions and a check-then-bind race. Optional `--port NUMBER`
requests a preferred port; if it is occupied, the viewer falls back to an
OS-assigned free port. The actual port is printed at startup and recorded as
`port` in the access file. Other bind failures are reported without being hidden.
It writes a
private `viewer-access.json` under the separate access directory, mode 0600, containing
the authenticated browser link. Keep that link private: it authorizes viewing,
desktop input, control transfers and lifecycle operations. Do not put it in an agent prompt,
repository or public proxy URL. The fragment is removed from browser history
when loaded. It is exchanged for an HttpOnly, SameSite=Strict browser-session
cookie, so another tab in the same browser can open the plain address. A fresh
browser shows an unlock form for the private link or token instead of disabled
workspace controls. The cookie has no persistent expiry, although browsers may
restore session cookies with restored tabs. Server restart
rotates the token; reopen the newly generated private link.

From another computer, read the actual port from startup output or the access file, then forward that
same loopback port through your SSH account (replace both port placeholders):

```sh
ssh -N -L 127.0.0.1:YOUR_VIEWER_PORT:127.0.0.1:YOUR_VIEWER_PORT YOUR_VIEWER_SERVER_SSH_ALIAS
```

Open the private link locally after establishing the tunnel. Using the same port on both ends is simplest. If that port is occupied on your
local computer, choose another free local forwarding port and change the port
in the private browser link to match. Only loopback Host names are accepted and
the browser Origin must match the address in that link. No proxy,
Cloudflare, LAN listener, Docker port publication or public authentication is
configured automatically. Status/frames/actions require the token; action POSTs
also enforce same-origin policy. Static assets contain no token or desktop data.
The server suppresses request logging and sends no-store/no-referrer headers.
No capture is written to disk by the viewer itself. A stale frame is dimmed and
marked unavailable rather than presented as a current desktop.

## Controls and recovery

- **Pause agent** blocks both agent and browser input. **Reserve for human use**
  blocks agent writes and enables browser input after a fresh frame. The server
  enforces the human lease independently of disabled UI buttons.
- **Return to agent** increments the control generation. Old snapshots cannot be
  used; the agent must capture again before writing.
- **Start / Shut down / Restart** wait for active writes, invalidate old captures,
  and leave the controller paused. Save work before shutdown/restart. The browser
  confirms these actions; backend dispatch remains single-shot without retries.
- If an operation fails or its outcome is unknown, inspect the native guest view
  and host state first. Explicitly acknowledge that uncertainty when transferring
  control. Lifecycle will refuse to run while an earlier outcome is pending.
- A VM reported running may still be booting. The preview reconnects when the
  graphical login and signed driver are ready. No automatic input is sent.

The same lifecycle actions are available to an operator from the source checkout:

```sh
python3 scripts/ownmachine-vm.py restart \
  --host-alias ownmachine-viewer-host --vm-name ownmachine \
  --control-dir /absolute/path/to/the/shared-control-directory
```

They are not model-facing tools. The native plugin status reports the viewer's
heartbeat without disclosing its access token. This remains a trusted-operator
system: raw SSH credential holders or clients configured with a different control
directory can bypass local coordination. A loopback token is not a multi-user
identity system. Keep the existing single-operator trust boundary.


## Earlier lifecycle acceptance evidence

The private viewer was opened in a browser through an SSH loopback tunnel. It
showed changing guest frames and current control state. Returning control through
the browser invalidated an active native backend's old capture (`stale_target`);
human reservation then blocked its input (`human_takeover`). No input was sent by
the viewer. Browser shutdown produced a stopped VM and a visibly unavailable
preview. Browser start brought back the VM, graphical login, signed driver and
live frames. The separate Restart button also completed a full cycle, ending
with the VM running and agent control paused.

The plain-text acceptance file created by the native Hermes provider remained on
disk. It did not automatically reopen after OS shutdown; the operator reopened
it normally in TextEdit, then native AX readback confirmed the original content.
Guest TCC grants and recorded capture consent persisted, and VNC stayed disabled.
These checks cover a guest restart, not a cold reboot of the physical Mac host.
Browser input was not part of that earlier test; it is covered separately below.
That earlier test used frame mode; later noVNC streaming acceptance is documented
in [streaming setup](streaming.md) and [laptop acceptance](laptop-acceptance.md).

Final validation discovered 73 tests: 64 passed locally with nine Hermes-only
skips; 68 passed in the Hermes container with five macOS-only skips. The two
environments together exercised every test. Hermes plugin validation passed.
The deployed viewer listener was confirmed to bind only to loopback.

## Frame-mode browser input and configuration

Reserve for human use, then click a field in the displayed desktop. Select
single, double or right click using **Click mode**. Compose up to 4096 characters
in **Text to type in the VM**, then press **Send text**. Text is sent as one action
and cleared only after success. The buttons send Enter, Tab, Escape, Backspace,
arrows, Select all, Undo, Copy/Paste within the VM and scroll. These controls
avoid forwarding browser shortcuts or accidentally typing while editing local
text. Physical keyboard events are not globally forwarded. Copy/Paste operates
on the **guest** clipboard; clipboard synchronization, drag, file transfer and
continuous mouse movement are not implemented.

Coordinates account for browser scaling and letterboxing. The server accepts
only a recently displayed frame (at most five seconds old), from the current
control generation and the current image dimensions. Capture and input are
serialized. A click uses the latest matching-size driver capture ID for the
session's coordinate mapping. Screen content can change between frames, so
inspect the result of each action. Each dispatched input consumes all preceding
frame tokens; a duplicate request cannot repeat it. A fresh frame is required
for the next action. Failed/unknown dispatched input retains the shared pending
marker for explicit operator review. There is no automatic input retry.

All mutations hold the same SQLite write gate as the native provider, with a
human-controller requirement. Transfers wait for in-flight dispatch. Lifecycle
operations invalidate frame tokens and leave control paused. UI actions use a
bounded server allowlist; arbitrary driver tool names/arguments are refused.
Text, keys and raw driver errors are not logged or returned in error reports.

| Viewer option | Default | Purpose |
|---|---|---|
| `--host-alias` | required | Operator SSH alias |
| `--vm-name` | `ownmachine` | Configured VM allowlist identity |
| `--control-dir` | required | Shared control state |
| `--port` | `0` | Automatic free port; occupied preferred ports fall back |
| `--frame-interval` | `1.0` | Capture seconds, 0.25–10; inputs require frames younger than five seconds |
| `--max-image-dimension` | `1280` | Long-edge pixel cap, 640–3840 |
| `--read-only` | off | Server-enforced refusal of all browser input |
| `--connect-timeout-seconds` | `15` | SSH connection limit, 1–120 |
| `--action-timeout-seconds` | `30` | MCP call limit, 1–120 |

## Interactive acceptance evidence

Through the actual browser UI, a click on the displayed guest File menu opened
it; a second click selected New in TextEdit. Send text entered a two-line test
message into that new document, and the Enter button followed by another text
submission added a third line. Screenshots verified the guest result. These
were browser-dispatched MCP actions, not SSH text insertion. Existing documents
were left intact. Additional automated tests cover frame expiry/resize,
server-enforced human-only input and read-only mode, duplicate refusal,
authentication/origin rejection, invalid payloads and coordinates, uncertain
outcomes and transfer waiting for a human write.

The browser Pause, Return to agent and Reserve for human use controls were
exercised. Start on the already-running VM completed idempotently and left
control paused; human reservation was restored for testing. Shutdown/restart
hardware evidence is from the earlier lifecycle phase above, not a new shutdown
of the unsaved interactive test document. Final automated suite: 102 tests,
93 passed on macOS (nine Hermes-only skips) and 97 in Hermes (five macOS-only
skips); together every test ran. Installed plugin validation passed.

Access follow-up: a clean browser context reproduced the unauthenticated bare-link
failure. The unlock flow and browser-session authentication were verified,
including a second tab opened with only the plain URL. Human reservation and
text dispatch worked from that tab. The suite now has 103 tests: 94 pass locally
with nine Hermes-only skips; 98 pass in Hermes with five macOS-only skips.
This patch does not add VNC/video streaming or physical keyboard forwarding.
