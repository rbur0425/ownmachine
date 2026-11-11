#!/bin/bash
# Run as the guest desktop user. Launches a normal OwnMachine consent window
# at GUI login; never approves permissions or edits TCC databases.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" -ne 0 ] || { echo 'Run as the macOS guest desktop user' >&2; exit 1; }
[ -x "$HOME/.local/bin/cua-driver" ] || { echo 'Install the signed guest driver first' >&2; exit 1; }
startup_attempts=${OWNMACHINE_PERMISSION_STARTUP_ATTEMPTS:-15}
[[ "$startup_attempts" =~ ^[1-9][0-9]?$ ]] && (( startup_attempts <= 60 )) || { echo 'Startup attempts must be 1–60' >&2; exit 1; }
umask 077
support="$HOME/.local/lib/ownmachine"
state="$HOME/.local/state/ownmachine/permissions"
plist="$HOME/Library/LaunchAgents/org.ownmachine.permission-guide.plist"
mkdir -p "$support" "$state" "$(dirname "$plist")"
cat > "$support/permission-guide.sh" <<'GUIDE'
#!/bin/bash
set -u
umask 077
export CUA_DRIVER_RS_TELEMETRY_ENABLED=0
state="$HOME/.local/state/ownmachine/permissions"
driver="$HOME/.local/bin/cua-driver"
mkdir -p "$state"
# Atomic directory lock avoids duplicate guides within one login. It is removed
# on normal exit; a lock from a previous boot is discarded by boot-session ID.
boot=$(/usr/sbin/sysctl -n kern.bootsessionuuid)
lock="$state/guide-$boot.lock"
mkdir "$lock" 2>/dev/null || exit 0
trap 'rmdir "$lock" 2>/dev/null || true' EXIT
status="$state/status.json"
granted() {
  # Unknown/unavailable status is distinct from a confirmed revoked grant.
  "$driver" permissions status --json > "$status.tmp" 2>/dev/null || return 2
  mv "$status.tmp" "$status"
  for permission_key in daemon_running accessibility screen_recording; do
    [ "$(/usr/bin/plutil -type "$permission_key" "$status" 2>/dev/null)" = bool ] || return 2
  done
  [ "$(/usr/bin/plutil -extract daemon_running raw -o - "$status" 2>/dev/null)" = true ] || return 2
  accessibility=$(/usr/bin/plutil -extract accessibility raw -o - "$status" 2>/dev/null) || return 2
  recording=$(/usr/bin/plutil -extract screen_recording raw -o - "$status" 2>/dev/null) || return 2
  case "$accessibility:$recording" in
    true:true) return 0 ;;
    true:false|false:true|false:false) return 1 ;;
    *) return 2 ;;
  esac
}
capture_verified() {
  # Same signed-driver evidence as host readiness; a stale local marker alone
  # is not proof of capture consent, and no approval is performed here.
  [ "$(/usr/bin/plutil -extract direct_capture_verification.bundle_id raw -o - "$status" 2>/dev/null)" = com.trycua.driver ] &&
  [ "$(/usr/bin/plutil -extract direct_capture_verification.source raw -o - "$status" 2>/dev/null)" = permissions_grant ] &&
  [ "$(/usr/bin/plutil -type direct_capture_verification.verified_at "$status" 2>/dev/null)" = string ] &&
  [ -n "$(/usr/bin/plutil -extract direct_capture_verification.verified_at raw -o - "$status" 2>/dev/null)" ]
}
# Start the signed daemon before interpreting its TCC identity. This suppresses
# only its floating guide, never the operating system's permission policy.
/usr/bin/open -g -a /Applications/CuaDriver.app --args serve --no-permissions-gate
attempts=${OWNMACHINE_PERMISSION_STARTUP_ATTEMPTS:-15}
[[ "$attempts" =~ ^[1-9][0-9]?$ ]] && (( attempts <= 60 )) || exit 1
permission_state=2
for (( attempt=1; attempt<=attempts; attempt++ )); do
  granted; permission_state=$?
  [ "$permission_state" -ne 2 ] && break
  [ "$attempt" -lt "$attempts" ] && /bin/sleep 1
done
if [ "$permission_state" -eq 2 ]; then
  printf '%s\n' 'driver_unavailable' > "$state/state"
  exit 1
fi
if [ "$permission_state" -eq 0 ] && capture_verified && [ "${1:-}" != --show ]; then
  printf '%s\n' 'ready' > "$state/state"
  exit 0
fi
# Only a confirmed revoked grant invalidates the legacy local marker.
if [ "$permission_state" -eq 1 ]; then rm -f "$state/capture-verified"; fi
printf '%s\n' 'awaiting_user' > "$state/state"
/usr/bin/osascript -l JavaScript "$HOME/.local/lib/ownmachine/permission-guide.js"
if granted && capture_verified; then
  printf '%s\n' 'ready' > "$state/state"
else
  printf '%s\n' 'approval_required' > "$state/state"
fi
GUIDE
cat > "$support/permission-guide.js" <<'JXA'
ObjC.import('AppKit');
const shell = Application.currentApplication();
shell.includeStandardAdditions = true;
const home = ObjC.unwrap($.NSHomeDirectory());
function quote(s) { return "'" + s.replace(/'/g, "'\\''") + "'"; }
const app = $.NSApplication.sharedApplication;
app.setActivationPolicy($.NSApplicationActivationPolicyRegular);
let window, status;
function settings(pane) {
    shell.doShellScript('/usr/bin/open ' + quote('x-apple.systempreferences:com.apple.preference.security?' + pane));
    // Yield focus so native permission dialogs can appear unobstructed.
    window.orderBack(null);
}
function check() {
    try {
        const result = JSON.parse(shell.doShellScript(quote(home + '/.local/bin/cua-driver') + ' permissions status --json'));
        status.stringValue = 'Accessibility: ' + (result.accessibility ? 'Approved' : 'Needed') +
            '     Screen Recording: ' + (result.screen_recording ? 'Approved' : 'Needed');
        if (result.accessibility === true && result.screen_recording === true) {
            const verified = result.direct_capture_verification;
            if (verified && verified.bundle_id === 'com.trycua.driver' &&
                verified.source === 'permissions_grant' && typeof verified.verified_at === 'string' && verified.verified_at.length) {
                app.terminate(null);
                return;
            }
            status.stringValue = 'Final capture check: click Allow if macOS asks.';
            window.displayIfNeeded;
            window.orderBack(null);
            // Only enter the signed consent flow once both switches are on and
            // its daemon is running, so its floating first-launch gate is unused.
            if (result.daemon_running !== true) {
                status.stringValue = 'CuaDriver is restarting. Click Check Again shortly.';
                return;
            }
            shell.doShellScript(quote(home + '/.local/bin/cua-driver') +
                ' permissions grant > ' + quote(home + '/.local/state/ownmachine/permissions/capture-check.log') + ' 2>&1');
            shell.doShellScript('/usr/bin/touch ' + quote(home + '/.local/state/ownmachine/permissions/capture-verified'));
            app.terminate(null);
        }
    } catch (e) {
        status.stringValue = 'Capture not verified. Approve the prompt, then Check Again.';
    }
}
ObjC.registerSubclass({name: 'OwnMachineGuideActions', superclass: 'NSObject', methods: {
    'accessibility:': {types: ['void', ['id']], implementation: function() { settings('Privacy_Accessibility'); }},
    'recording:': {types: ['void', ['id']], implementation: function() { settings('Privacy_ScreenCapture'); }},
    'check:': {types: ['void', ['id']], implementation: check},
    'later:': {types: ['void', ['id']], implementation: function() { app.terminate(null); }},
    'windowWillClose:': {types: ['void', ['id']], implementation: function() { app.terminate(null); }}
}});
const actions = $.OwnMachineGuideActions.alloc.init;
window = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(
    $.NSMakeRect(0, 0, 620, 370),
    $.NSWindowStyleMaskTitled | $.NSWindowStyleMaskClosable | $.NSWindowStyleMaskMiniaturizable,
    $.NSBackingStoreBuffered, false);
window.title = 'OwnMachine — Guest Permissions';
window.level = $.NSNormalWindowLevel;
window.delegate = actions;
window.releasedWhenClosed = false;
function label(text, x, y, w, h) {
    const field = $.NSTextField.alloc.initWithFrame($.NSMakeRect(x, y, w, h));
    field.stringValue = text;
    field.editable = false; field.selectable = false;
    field.bezeled = false; field.drawsBackground = false;
    window.contentView.addSubview(field);
    return field;
}
label('Allow OwnMachine to use this guest desktop', 24, 324, 570, 24);
label('Open each settings page and enable CuaDriver. If it is missing, click +,\npress Command-Shift-G and enter /Applications/CuaDriver.app.\nApprove any macOS prompts, including Quit & Reopen if requested.\nClick Check Again, then Allow on the final screen-capture prompt.', 24, 210, 570, 100);
function button(title, selector, x, y, width) {
    const b = $.NSButton.alloc.initWithFrame($.NSMakeRect(x, y, width, 32));
    b.title = title; b.bezelStyle = $.NSBezelStyleRounded;
    b.target = actions; b.action = selector;
    window.contentView.addSubview(b);
}
button('Open Accessibility', 'accessibility:', 20, 170, 210);
button('Open Screen Recording', 'recording:', 235, 170, 245);
status = label('Approve both permissions in System Settings.', 24, 135, 570, 25);
label('Password prompt? Use the guest password, not your Mac login.\nOn the VM host, find ~/.local/state/ownmachine/<vm-name>/guest-password.\nIf paste fails in Lume, type the grouped password directly.', 24, 55, 570, 70);
button('Later', 'later:', 365, 15, 90);
button('Check Again', 'check:', 460, 15, 140);
window.center;
window.makeKeyAndOrderFront(null);
app.activateIgnoringOtherApps(true);
app.run;
JXA
chmod 600 "$support/permission-guide.js"
chmod 700 "$support/permission-guide.sh"
# plutil handles arbitrary home paths without unsafe XML interpolation.
task_plist=$(mktemp "$HOME/Library/LaunchAgents/.ownmachine-guide.XXXXXX")
trap 'rm -f "$task_plist"' EXIT
/usr/bin/plutil -create xml1 "$task_plist"
/usr/bin/plutil -insert Label -string org.ownmachine.permission-guide "$task_plist"
/usr/bin/plutil -insert ProgramArguments -json '[]' "$task_plist"
/usr/bin/plutil -insert ProgramArguments.0 -string /bin/bash "$task_plist"
/usr/bin/plutil -insert ProgramArguments.1 -string "$support/permission-guide.sh" "$task_plist"
/usr/bin/plutil -insert EnvironmentVariables -json '{}' "$task_plist"
/usr/bin/plutil -insert EnvironmentVariables.OWNMACHINE_PERMISSION_STARTUP_ATTEMPTS -string "$startup_attempts" "$task_plist"
/usr/bin/plutil -insert RunAtLoad -bool true "$task_plist"
/usr/bin/plutil -insert LimitLoadToSessionType -string Aqua "$task_plist"
/usr/bin/plutil -insert ProcessType -string Interactive "$task_plist"
/usr/bin/plutil -insert StandardOutPath -string "$state/guide.log" "$task_plist"
/usr/bin/plutil -insert StandardErrorPath -string "$state/guide-error.log" "$task_plist"
/usr/bin/plutil -lint "$task_plist"
mv "$task_plist" "$plist"
chmod 600 "$plist"
echo 'Permission guide installed for next graphical login. No permissions were granted.'
