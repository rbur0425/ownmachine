import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock
spec=importlib.util.spec_from_file_location('viewer_server',Path(__file__).parents[1]/'viewer/server.py')
viewer=importlib.util.module_from_spec(spec);spec.loader.exec_module(viewer)

class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        import shutil
        self.addCleanup(lambda:shutil.rmtree(self.tmp.name+'-access',ignore_errors=True))
        self.service=viewer.Viewer(viewer.Config(host_alias='example-mac',control_dir=self.tmp.name),access_dir=self.tmp.name+'-access')
        self.server=viewer.Server(('127.0.0.1',0),self.service)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.cleanup)
    def cleanup(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.service.close()
    def request(self,path,method='GET',payload=None,auth=True,origin=None,host=None,cookie=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        headers={}
        if auth:headers['X-OwnMachine-Token']=self.service.token
        if origin:headers['Origin']=origin
        if host:headers['Host']=host
        if cookie:headers['Cookie']=cookie
        body=json.dumps(payload) if payload is not None else None
        if body:headers['Content-Type']='application/json'
        conn.request(method,path,body,headers);res=conn.getresponse();data=res.read();conn.close()
        return res.status,data
    def test_frames_and_state_require_token(self):
        for path in ('/api/state','/api/frame'):
            self.assertEqual(self.request(path,auth=False)[0],403)
        status,data=self.request('/')
        self.assertEqual(status,200);self.assertNotIn(self.service.token.encode(),data)
    def test_bad_origin_host_and_cross_site_post_do_not_change_control(self):
        initial=self.service.lease.status()
        for kw in ({'origin':'https://evil.example'},{'host':'evil.example'},{'auth':False}):
            self.assertEqual(self.request('/api/action','POST',{'action':'agent'},**kw)[0],403)
        self.assertEqual(initial,self.service.lease.status())
    def test_handoff_requires_explicit_uncertainty_acknowledgement(self):
        with self.assertRaises(RuntimeError):
            with self.service.lease.lifecycle():raise RuntimeError()
        self.assertEqual(self.request('/api/action','POST',{'action':'agent'})[0],409)
        self.assertEqual(self.request('/api/action','POST',{'action':'agent','acknowledge':True})[0],200)
        self.assertEqual(self.service.lease.status()['controller'],'agent')
    def test_input_and_unknown_actions_have_no_route(self):
        for action in ('click','type','delete','create'):
            self.assertEqual(self.request('/api/action','POST',{'action':action})[0],400)
        self.assertEqual(self.request('/api/input','POST',{})[0],400)
    def test_stale_frame_is_not_presented_as_current(self):
        self.service.frame=b'PNG';self.service.frame_time=time.time()
        self.assertEqual(self.request('/api/frame'),(200,b'PNG'))
        self.service.frame_time=time.time()-10
        self.assertEqual(self.request('/api/frame')[0],503)
    def test_lifecycle_errors_clear_busy_state_but_preserve_marker(self):
        with patch.object(viewer,'operate',side_effect=viewer.LifecycleError('unknown')):
            self.assertEqual(self.request('/api/action','POST',{'action':'restart'})[0],409)
        self.assertFalse(self.service.suspended.is_set());self.assertIsNone(self.service.operation)
    def test_second_viewer_cannot_replace_access_state(self):
        with self.assertRaises(BlockingIOError):viewer.Viewer(self.service.config,access_dir=self.tmp.name+'-access')

    def test_occupied_requested_port_falls_back_atomically(self):
        other=viewer.bind_server(self.service,self.server.server_port)
        try:
            self.assertNotEqual(other.server_port,self.server.server_port)
            self.assertGreater(other.server_port,0)
            self.assertEqual(other.server_address[0],'127.0.0.1')
        finally:other.server_close()
    def test_default_port_is_os_assigned(self):
        other=viewer.bind_server(self.service)
        try:self.assertGreater(other.server_port,0)
        finally:other.server_close()

    def test_tunnel_may_use_another_loopback_port_but_origin_must_match(self):
        host='127.0.0.1:54321'
        self.assertEqual(self.request('/api/state',host=host,origin='http://'+host)[0],200)
        self.assertEqual(self.request('/api/state',host=host,origin='http://127.0.0.1:54322')[0],403)

    def prepare_input(self):
        self.service.lease.transfer('human')
        self.service.frame=b'PNG';self.service.frame_time=time.time()
        self.service.frame_id='test-frame';self.service.capture_id='capture-test'
        self.service.dimensions=(1280,800);self.service.session='test-session'
        self.service.frames={'test-frame':{'time':time.time(),'generation':self.service.lease.status()['generation'],'dimensions':(1280,800)}}
        self.service.client=MagicMock()
        self.service.client.tools={n:{'properties':{k:{} for k in fields}} for n,fields in {
            'click':['x','y','button','count','scope','session','capture_id'],
            'type_text':['text','scope','session'], 'press_key':['key','scope','session'],
            'hotkey':['keys','scope','session'], 'scroll':['direction','amount','scope','session']}.items()}
        self.service.client.call.return_value={'structuredContent':{'ok':True,'verified':False}}
        return {'kind':'click','frame_id':'test-frame','x':400,'y':300}
    def test_human_click_uses_capture_and_consumes_frame(self):
        payload=self.prepare_input()
        self.assertEqual(self.request('/api/input','POST',payload)[0],200)
        args=self.service.client.call.call_args.args
        self.assertEqual(args[0],'click');self.assertEqual(args[1]['capture_id'],'capture-test')
        self.assertFalse(self.service.lease.status()['pending'])
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        self.assertEqual(self.service.client.call.call_count,1)
    def test_agent_paused_and_old_generation_refuse_input(self):
        for state in ('agent','paused','human'):
            payload=self.prepare_input();self.service.lease.transfer(state)
            self.assertEqual(self.request('/api/input','POST',payload)[0],409)
            self.service.client.call.assert_not_called()
    def test_failed_input_is_pending_and_not_replayed(self):
        payload=self.prepare_input()
        self.service.client.call.side_effect=viewer.TransportError('private detail')
        status,data=self.request('/api/input','POST',payload)
        self.assertEqual(status,409);self.assertNotIn(b'private detail',data)
        self.assertTrue(self.service.lease.status()['pending'])
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        self.assertEqual(self.service.client.call.call_count,1)
    def test_read_only_is_server_enforced(self):
        payload=self.prepare_input();self.service.allow_input=False
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        self.service.client.call.assert_not_called()
    def test_invalid_coordinates_and_extra_driver_fields_rejected(self):
        payload=self.prepare_input()
        for extra in ({'x':1280},{'x':-1},{'x':True},{'pid':123},{'x':float('nan')}):
            self.assertEqual(self.request('/api/input','POST',{**payload,**extra})[0],400)
        self.service.client.call.assert_not_called()
    def test_stale_or_resized_frame_refused(self):
        payload=self.prepare_input();self.service.frames['test-frame']['time']-=10
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        payload=self.prepare_input();self.service.dimensions=(1920,1200)
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        self.service.client.call.assert_not_called()
    def test_text_keys_and_scroll_allowlist(self):
        for body,name in [({'kind':'text','text':'hello'},'type_text'),({'kind':'key','keys':['enter']},'press_key'),({'kind':'key','keys':['cmd','a']},'hotkey'),({'kind':'scroll','direction':'down'},'scroll')]:
            self.prepare_input()
            self.assertEqual(self.request('/api/input','POST',{'frame_id':'test-frame',**body})[0],200)
            self.assertEqual(self.service.client.call.call_args.args[0],name)
    def test_input_auth_and_origin_required(self):
        payload=self.prepare_input()
        for kw in ({'auth':False},{'origin':'https://evil.example'}):
            self.assertEqual(self.request('/api/input','POST',payload,**kw)[0],403)
        self.service.client.call.assert_not_called()
    def test_transfer_waits_for_human_write(self):
        payload=self.prepare_input();entered=threading.Event();release=threading.Event()
        def call(*args):
            entered.set();release.wait(2);return {'structuredContent':{'ok':True}}
        self.service.client.call.side_effect=call
        thread=threading.Thread(target=lambda:self.service.input(payload));thread.start()
        self.assertTrue(entered.wait(1))
        transferred=threading.Event()
        transfer=threading.Thread(target=lambda:(self.service.lease.transfer('agent'),transferred.set()));transfer.start()
        self.assertFalse(transferred.wait(.1));release.set();thread.join(3);transfer.join(3)
        self.assertTrue(transferred.is_set());self.assertEqual(self.service.lease.status()['controller'],'agent')

    def test_session_login_requires_token_and_same_origin(self):
        origin='http://127.0.0.1:'+str(self.server.server_port)
        self.assertEqual(self.request('/api/session','POST',{'token':self.service.token},auth=False)[0],403)
        self.assertEqual(self.request('/api/session','POST',{'token':'wrong'},auth=False,origin=origin)[0],403)
        self.assertEqual(self.request('/api/session','POST',{'token':self.service.token},auth=False,origin='https://evil.example')[0],403)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        conn.request('POST','/api/session',json.dumps({'token':self.service.token}),{'Content-Type':'application/json','Origin':origin})
        result=conn.getresponse();result.read();cookie=result.getheader('Set-Cookie');conn.close()
        self.assertEqual(result.status,200)
        self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie);self.assertNotIn('Max-Age',cookie)
        self.assertEqual(self.request('/api/state',auth=False,cookie=cookie)[0],200)
        self.assertEqual(self.request('/api/action','POST',{'action':'human'},auth=False,cookie=cookie,origin='https://evil.example')[0],403)
        self.service.token='rotated'
        self.assertEqual(self.request('/api/state',auth=False,cookie=cookie)[0],403)

    def test_stream_requires_auth_and_exact_browser_origin(self):
        self.service.mode='vnc'
        self.assertEqual(self.request('/api/stream',auth=False)[0],403)
        self.assertEqual(self.request('/api/stream',origin='https://evil.example')[0],403)
        self.assertEqual(self.request('/api/stream')[0],403)
        self.assertEqual(self.request('/api/stream',origin='http://127.0.0.1:'+str(self.server.server_port))[0],400)

    def test_streaming_disables_mcp_input_endpoint(self):
        payload=self.prepare_input();self.service.mode='vnc'
        self.assertEqual(self.request('/api/input','POST',payload)[0],409)
        self.service.client.call.assert_not_called()

    def test_stream_snapshot_distinguishes_live_held_input(self):
        from stream import InputGate
        from types import SimpleNamespace
        self.service.lease.transfer('human')
        gate=InputGate(self.service.lease,self.service.lease.status()['generation'],lambda data:None)
        class Connection:
            pass
        connection=Connection();connection.gate=gate
        self.service.streams.add(connection)
        try:
            gate.dispatch(4,b'\x04\x01\x00\x00\x00\x00\x00a')
            self.assertTrue(self.service.lease.status()['pending'])
            state=self.service.snapshot()['control']
            self.assertFalse(state['pending']);self.assertTrue(state['input_active'])
            gate.release()
            self.assertFalse(self.service.snapshot()['control']['pending'])
        finally:
            gate.release();self.service.streams.remove(connection)

class ViewerSecretBoundaryTests(unittest.TestCase):
    def test_new_control_directory_is_private_with_permissive_umask(self):
        import os
        with tempfile.TemporaryDirectory() as root:
            previous=os.umask(0)
            try:
                service=viewer.Viewer(viewer.Config(host_alias='viewer-host',control_dir=root+'/control'),
                                      access_dir=root+'/access')
                try:
                    self.assertEqual((Path(root)/'control').stat().st_mode&0o777,0o700)
                finally:service.close()
            finally:os.umask(previous)

    def test_access_directory_cannot_overlap_shared_state(self):
        with tempfile.TemporaryDirectory() as root:
            config=viewer.Config(host_alias='viewer-host',control_dir=root+'/shared')
            for path in (root+'/shared',root+'/shared/private',root):
                with self.assertRaisesRegex(ValueError,'viewer_access_must_be_separate'):
                    viewer.Viewer(config,access_dir=path)
    def test_access_directory_must_be_private_and_not_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            from pathlib import Path
            path=Path(root)/'access';path.mkdir(mode=0o755);path.chmod(0o755)
            config=viewer.Config(host_alias='viewer-host',control_dir=root+'/shared')
            with self.assertRaisesRegex(ValueError,'unsafe_viewer_access_directory'):
                viewer.Viewer(config,access_dir=path)
            path.rmdir();path.symlink_to(Path(root)/'target',target_is_directory=True)
            (Path(root)/'target').mkdir(mode=0o700)
            with self.assertRaisesRegex(ValueError,'unsafe_viewer_access_directory'):
                viewer.Viewer(config,access_dir=path)
