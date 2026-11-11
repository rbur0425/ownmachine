import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'darwin', 'Requires macOS plutil and launch-agent format')
class PermissionGuideTests(unittest.TestCase):
    def run_guide(self, initially_granted, approve=True, capture_verified=True, signed_record=False, transient=0, transient_kind="daemon", unavailable=False):
        with tempfile.TemporaryDirectory(prefix='ownmachine test & ') as temp:
            home = Path(temp)
            binary = home / '.local/bin/cua-driver'
            binary.parent.mkdir(parents=True)
            binary.write_text('''#!/bin/bash
count=$(cat "$HOME/status-count" 2>/dev/null || echo 0)
count=$((count+1)); echo "$count" > "$HOME/status-count"
if [ "$count" -le TRANSIENT_LIMIT ]; then
  TRANSIENT_BEHAVIOR
fi
if [ "$2" = grant ]; then
  echo 'Floating guide must not be used' >&2
  exit 1
fi
verification=null
if [ -e "$HOME/driver-record" ] || [ -e "$HOME/.local/state/ownmachine/permissions/capture-verified" ]; then
  verification='{"bundle_id":"com.trycua.driver","source":"permissions_grant","verified_at":"test"}'
fi
if [ -e "$HOME/granted" ]; then permission=true; else permission=false; fi
printf '{"accessibility":%s,"screen_recording":%s,"daemon_running":true,"direct_capture_verification":%s}\\n' "$permission" "$permission" "$verification"
'''.replace('TRANSIENT_LIMIT', str(transient)).replace('TRANSIENT_BEHAVIOR',
    "echo '{\"accessibility\":false,\"screen_recording\":false,\"daemon_running\":false}'; exit 0" if transient_kind == 'daemon' else 'exit 1'))
            if signed_record: (home / 'driver-record').touch()
            binary.chmod(0o700)
            if initially_granted:
                (home / 'granted').touch()
                state = home / '.local/state/ownmachine/permissions'
                state.mkdir(parents=True)
                if capture_verified: (state / 'capture-verified').touch()
            env = dict(os.environ, HOME=temp, OWNMACHINE_PERMISSION_STARTUP_ATTEMPTS="2" if unavailable else "15")
            installer = Path(__file__).parents[1] / 'scripts/install-permission-guide.sh'
            subprocess.run(['/bin/bash', str(installer)], env=env, check=True, capture_output=True)
            plist = plistlib.loads((home / 'Library/LaunchAgents/org.ownmachine.permission-guide.plist').read_bytes())
            self.assertTrue(plist['RunAtLoad'])
            self.assertNotIn('KeepAlive', plist)
            self.assertEqual(plist['LimitLoadToSessionType'], 'Aqua')
            support = home / '.local/lib/ownmachine'
            # Compile the actual UI, but substitute its process boundary in flow
            # tests so tests never change permissions or open desktop windows.
            subprocess.run(['/usr/bin/osacompile', '-l', 'JavaScript', '-o',
                            str(home / 'guide.scpt'), str(support / 'permission-guide.js')],
                           check=True, capture_output=True)
            fake_ui = home / 'fake-ui'
            fake_ui.write_text('#!/bin/bash\ntouch "$HOME/grant-requested"\n' +
                               ('touch "$HOME/granted" "$HOME/.local/state/ownmachine/permissions/capture-verified"\n' if approve else ''))
            fake_ui.chmod(0o700)
            helper = support / 'permission-guide.sh'
            helper.write_text(helper.read_text().replace(
                '/usr/bin/open -g -a /Applications/CuaDriver.app --args serve --no-permissions-gate', ':').replace(
                '/usr/bin/osascript -l JavaScript', '"$HOME/fake-ui"'))
            result = subprocess.run(plist['ProgramArguments'], env=env, check=False, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1 if unavailable else 0)
            self.assertEqual((home / '.local/state/ownmachine/permissions/state').read_text().strip(),
                             'driver_unavailable' if unavailable else 'ready' if (initially_granted and (capture_verified or signed_record)) or approve else 'approval_required')
            self.assertEqual((home / 'grant-requested').exists(), False if unavailable else not (initially_granted and (capture_verified or signed_record)))

    def test_already_granted_does_not_prompt(self):
        self.run_guide(True)

    def test_missing_grants_launch_guide_and_recheck(self):
        self.run_guide(False)

    def test_dismissed_guide_leaves_approval_pending(self):
        self.run_guide(False, approve=False)

    def test_switches_alone_do_not_mark_ready(self):
        self.run_guide(True, approve=False, capture_verified=False)

    def test_switches_then_successful_capture_mark_ready(self):
        self.run_guide(True, approve=True, capture_verified=False)

    def test_signed_capture_record_avoids_repeat_onboarding(self):
        self.run_guide(True, capture_verified=False, signed_record=True)

    def test_startup_daemon_race_preserves_existing_verification(self):
        self.run_guide(True, transient=2)

    def test_startup_cli_errors_do_not_invalidate_verification(self):
        self.run_guide(True, transient=2, transient_kind='error')

    def test_revoked_grants_still_require_user_with_signed_record(self):
        self.run_guide(False, approve=False, signed_record=True)

    def test_unavailable_driver_does_not_show_false_permission_prompt(self):
        self.run_guide(True, transient=99, unavailable=True)
