import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HOST=Path(__file__).resolve().parents[1]/'host'
sys.path.insert(0,str(HOST))
import kvm_backend as kvm
import kvm_security as security

spec=importlib.util.spec_from_file_location('kvm_installer',HOST.parent/'scripts/install-kvm-security.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class KvmBackendTests(unittest.TestCase):
    def setUp(self):
        self.config={'vm_uuid':'test-uuid','vm_name':'desktop','network_uuid':'network-uuid','network_name':'desktop-net','console_socket':'/private/console.sock'}
        self.settings=patch.object(kvm,'C',self.config);self.settings.start();self.addCleanup(self.settings.stop)

    def xml(self,extra='',graphics=None):
        return '<domain><name>desktop</name><uuid>test-uuid</uuid><devices>'+ (graphics or '<graphics type="vnc"><listen type="socket" socket="/private/console.sock"/></graphics>')+'<interface type="network"><source network="desktop-net"/></interface>'+extra+'</devices></domain>'

    def inspect(self,xml):
        with patch.object(kvm,'virsh',side_effect=[xml,'running']): return kvm.inspect()

    def test_configured_private_console_accepted(self):
        self.assertEqual(self.inspect(self.xml())[1],'running')

    def test_wrong_uuid_refused(self):
        with self.assertRaisesRegex(ValueError,'identity'): self.inspect(self.xml().replace('test-uuid','other'))

    def test_tcp_console_refused(self):
        with self.assertRaisesRegex(ValueError,'tcp_console'): self.inspect(self.xml().replace('type="vnc"','type="vnc" port="5900"'))

    def test_host_shares_and_devices_refused(self):
        for element in ('filesystem','hostdev','redirdev'):
            with self.subTest(element=element),self.assertRaisesRegex(ValueError,'sharing'): self.inspect(self.xml('<'+element+'/>'))

    def test_unrelated_network_refused(self):
        with self.assertRaisesRegex(ValueError,'network_identity'): self.inspect(self.xml().replace('desktop-net','other'))

    def test_untrusted_configuration_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'config.json';path.write_text('{}')
            with self.assertRaises(ValueError): kvm.configure(path)

    def test_firewall_refusal_precedes_vm_inspection(self):
        self.config['agent_user']='agent'
        with patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host mcp --vm desktop'}),patch.object(kvm,'security_ready',side_effect=ValueError('drift')),patch.object(kvm,'inspect') as inspect:
            user.return_value.pw_name='agent'
            with self.assertRaisesRegex(ValueError,'drift'): kvm.dispatch('agent')
            inspect.assert_not_called()

    def test_fresh_guest_mcp_requires_hardening_even_with_ready_driver(self):
        import subprocess
        self.config.update(agent_user='agent',require_hardened=True)
        health={k:True for k in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user')}
        health['bootstrap_hardened']=False
        with patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host mcp --vm desktop'}),patch.object(kvm,'security_ready'),patch.object(kvm,'inspect',return_value=(None,'running')),patch.object(kvm,'guest_argv',return_value=['ssh']),patch.object(kvm.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(health))),patch.object(kvm.os,'execve') as execute:
            user.return_value.pw_name='agent'
            with self.assertRaisesRegex(ValueError,'hardening_required'):kvm.dispatch('agent')
            execute.assert_not_called()

    def test_agent_cannot_start(self):
        self.config['agent_user']='agent'
        with patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host start --vm desktop'}),patch.object(kvm,'security_ready') as ready:
            user.return_value.pw_name='agent'
            with self.assertRaisesRegex(ValueError,'unsupported'): kvm.dispatch('agent')
            ready.assert_not_called()

    def test_stop_survives_firewall_drift(self):
        self.config['viewer_user']='viewer'
        with patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host stop --vm desktop'}),patch.object(kvm,'security_ready',side_effect=ValueError('drift')) as ready,patch.object(kvm,'inspect',return_value=(None,'shut off')),patch('sys.stdout',new_callable=io.StringIO):
            user.return_value.pw_name='viewer';kvm.dispatch('viewer');ready.assert_not_called()

    def test_nft_canonicalization_preserves_rules(self):
        a={'nftables':[{'metainfo':{'version':'one'}},{'rule':{'handle':5,'expr':[{'drop':None}]}}]}
        b={'nftables':[{'rule':{'expr':[{'drop':None}]}}]}
        self.assertEqual(security.canonical(a),b)
        self.assertNotEqual(security.canonical(a),{'nftables':[{'rule':{'expr':[{'accept':None}]}}]})

    def test_firewall_only_targets_configured_bridge(self):
        text=installer.firewall({'bridge':'guest9'},'ownmachine_test')
        self.assertNotIn('flush',text)
        self.assertIn('iifname "guest9" drop',text)
        self.assertIn('ct direction reply ct state established,related accept',text)
        self.assertNotIn('ct direction original',text)
        with self.assertRaises(ValueError):installer.firewall({'bridge':'bad"bridge'},'table')

    def test_policy_does_not_grant_unrelated_accounts(self):
        text=installer.policy(dict(agent_user='a',viewer_user='v',vm_uuid='uuid',network_uuid='net'))
        self.assertIn('if (!agent && !viewer) return;',text)
        self.assertNotIn('isInGroup',text)


class KvmSecurityConfigurationTests(unittest.TestCase):
    def test_polkit_accepts_blank_line_without_accepting_duplicate_or_disabled_rules(self):
        enabled='access_drivers = [ "polkit" ]'
        self.assertTrue(security.polkit_configured('\n\n'+enabled+'\n'))
        self.assertFalse(security.polkit_configured('# '+enabled))
        self.assertFalse(security.polkit_configured(enabled+'\n'+enabled))
        self.assertFalse(security.polkit_configured('access_drivers = []'))

    def test_boot_apply_does_not_wait_on_libvirt(self):
        with tempfile.TemporaryDirectory() as folder:
            rules=Path(folder)/'rules.nft';rules.write_text('table inet ownmachine_test {}')
            config={'vm_uuid':'00000000-0000-0000-0000-000000000001'}
            manifest={'table':'ownmachine_test','rules':str(rules),'nft_sha256':'verified'}
            with patch.object(security.os,'geteuid',return_value=0),patch.object(security.sys,'argv',['helper','--apply','/root/config']),patch.object(security,'load',return_value=(config,manifest)),patch.object(security,'live_hash',return_value='verified'),patch.object(security,'run') as run,patch.object(security.subprocess,'run') as process,patch('sys.stdout',new_callable=io.StringIO):
                process.return_value.returncode=0
                security.main()
                run.assert_not_called()
                for call in process.call_args_list:self.assertEqual(call.args[0][0],'/usr/sbin/nft')


class KvmMcpStreamTests(unittest.TestCase):
    def test_health_probe_cannot_consume_mcp_stdin(self):
        flags={k:True for k in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user')}
        config={'agent_user':'agent','vm_name':'desktop'}
        with patch.object(kvm,'C',config),patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host mcp --vm desktop'}),patch.object(kvm,'security_ready'),patch.object(kvm,'inspect',return_value=(None,'running')),patch.object(kvm,'guest_argv',return_value=['ssh','guest']),patch.object(kvm.subprocess,'run') as run,patch.object(kvm.os,'execve',side_effect=SystemExit(0)):
            user.return_value.pw_name='agent';run.return_value.stdout=json.dumps(flags)
            with self.assertRaises(SystemExit):kvm.dispatch('agent')
            self.assertEqual(run.call_args.kwargs['stdin'],kvm.subprocess.DEVNULL)

    def test_unhealthy_session_never_executes_mcp(self):
        with patch.object(kvm,'C',{'agent_user':'agent','vm_name':'desktop'}),patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host mcp --vm desktop'}),patch.object(kvm,'security_ready'),patch.object(kvm,'inspect',return_value=(None,'running')),patch.object(kvm,'guest_argv',return_value=['ssh','guest']),patch.object(kvm.subprocess,'run') as run,patch.object(kvm.os,'execve') as execute:
            user.return_value.pw_name='agent';run.return_value.stdout='{}'
            with self.assertRaisesRegex(ValueError,'interactive_standard'):kvm.dispatch('agent')
            execute.assert_not_called()

    def test_restart_rechecks_stopped_definition_before_start(self):
        with patch.object(kvm,'C',{'viewer_user':'viewer','vm_name':'desktop','vm_uuid':'id'}),patch.object(kvm.pwd,'getpwuid') as user,patch.dict(kvm.os.environ,{'SSH_ORIGINAL_COMMAND':'ownmachine-host restart --vm desktop'}),patch.object(kvm,'security_ready') as ready,patch.object(kvm,'inspect',side_effect=[(None,'running'),ValueError('persistent_definition_drift')]),patch.object(kvm,'virsh',side_effect=['','shut off']) as virsh:
            user.return_value.pw_name='viewer'
            with self.assertRaisesRegex(ValueError,'persistent_definition_drift'):kvm.dispatch('viewer')
            self.assertEqual(ready.call_count,2)
            self.assertFalse(any(c.args[0]=='start' for c in virsh.call_args_list))
