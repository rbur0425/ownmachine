# Viewer diagnostics and recovery

To retrieve the current private link/token or generate a loopback tunnel command,
use the [viewer access helper](viewer-access.md).

Use `hermes computer-use doctor` for native provider/MCP readiness. For browser
problems, run the operator viewer doctor **on the viewer machine, as its owner,
with the viewer's Python environment**, from the source checkout:

```sh
"$HOME/.local/share/ownmachine-viewer-venv/bin/python" scripts/ownmachine-viewer-doctor.py \
  --host-alias ownmachine-viewer-host --vm-name ownmachine \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" --control-dir /absolute/path/to/shared-control-directory
```

Use the same alias and VM configuration as the running viewer. With Docker, this
usually runs on the host with the host path to the bind-mounted control directory,
not inside the Hermes container. Paths and identities are operator supplied.
Add `--json` for a sanitized report. Exit 1 means a failed check; exit 0 means
these checks passed, possibly with warnings. Neither means a GUI task succeeded.

The default checks read the private local access file and send its token only in
an HTTP header to the validated numeric loopback endpoint. They refuse symlinks,
non-owner/world-readable files, non-loopback destinations and redirects. They do
not honor HTTP proxy environment variables. No raw state, token, URL, SSH error,
password, desktop image or typed text is included in the report.

Add `--probe-vnc` to authenticate a separate **shared** RFB connection through
the restricted SSH relay, then close it. This uses the supplied alias/VM and does
not prove that differently configured viewer arguments target the same VM. It
requests no framebuffer and sends no key, pointer, clipboard or lifecycle command.
It does not take ownership of the human gate or disconnect the existing viewer.
The probe skips an active viewer lifecycle operation. Connection and action
bounds are configurable using the same 1–120 second timeout flags as setup.

## Fix the first failed check

| Code / symptom | Recovery |
| --- | --- |
| `viewer_not_started` | Start the viewer with the same shared control directory. Run doctor as its owner on that machine. |
| `invalid_or_unsafe_access_file` | Check ownership and 0600 permissions; use the real file, not a symlink. Restart the viewer to regenerate it. Never paste its contents into a support issue. |
| `viewer_unreachable` | Check the viewer process and actual HTTP port. A preferred port may have fallen back to a free port. Do not delete the lease. |
| `viewer_authentication_failed` | The access token may have rotated. Open the current private link; update the SSH tunnel if the port changed. |
| `vnc_dependency_missing` | Install `viewer/requirements.txt` in the viewer environment, and run this doctor with that same Python. |
| `novnc_assets_missing` | Restore the complete matching `viewer/` directory, including vendor source/licenses. |
| `vnc_connection_failed` | Check the verified SSH alias, running named VM, installed relay, explicit host VNC opt-in and fixed port. Use native doctor for host/MCP checks. Never disable host-key verification. |
| `no_browser_stream` | Open the private link, check the loopback tunnel and exact browser origin. A native doctor success does not test WebSockets. |
| `control_paused` / `control_agent` | Browser input is intentionally blocked. Reserve for human use before typing. |
| `viewer_read_only` | The server was launched with `--read-only`; restart without it only if input is intended. |
| `human_input_active` | A key/button is held. Release it before handoff; do not reset state to bypass it. |
| `uncertain_outcome` | Inspect the guest before explicitly acknowledging through trusted controls. Never automatically repeat the failed action. |
| Reversed red/blue colors | Use `--swap-red-blue` for affected servers. This changes rendering, not the guest. |
| Local browser shortcut wins | Browser/OS-reserved shortcuts may remain local. Click the guest canvas to focus it and use its menus where necessary. |

## Lost connection or stopped VM

A browser refresh or tunnel reconnect must not reboot the guest, replay input or
change the human lease. Reopen the current private link, inspect the desktop and
control state, and reserve/return control explicitly as needed. After returning
to the agent, it must capture fresh state before further input.

If an input outcome is uncertain, the pending marker survives process failure.
Do not remove `lease.db`, create another control directory, or blindly resend the
action. Inspect the guest first and use the viewer/control command to acknowledge
only when you understand the result. Every writer must use the same lease.

Save work before lifecycle operations. Restart and shutdown use guest graceful
shutdown; there is no forced power-off fallback. If shutdown cannot be confirmed,
inspect the guest and repair its SSH/helper setup before retrying. Do not use
force stop as a diagnostic shortcut. A reboot retains disk contents, not running
processes; service-side browser sessions can still expire.

## Firewall check remains independent

From a different machine, verify that the selected host VNC port cannot be
reached, while the SSH-backed viewer still connects. A timed-out connection alone
can also mean a routing failure; establish host reachability and successful relay
access before concluding the intended path is blocked. Repeat after host reboot
or firewall changes. The viewer doctor deliberately reports this as a manual
check; it cannot certify PF policy from a local HTTP/VNC handshake.

Use an administrator account for the firewall installer. The dedicated VM
account need not be in sudoers. Follow [streaming setup](streaming.md) and never
work around missing privileges by exposing VNC directly or weakening SSH checks.

## Native transport reconnection

A failed native request closes its MCP/SSH stream and invalidates captured targets.
A later explicitly requested read may open a new stream and driver session, but
must pass the same required-tool discovery and session checks as initial startup.
An incompatible or failed session is closed; it never enables input. Recovery
never retries the failed write or clears its durable uncertain-outcome marker.
After inspecting the guest, explicitly acknowledge through trusted operator
controls, return control, and take a fresh capture before a new action.

The action timeout bounds each RPC request, including already-buffered replies
and ready file descriptors. Initialization and tool discovery use multiple
bounded requests; this is not a promise that the entire startup completes within
one action timeout. Process teardown has its own cleanup allowance.

### Recorded recovery evidence

140 tests completed: 127 passed on macOS with 13 Hermes-only skips; 135 passed
in Hermes with five macOS-only skips. New tests use a real synthetic MCP
subprocess, the installed Hermes backend contract and a durable lease. Lost
replies and timeouts leave uncertainty, no input replay occurs after reconnect,
and acknowledgement still requires a fresh capture. Thirty synthetic
capture/write/handoff cycles dispatched exactly thirty writes. Incompatible
tool discovery and failed driver sessions closed the reconnect without input.

A separate live check opened the real SSH/MCP stream, listed apps, terminated
only that test's SSH client, observed a transport failure, then explicitly
requested another read. It connected with a new driver session while controller
and generation remained unchanged. No GUI input or VM lifecycle command was
sent. This does not simulate losing a real GUI-write reply; that hardware
acceptance check and an extended hardware soak remain outstanding.
