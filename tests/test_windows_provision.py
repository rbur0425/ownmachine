import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import windows_provision as w
from setup_support import module
stages=module('tested_fresh_windows','scripts/setup-windows.py')

class FreshWindowsTests(unittest.TestCase):
    def config(self):
        p=dict(vm_uuid='11111111-1111-4111-8111-111111111111',network_uuid='22222222-2222-4222-8222-222222222222',bridge='ownm-test',subnet='10.243.0.0/24',guest_ip='10.243.0.10',dns_server='9.9.9.9',windows_iso='/private/windows.iso',windows_iso_sha256='a'*64,driver_zip='/private/driver.zip',accept_evaluation_terms=True,operator_user='operator',agent_user='agent',viewer_user='viewer',qemu_user='qemu',console_group='console',console_socket='/private/console/vnc.sock',host_address='host.example',host_known_hosts='/private/known_hosts',runtime_prefix='/usr/local/lib/ownmachine-test',guest_user='desktop',guest_setup_user='setup',guest_install_root='C:/ProgramData/OwnMachine',viewer_python='/private/venv/bin/python',viewer_control_dir='/private/viewer/control',access_dir='/private/viewer/access',viewer_port=0)
        return dict(provision=p),dict(vm_name='ownmachine-test',storage_dir='/private/new',control_dir='/container/control',cpu=4,memory_gb=8,disk_gb=96)

    def test_omarchy_driver_waits_for_sign_in_before_mutation(self):
        plan={'guest_profile':'omarchy-kvm'}
        with patch.object(w,'guest',return_value=dict(bootstrap_hardened=True,graphical_session=False)) as guest:
            self.assertEqual(stages.execute({},plan,'driver',True)['code'],'graphical_session_required')
            guest.assert_called_once_with({},'status')

    def test_omarchy_driver_waits_after_a_single_install(self):
        plan = {'guest_profile': 'omarchy-kvm'}
        pending = dict(bootstrap_hardened=True, graphical_session=True, guest_reachable=True,
                       vm_state='running', driver_ready=False, foreground_input_ready=False)
        ready = dict(pending, driver_ready=True, foreground_input_ready=True)
        with patch.object(w, 'guest', side_effect=[pending, {'ok': True}]) as guest, \
                patch.object(stages, 'probe', side_effect=[pending, ready]), patch.object(stages.time, 'sleep'):
            self.assertEqual(stages.execute({}, plan, 'driver', True)['stage'], 'verified')
            self.assertEqual([call.args[1] for call in guest.call_args_list], ['status', 'driver'])

    def test_omarchy_driver_errors_direct_operator_to_build_recovery(self):
        pending = dict(bootstrap_hardened=True, graphical_session=True)
        for response in (ValueError('invalid json'), subprocess.TimeoutExpired('ssh',1), [], {}):
            with patch.object(w,'guest',side_effect=[pending,response]):
                result=stages.execute({}, {'guest_profile':'omarchy-kvm'}, 'driver', True)
                self.assertEqual(result['code'],'omarchy_driver_install_incomplete')

    def test_guest_retirement_resumes_after_lost_reply(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td).resolve()
            key = state/'guest-setup'
            key.touch(mode=0o600)
            conf = state/'ssh_config'
            conf.write_text('fixture')
            c = dict(storage_dir=str(state), ssh_config=str(conf), _profile='omarchy-kvm', _vm_uuid='test')
            denied = subprocess.CompletedProcess([],255,'','Permission denied (publickey).')
            with patch.object(w,'guest',side_effect=[subprocess.TimeoutExpired('ssh',1),
                              subprocess.CalledProcessError(255,'ssh')]), patch.object(w.subprocess,'run',return_value=denied):
                with self.assertRaises(subprocess.TimeoutExpired):
                    w.retire(c,state)
                self.assertTrue(key.exists())
                w.retire(c,state)
                self.assertFalse(key.exists())
                w.retire(c,state)

    def test_first_build_has_budget_for_all_three_build_commands(self):
        for profile, operation, timeout in [('omarchy-kvm', 'driver', 6900), ('windows', 'driver', 1800),
                                            ('omarchy-kvm', 'status', 120)]:
            with patch.object(w, 'run', return_value=subprocess.CompletedProcess([], 0, '{}')) as run:
                w.guest({'ssh_config': '/config', '_profile': profile}, operation)
                self.assertEqual(run.call_args.kwargs['timeout'], timeout)

    def test_omarchy_bootstrap_and_readiness_report_profile_reasons(self):
        plan={'guest_profile':'omarchy-kvm'}
        with patch.object(stages,'probe',return_value={'vm_state':'running'}),patch.object(w,'guest',side_effect=ValueError()):
            self.assertEqual(stages.execute({},plan,'provision',True)['code'],'omarchy_bootstrap_pending')
        self.assertEqual(stages.readiness_result({},linux=True)['code'],'omarchy_guest_unreachable')
        self.assertEqual(stages.readiness_result(dict(guest_reachable=True,bootstrap_hardened=True),linux=True)['code'],'graphical_session_required')

    def test_host_viewer_and_client_control_paths_are_distinct(self):
        c,p=self.config();merged=w.settings(c,p)
        self.assertEqual(merged['viewer_control_dir'],'/private/viewer/control')
        self.assertEqual(merged['control_dir'],'/container/control')
        p['guest_ip']='10.243.0.20'
        with self.assertRaisesRegex(ValueError,'ambiguous'):w.settings(c,p)

    def test_reject_unsafe_or_unreviewed_inputs(self):
        for field,value in [('accept_evaluation_terms',False),('guest_ip','10.243.0.1'),('guest_ip','192.0.2.1'),('windows_iso','/private/../old.iso'),('host_address','host;command'),('viewer_port',True),('agent_user','operator')]:
            c,p=self.config();c['provision'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):w.settings(c,p)

    def test_power_and_time_zone_are_configurable_and_validated(self):
        c,p=self.config();merged=w.settings(c,p)
        self.assertEqual((merged['display_idle_minutes'],merged['sleep_idle_minutes'],merged['time_zone']),(0,0,'UTC'))
        c['provision'].update(display_idle_minutes=30,sleep_idle_minutes=60,time_zone='Eastern Standard Time')
        self.assertEqual(w.settings(c,p)['time_zone'],'Eastern Standard Time')
        for key,value in [('display_idle_minutes',True),('sleep_idle_minutes',-1),('display_idle_minutes',1441),('time_zone','UTC;command')]:
            invalid=copy.deepcopy(c);invalid['provision'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):w.settings(invalid,p)

    def test_time_servers_are_bounded_configuration_not_command_arguments(self):
        c,p=self.config()
        self.assertEqual(w.settings(c,p)['time_servers'],['time.windows.com'])
        c['provision']['time_servers']=['ntp.example','192.0.2.8']
        self.assertEqual(w.settings(c,p)['time_servers'],['ntp.example','192.0.2.8'])
        for peers in ([], 'ntp.example', ['x']*6, ['bad" /unsafe'], [None], ['-flag'], ['x'*254]):
            c['provision']['time_servers']=peers
            with self.subTest(peers=peers),self.assertRaisesRegex(ValueError,'time_servers'):w.settings(c,p)

    def test_clock_retry_does_not_reinstall_or_start_running_guest(self):
        with patch.object(stages,'probe',return_value={'vm_state':'running'}),patch.object(w,'run') as run:
            for success in (True,False):
                with patch.object(w,'guest',side_effect=[{'configured':False,'bootstrap_stage':'awaiting_time_sync'},{'configured':success}]) as guest:
                    result=stages.execute({}, {},'provision',True)
                    self.assertEqual(result['ok'],success)
                    self.assertEqual(guest.call_args_list[1].args[1],'sync-time')
                    if not success:self.assertEqual(result['code'],'windows_time_sync_required')
            run.assert_not_called()

    def test_bootstrap_progress_does_not_replay_running_or_failed_steps(self):
        with patch.object(stages,'probe',return_value={'vm_state':'running'}):
            for phase,code in [('installing_openssh','windows_bootstrap_in_progress'),('synchronizing_clock','windows_bootstrap_in_progress'),('failed','windows_bootstrap_failed')]:
                with patch.object(w,'guest',return_value={'configured':False,'bootstrap_stage':phase}) as guest:
                    self.assertEqual(stages.execute({}, {},'provision',True)['code'],code)
                    guest.assert_called_once_with({},'status')

    def test_existing_storage_is_never_overwritten(self):
        c,p=self.config()
        with tempfile.TemporaryDirectory() as td:
            p['storage_dir']=str(Path(td).resolve());disk=Path(td)/'windows.qcow2';disk.write_bytes(b'existing')
            with patch.object(w,'run') as run,self.assertRaisesRegex(ValueError,'nonempty'):w.build(c,p)
            run.assert_not_called();self.assertEqual(disk.read_bytes(),b'existing')

    def test_hardening_waits_for_bootstrap_before_ejecting_media(self):
        with patch.object(w,'guest',return_value={'configured':False}),patch.object(w,'eject') as eject:
            with self.assertRaisesRegex(ValueError,'bootstrap'):stages.execute({}, {},'harden',True)
            eject.assert_not_called()

    def test_provision_resume_does_not_start_running_vm(self):
        with patch.object(stages,'probe',return_value={'vm_state':'running'}),patch.object(w,'guest',side_effect=subprocess.TimeoutExpired('ssh',1)),patch.object(w,'run') as run:
            result=stages.execute({}, {},'provision',True)
            self.assertEqual(result['code'],'windows_installation_in_progress');run.assert_not_called()

    def test_retirement_requires_positive_rejection_and_never_replays_uncertainty(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)
            with patch.object(w,'guest',return_value={'ok':True,'retired':True}),patch.object(w.subprocess,'run',return_value=subprocess.CompletedProcess([],255,'','Connection refused')):
                with self.assertRaisesRegex(ValueError,'rejection_not_proven'):w.retire({'ssh_config':'/private/config'},state)
            with patch.object(w,'guest') as guest,self.assertRaisesRegex(ValueError,'inspection'):w.retire({},state)
            guest.assert_not_called()

    def test_mutating_stage_receipts_match_transport_contract(self):
        with patch.object(stages,'probe',side_effect=lambda c,r,operation='status': {'vm_uuid':'test'} if operation=='status' else True):
            for step in ('keys','relay'):
                self.assertEqual(stages.execute({}, {},step,True)['stage'],'verified')
        with patch.object(w,'guest',return_value={k:True for k in ('configured','hardened','secure_boot','tpm_ready','driver_signature','driver_unchanged')}), patch.object(stages,'wait_driver',return_value={'driver_ready':True}):
            self.assertEqual(stages.execute({}, {},'driver',True)['stage'],'verified')

    def test_read_only_viewer_receipt_matches_transport_contract(self):
        with patch.object(w, 'viewer') as viewer:
            plan = {'guest_profile': 'omarchy-kvm'}
            self.assertEqual(stages.execute({}, plan, 'viewer-check')['stage'], 'checks_passed')
            viewer.assert_called_once_with({}, plan, False)

    def test_driver_readiness_wait_is_bounded_and_read_only(self):
        pending=dict(vm_state='running',guest_reachable=True,bootstrap_hardened=True,driver_ready=False)
        ready=dict(pending,driver_ready=True)
        with patch.object(stages.time,'monotonic',side_effect=[0,0,2]),patch.object(stages.time,'sleep') as sleep,patch.object(stages,'probe',return_value=ready) as probe:
            self.assertEqual(stages.wait_driver({},pending),ready)
            sleep.assert_called_once_with(2)
            probe.assert_called_once_with({},'agent',timeout=20)
        with patch.object(stages.time,'monotonic',side_effect=[0,30]),patch.object(stages,'probe') as probe:
            self.assertEqual(stages.wait_driver({},pending),pending)
            probe.assert_not_called()
        with patch.object(stages.time,'monotonic',side_effect=[0,0,2]),patch.object(stages.time,'sleep'),patch.object(stages,'probe',side_effect=subprocess.TimeoutExpired('ssh',1)):
            self.assertEqual(stages.wait_driver({},pending),pending)
        for changes in ({'vm_state':'stopped'},{'bootstrap_hardened':False},{'guest_reachable':False},{'driver_state':'health_check_failed'},{'driver_state':'foreground_input_unavailable'}):
            report=dict(pending,**changes)
            with patch.object(stages,'probe') as probe:
                self.assertEqual(stages.wait_driver({},report),report)
                probe.assert_not_called()

    def test_driver_wait_configuration(self):
        self.assertEqual(stages.readiness_timeout({}),30)
        for seconds in (0,120):self.assertEqual(stages.readiness_timeout({'driver_ready_timeout_seconds':seconds}),seconds)
        for value in (True,-1,121,'30',None):
            with self.assertRaisesRegex(ValueError,'invalid_driver_ready_timeout'):
                stages.readiness_timeout({'driver_ready_timeout_seconds':value})

    def test_ejected_cdrom_accepts_live_index_but_rejects_media(self):
        import xml.etree.ElementTree as ET
        for source,empty in [('',True),('<source index="4"/>',True),
                             ('<source file="/private/media.iso" index="4"/>',False),
                             ('<source dev="/dev/sr0"/>',False),
                             ('<source protocol="https"><host name="media.example"/></source>',False),
                             ('<source index="not-a-number"/>',False)]:
            with self.subTest(source=source):
                self.assertEqual(w.empty_cdrom(ET.fromstring('<disk>'+source+'</disk>')),empty)

    def test_media_ejection_checks_persistent_definition_too(self):
        live='<domain><devices><disk device="cdrom"><source index="4"/></disk></devices></domain>'
        saved='<domain><devices><disk device="cdrom"><source file="/private/media.iso"/></disk></devices></domain>'
        with tempfile.TemporaryDirectory() as td:
            config=Path(td)/'runtime.json';config.write_text(json.dumps({'vm_uuid':'test'}))
            for persistent,expected in [(live,True),(saved,False)]:
                with patch.object(w,'run',side_effect=[subprocess.CompletedProcess([],0,live),subprocess.CompletedProcess([],0,persistent)]) as run:
                    self.assertEqual(w.media_ejected({'runtime_config':str(config)}),expected)
                    self.assertIn('--inactive',run.call_args.args[0])

    def test_viewer_preserves_normal_colors_unless_explicitly_overridden(self):
        c,p=self.config();c['viewer_alias']='viewer-test'
        self.assertNotIn('--swap-red-blue',w.viewer_argv(c,w.settings(c,p)))
        c['provision']['viewer_swap_red_blue']=True
        self.assertIn('--swap-red-blue',w.viewer_argv(c,w.settings(c,p)))
        c['provision']['viewer_swap_red_blue']='true'
        with self.assertRaisesRegex(ValueError,'color_override'):w.settings(c,p)

    def test_domain_has_only_private_console_no_host_share(self):
        c,p=self.config()
        with tempfile.TemporaryDirectory() as td:
            config=Path(td)/'config.json';config.write_text(json.dumps(w.settings(c,p)))
            subprocess.run([sys.executable,str(ROOT/'scripts/windows/render-domain.py'),str(config),td],check=True,capture_output=True)
            import xml.etree.ElementTree as ET
            tree=ET.fromstring((Path(td)/'domain.xml').read_text())
            self.assertEqual(tree.find('./clock').get('offset'),'utc')
            self.assertIsNone(tree.find('./devices/filesystem'))
            self.assertEqual(tree.find('./devices/graphics/listen').get('type'),'socket')
            self.assertEqual(tree.find('./devices/graphics').get('socket'),c['provision']['console_socket'])
            self.assertEqual(tree.find('./devices/tpm/backend').get('version'),'2.0')
            self.assertEqual(len(tree.findall('./devices/disk')),3)

if __name__=='__main__':unittest.main()
