# noVNC streaming desktop

Complete [required identity and firewall setup](security-isolation.md) first.
The viewer key is separate from Hermes; access tokens live outside shared state.
Legacy frames mode is not available through the hardened viewer CLI.

The default operator viewer now uses noVNC 1.6.0 and a continuous RFB/WebSocket
connection. Click inside the desktop and type normally; mouse movement, button
press/release, dragging, wheel scrolling and keyboard shortcuts are delivered to
the guest. Native Hermes computer use uses MCP; the separate viewer key cannot
open MCP sessions.

## Host prerequisites and firewall

Build the protected-password-file Lume patch, set `lume_path` to its executable,
and update the restricted host relay, then explicitly opt into VNC in the host's
operator-owned `~/.config/ownmachine/host.json`:

```json
{
  "vm_name": "ownmachine",
  "guest_ssh_alias": "ownmachine-guest",
  "enable_mcp": true,
  "enable_lifecycle": true,
  "enable_vnc": true,
  "vnc_port": 59501,
  "display_mode": "none"
}
```

Retain your existing custom `lume_path`, VM and guest alias. The example port is
a placeholder preference: choose an unused host port, and apply the same port to
the firewall. A fixed port is needed for a narrow firewall rule. Lume refuses an
occupied explicit VNC port; it does not silently move outside that rule. The
browser HTTP port is separate and still selects a free port automatically.

**Lume 0.7.0 binds its VNC listener to all interfaces. A localhost URL does not
mean a loopback-only listener.** Before production use, restrict that host port
to loopback with the Mac's firewall. The required operator installer needs
administrator privileges on the Mac:

```sh
sudo bash scripts/install-vnc-firewall.sh YOUR_VNC_PORT /absolute/path/to/lume.app
```

macOS may print `No ALTQ support in kernel` and
`ALTQ related functions disabled`. These messages are harmless for this setup:
ALTQ provides traffic queuing, which OwnMachine's port-blocking rule does not use.
You can proceed when the installer finishes successfully with
`OwnMachine VNC port YOUR_VNC_PORT is restricted to loopback.` (showing your chosen
port). An ALTQ message alone does not confirm success; resolve any actual error
or missing success message before enabling VNC. Complete the external blocking
check below as well.

It installs a narrow PF rule under `com.apple/ownmachine`, plus a root LaunchDaemon
that reloads/checks it at host boot and every 15 seconds. It also enables the
application firewall and blocks Lume across ports. Fresh root-owned status is
required by the relay before starting or opening VNC. It requires the standard `com.apple/*` anchor to
already exist in the loaded PF configuration; otherwise it stops without
replacing global rules. It does not flush or replace existing firewall rules.
Review it with your firewall administrator if you use a custom PF setup. Verify
from a different machine that direct access is blocked, while the local SSH
relay still connects. For an existing running VM, save work and gracefully
restart through the operator controls to apply VNC settings. Never force stop.
If firewall setup is incomplete, keep `enable_vnc` false for routine operation.

VNC credentials remain private Lume runtime data on the host. Protect that
account, Lume session files and logs. The relay reads the configured VM's current
loopback URL and opens only that socket; it accepts no browser-supplied host,
port, VM or shell command. Credentials travel only inside the verified SSH pipe.
The Python bridge terminates VNC challenge-response authentication before the
browser RFB handshake, so the VNC password never reaches JavaScript, model tools
or browser URLs. Raw host/SSH credential holders remain trusted operators.

## Viewer installation

Use a separate Python environment outside the source checkout or installed
Hermes package, for example:

```sh
python3 -m venv "$HOME/.local/share/ownmachine-viewer-venv"
"$HOME/.local/share/ownmachine-viewer-venv/bin/pip" install -r viewer/requirements.txt
"$HOME/.local/share/ownmachine-viewer-venv/bin/python" viewer/server.py \
  --host-alias ownmachine-viewer-host --vm-name ownmachine \
  --control-dir /absolute/path/to/shared-control-directory
```

PyCryptodome is pinned for legacy VNC DES authentication compatibility, not for
new cryptographic protocol design. noVNC JavaScript is bundled as inspectable
source with its licenses; there is no runtime CDN or self-update. Neither is
installed into the Hermes plugin. See [dependency provenance](../viewer/VENDOR.md).

The browser endpoint always binds loopback and uses the existing authenticated
access link/session-cookie flow and SSH tunnel. WebSocket upgrades require the
same authentication and an exact same-origin check. The VNC endpoint on the Mac
is never the browser URL. Save the private link outside source and agent prompts.

| Option | Default | Purpose |
| --- | --- | --- |
| `--viewer-mode` | `vnc` | `vnc` streaming only |
| `--read-only` | off | Server-enforced refusal of browser input |
| `--quality` | `6` | noVNC quality preference, 0–9; server encoding support determines effect |
| `--compression` | `2` | noVNC compression preference, 0–9 |
| `--swap-red-blue` | off | Correct servers that ignore requested RGB channel order; needed by the tested Lume VNC server |
| `--host-alias` | required | Verified SSH alias for the restricted host relay |
| `--vm-name` | `ownmachine` | Host relay's configured VM |
| `--control-dir` | required | Same underlying shared gate directory as every agent/operator |
| `--access-dir` | viewer user state directory | Private bearer file outside shared control |
| `--port` | `0` | Free browser HTTP port; occupied preferred ports fall back |
| `--connect-timeout-seconds` | `15` | SSH connection bound, 1–120 |
| `--action-timeout-seconds` | `30` | Operator action timeout, 1–120 |

The color correction applies only to the rendered streaming canvas. It is an
explicit compatibility option, not a modified noVNC decoder. Stream size follows
the VM's configured display; the canvas scales to the browser viewport and
preserves pointer coordinates. Browser resizing does not resize the guest.
Legacy screenshot options do not affect VNC streaming.

## Human-control boundary

For connection or input problems, run the operator-only [viewer doctor](recovery.md)
with the viewer Python environment. Its optional VNC probe does not capture,
send input, transfer control or restart the guest.

- **Pause agent:** neither browser nor native agent may write; viewing continues.
- **Reserve for human use:** the server accepts direct browser input and blocks
  native writes. Click the canvas to give keyboard focus to the guest.
- **Return to agent:** streaming connections are closed, pressed keys/buttons
  are released, the lease generation changes, and clients reconnect view-only.
  The agent must capture fresh state before writing.
- **Start/Restart/Shut down:** stop viewer input first and leave control paused.
  Save work before shutdown/restart. Closing a browser never stops the VM.

The bridge parses complete RFB client messages across WebSocket fragments.
Only display negotiation/update requests and standard key/pointer events are
accepted. Every input event is guarded by the same SQLite human lease as native
Hermes writes. A key or button held down retains the write transaction until
release, preventing handoff in the middle of a modifier or drag. The browser
control endpoints first close streams and release held inputs; external CLI
transfers may wait or time out while a key is held. An abandoned hold is capped
at 30 seconds. Failed input leaves an uncertain marker; there is no replay.

One streaming connection at a time owns browser input; other connections can
watch. Returning/reserving control resets ownership. Up to four simultaneous
streams are admitted. The page's view-only setting improves usability, but
server-side parsing and the lease enforce the gate even for a modified client.

Clipboard synchronization, file transfer, guest display-resize requests and VNC
power-control extensions are not admitted. Ordinary Copy/Paste shortcuts work
inside the guest. Browser/OS-reserved shortcuts can remain local depending on
the browser; click outside the canvas to return focus to browser controls.
RFB provides continuous desktop updates, not a promised fixed frame rate or
video-codec latency guarantee. Performance depends on the guest, encoding,
network and browser. Do not expose this single-operator service publicly.

## Recorded verification

The live browser completed a noVNC connection over the SSH relay, displayed the
1920×1200 guest desktop, opened apps through direct keyboard shortcuts, typed
into a new TextEdit document without the text composer, and moved its window by
dragging the title bar. Guest AX readback confirmed an exact keyboard test marker
and a longer alphabet/number burst. macOS text correction remains an OS setting.
The red/blue correction was checked visually against native guest screenshots.

While paused, a deliberately injected raw RFB key message did not enter the
text document. The native Hermes backend returned `human_takeover` while browser
control was reserved for a human. Automated tests cover key/button holds,
release before transfer, failed writes/pending state, stale generation,
read-only mode, WebSocket fragmentation/masking, disallowed protocol extensions,
clipboard suppression, authentication/origin checks and fixed host routing.

The host's VNC listener was observed on all interfaces. After an administrator
installed the loopback-only PF rule, a connection from a different machine was
blocked. A fresh browser stream still connected through the local SSH relay;
newly typed text was confirmed through guest AX readback. Firewall persistence
was subsequently checked on the configured IPv4 LAN path after a physical-host
reboot; see the qualified [reboot result](hardware-acceptance.md#physical-host-reboot-follow-up--2026-11-10).

118 tests completed: macOS passed 109 with nine Hermes-only skips; the Hermes
container passed 113 with five macOS-only skips. Installed plugin validation
passed. These checks complement the browser tests; they do not claim fresh-Mac
provisioning or a fixed streaming frame rate.
