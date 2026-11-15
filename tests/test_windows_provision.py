import copy
import importlib.util
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
        with patch.object(w,'guest',return_value={k:True for k in ('configured','hardened','secure_boot','tpm_ready','driver_signature','driver_unchanged')}):
            self.assertEqual(stages.execute({}, {},'driver',True)['stage'],'verified')

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
