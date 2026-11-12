"""Run against Hermes's installed public ABC; skip when Hermes is absent."""
import base64
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
try:
 from ownmachine.provider import OwnMachineBackend
except ModuleNotFoundError:
 OwnMachineBackend=None
from ownmachine.config import Config
from ownmachine.transport import TransportError

class FakeTransport:
 def __init__(self):
  names=['get_desktop_state','get_window_state','list_windows','list_apps','click','type_text',
         'press_key','hotkey','scroll','start_session','end_session','bring_to_front','launch_app','set_value']
  self.tools={n:{'properties':{'session':{}}} for n in names}
  self.tools['click']['properties'].update(capture_id={},button={},count={})
  self.calls=[];self.fail=False
 def start(self):pass
 def stop(self):pass
 def call(self,name,args):
  self.calls.append((name,args))
  if self.fail:raise TransportError('transport_outcome_unknown')
  if name=='list_windows':return {'structuredContent':{'windows':[{'pid':12,'window_id':34,'app_name':'Editor','bounds':{'x':0,'y':0,'width':100,'height':100}}]}}
  if name=='get_window_state':
   from PIL import Image
   import io
   stream=io.BytesIO();Image.new('RGB',(100,100)).save(stream,format='PNG')
   image=base64.b64encode(stream.getvalue()).decode()
   return {'content':[{'type':'image','data':image}], 'structuredContent':{'capture_id':'capture-fixture','elements':[
    {'element_index':0,'element_token':'s00000001:0','role':'AXButton','label':'OK','frame':{'x':1,'y':2,'w':3,'h':4}}]}}
  return {'structuredContent':{'effect':'unverifiable','escalation':{'recommended':'foreground'},'path':'ax'}}

@unittest.skipIf(OwnMachineBackend is None,'Requires installed Hermes public provider contract')
class NativeProviderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.fake=FakeTransport();self.config=Config(host_alias='test',control_dir=self.tmp.name)
  self.b=OwnMachineBackend(self.config,transport=self.fake);self.b.start();self.addCleanup(self.b.stop)
 def test_abc_instantiates_and_permission_modes_fail_closed(self):
  for mode in ('bounded','unrestricted','unknown'):
   with self.assertRaises(ValueError):OwnMachineBackend(self.config,mode)
 def test_pause_takeover_and_stale_capture_refuse_without_dispatch(self):
  self.b.capture(app='Editor');count=len(self.fake.calls)
  self.assertEqual(self.b.type_text('x').code,'paused');self.assertEqual(len(self.fake.calls),count)
  self.b.lease.transfer('agent');self.assertEqual(self.b.type_text('x').code,'stale_target')
  self.b.capture(app='Editor');self.b.lease.transfer('human');count=len(self.fake.calls)
  self.assertEqual(self.b.type_text('x').code,'human_takeover');self.assertEqual(len(self.fake.calls),count)
 def test_tokens_and_structured_verdict_are_preserved(self):
  self.b.lease.transfer('agent');cap=self.b.capture(app='Editor')
  self.assertEqual(cap.elements[0].index,1)
  self.assertEqual(cap.elements[0].bounds,(1,2,3,4))
  result=self.b.click(element=1)
  self.assertEqual(self.fake.calls[-1][1]['element_token'],'s00000001:0')
  self.assertEqual(result.effect,'unverifiable');self.assertIsNone(result.verified)
  self.assertEqual(result.escalation,{'recommended':'foreground'})
 def test_unknown_write_blocks_followups_even_after_recapture(self):
  self.b.lease.transfer('agent');self.b.capture(app='Editor');self.fake.fail=True
  count=len(self.fake.calls);self.assertEqual(self.b.type_text('x').code,'transport_outcome_unknown')
  self.assertEqual(len(self.fake.calls),count+1);self.assertTrue(self.b.lease.status()['pending'])
  self.fake.fail=False;self.b.capture(app='Editor');count=len(self.fake.calls)
  self.assertEqual(self.b.type_text('x').code,'transport_outcome_unknown');self.assertEqual(len(self.fake.calls),count)
 def test_one_session_per_shared_vm(self):
  other=OwnMachineBackend(self.config,transport=FakeTransport())
  with self.assertRaises(BlockingIOError):other.start()
 def test_invalid_capture_disarms_previous_target(self):
  self.b.lease.transfer('agent');self.b.capture(app='Editor')
  with self.assertRaises(ValueError):self.b.capture(app='Missing')
  self.assertEqual(self.b.type_text('x').code,'capture_required')
 def test_unsupported_action_does_not_dispatch(self):
  count=len(self.fake.calls)
  self.assertEqual(self.b.drag().code,'unsupported_action')
  self.assertEqual(len(self.fake.calls),count)

 def test_pixel_input_requires_pixels_and_ax_tokens_still_work(self):
  self.b.lease.transfer('agent')
  # A real AX-only reply carries no image.
  original=self.fake.call
  def ax_only(name,args):
   reply=original(name,args)
   if name=='get_window_state':reply['content']=[]
   return reply
  self.fake.call=ax_only;self.b.capture(mode='ax',app='Editor')
  self.assertEqual(self.b.click(x=5,y=5).code,'pixel_capture_required')
  self.assertTrue(self.b.click(element=1).ok)

 def test_driver_error_preserves_uncertainty(self):
  self.b.lease.transfer('agent');self.b.capture(app='Editor')
  self.fake.call=lambda name,args:{'isError':True,'structuredContent':{'code':'tool_invocation_failed','escalation':{'recommended':'foreground'}}}
  result=self.b.type_text('x')
  self.assertEqual(result.code,'driver_action_failed_review_required')
  self.assertIsNone(result.escalation)
  self.assertTrue(result.meta['operator_review_required'])
  self.assertIn('driver_message',result.meta)
  import json
  from tools.computer_use.tool import _text_response
  from ownmachine.middleware import control_gate_result
  payload=json.loads(control_gate_result(tool_name='computer_use',next_call=lambda:_text_response(result)))
  self.assertEqual(payload['verdict']['decision'],'operator_review_required')
  self.assertNotIn('escalation',payload)
  self.assertTrue(self.b.lease.status()['pending'])

 def test_frontmost_window_uses_larger_z_index(self):
  original=self.fake.call
  def windows(name,args):
   if name=='list_windows':return {'structuredContent':{'windows':[
    {'pid':12,'window_id':34,'app_name':'Editor','z_index':0,'is_on_screen':True},
    {'pid':12,'window_id':99,'app_name':'Editor','z_index':6,'is_on_screen':True}]}}
   if name=='list_apps':return {'structuredContent':{'apps':[{'name':'Editor','pid':12}]}}
   return original(name,args)
  self.fake.call=windows;self.b.lease.transfer('agent');self.b.capture(app='Editor')
  self.assertEqual(self.b.target['window_id'],99)
  self.b.focus_app('Editor',raise_window=True)
  call=next(args for name,args in reversed(self.fake.calls) if name=='bring_to_front')
  self.assertEqual(call['window_id'],99)

 def test_unknown_window_order_requires_explicit_target(self):
  original=self.fake.call
  def windows(name,args):
   if name=='list_windows':return {'structuredContent':{'windows':[
    {'pid':12,'window_id':34,'app_name':'Editor','z_index':None},
    {'pid':12,'window_id':99,'app_name':'Editor','z_index':6}]}}
   return original(name,args)
  self.fake.call=windows
  with self.assertRaisesRegex(ValueError,'ambiguous_window'):self.b.capture(app='Editor')
  self.assertIsNone(self.b.target)
  self.b.capture(app='Editor',window_id=34)
  self.assertEqual(self.b.target['window_id'],34)

 def test_pending_followup_says_no_dispatch(self):
  self.b.lease.transfer('agent');self.b.capture(app='Editor');self.fake.fail=True
  self.b.type_text('x');self.fake.fail=False;self.b.capture(app='Editor')
  count=len(self.fake.calls);result=self.b.type_text('x')
  self.assertFalse(result.meta['dispatched']);self.assertIn('No new action',result.message)
  self.assertEqual(len(self.fake.calls),count)

 def test_launch_requires_capture_before_dispatch(self):
  self.fake.call=lambda name,args:{'structuredContent':{'apps':[{'name':'Editor','pid':0,'bundle_id':'example.editor'}]}}
  self.b.lease.transfer('agent')
  result=self.b.focus_app('Editor')
  self.assertEqual(result.code,'capture_required')
  self.assertFalse(self.b.lease.status()['pending'])

 def cold_launch_fixture(self, *, fail_launch=False, windows=True):
  original=self.fake.call
  launched=False
  def call(name,args):
   nonlocal launched
   if name=='list_apps':
    self.fake.calls.append((name,args))
    return {'structuredContent':{'apps':[{'name':'Browser','pid':77 if launched else 0,'bundle_id':'example.browser'}]}}
   if name=='launch_app':
    self.fake.calls.append((name,args));launched=True
    return {'structuredContent':{'ok':not fail_launch,'message':'Launched in background'}}
   if name=='list_windows' and launched:
    self.fake.calls.append((name,args))
    return {'structuredContent':{'windows':[{'pid':77,'window_id':88}] if windows else []}}
   return original(name,args)
  self.fake.call=call
  self.b.lease.transfer('agent');self.b.capture(app='Editor')

 def test_cold_launch_explicit_raise_targets_new_window(self):
  self.cold_launch_fixture()
  result=self.b.focus_app('Browser',raise_window=True)
  self.assertTrue(result.ok)
  writes=[(n,a) for n,a in self.fake.calls if n in ('launch_app','bring_to_front')]
  self.assertEqual([n for n,a in writes],['launch_app','bring_to_front'])
  self.assertEqual(writes[1][1]['pid'],77);self.assertEqual(writes[1][1]['window_id'],88)
  self.assertEqual(self.b.type_text('x').code,'capture_required')

 def test_cold_launch_without_raise_stays_background(self):
  self.cold_launch_fixture()
  self.assertTrue(self.b.focus_app('Browser').ok)
  self.assertNotIn('bring_to_front',[n for n,a in self.fake.calls])
  self.assertIsNone(self.b.target)

 def test_failed_cold_launch_never_raises_and_keeps_review_gate(self):
  self.cold_launch_fixture(fail_launch=True)
  self.assertEqual(self.b.focus_app('Browser',raise_window=True).code,'driver_action_failed_review_required')
  self.assertNotIn('bring_to_front',[n for n,a in self.fake.calls])
  self.assertTrue(self.b.lease.status()['pending'])

 def test_takeover_between_launch_and_raise_prevents_second_write(self):
  self.cold_launch_fixture()
  original=self.fake.call
  def call(name,args):
   reply=original(name,args)
   if name=='list_windows' and any(n=='launch_app' for n,a in self.fake.calls):self.b.lease.transfer('human')
   return reply
  self.fake.call=call
  self.assertEqual(self.b.focus_app('Browser',raise_window=True).code,'human_takeover')
  self.assertNotIn('bring_to_front',[n for n,a in self.fake.calls])

 def test_cold_launch_window_timeout_does_not_relaunch(self):
  from unittest.mock import patch
  self.cold_launch_fixture(windows=False)
  with patch('ownmachine.provider.time.monotonic',side_effect=[0,121]):
   result=self.b.focus_app('Browser',raise_window=True)
  self.assertEqual(result.code,'launched_window_not_ready')
  self.assertEqual([n for n,a in self.fake.calls].count('launch_app'),1)
  self.assertNotIn('bring_to_front',[n for n,a in self.fake.calls])
  self.assertFalse(self.b.lease.status()['pending'])

 def test_nonpressable_element_refused_before_dispatch(self):
  original=self.fake.call
  def field(name,args):
   reply=original(name,args)
   if name=='get_window_state':
    reply['structuredContent']['elements'][0].update(role='AXTextField',actions=['AXConfirm'],value='sample')
   return reply
  self.fake.call=field;self.b.lease.transfer('agent');cap=self.b.capture(app='Editor')
  self.assertEqual(cap.elements[0].attributes['actions'],['AXConfirm'])
  self.assertIn('#1 actions: AXConfirm',cap.note)
  count=len(self.fake.calls);result=self.b.click(element=1,bring_to_front=True)
  self.assertEqual(result.code,'element_press_unsupported');self.assertFalse(result.meta['dispatched'])
  self.assertEqual(len(self.fake.calls),count);self.assertFalse(self.b.lease.status()['pending'])
  self.assertTrue(self.b.set_value('updated',element=1).ok)

 def test_pixel_click_is_bound_once_and_right_double_use_same_route(self):
  self.b.lease.transfer('agent')
  for button,count in [('left',1),('left',2),('right',1)]:
   self.b.capture(app='Editor')
   self.assertTrue(self.b.click(x=20,y=30,button=button,click_count=count).ok)
   name,args=self.fake.calls[-1]
   self.assertEqual(name,'click');self.assertEqual(args['capture_id'],'capture-fixture')
   self.assertEqual((args['button'],args['count']),(button,count))
   before=len(self.fake.calls)
   self.assertEqual(self.b.click(x=20,y=30).code,'fresh_pixel_capture_required')
   self.assertEqual(len(self.fake.calls),before)

 def test_pixel_bounds_and_missing_binding_fail_before_focus(self):
  self.b.lease.transfer('agent');self.b.capture(app='Editor');before=len(self.fake.calls)
  for x,y in [(-1,1),(100,1),(1,100),(float('nan'),1),(True,1)]:
   self.assertEqual(self.b.click(x=x,y=y,bring_to_front=True).code,'pixel_coordinates_out_of_bounds')
  self.assertEqual(len(self.fake.calls),before)
  self.b.capture_id=None
  self.assertEqual(self.b.click(x=5,y=5,bring_to_front=True).code,'fresh_pixel_capture_required')
  self.assertEqual(len(self.fake.calls),before)

 def test_driver_screenshot_frame_overrides_earlier_window_geometry(self):
  original=self.fake.call
  def capture(name,args):
   r=original(name,args)
   if name=='get_window_state':
    r['structuredContent']['elements'][0]['screenshot_frame']={'x':30,'y':40,'w':10,'h':20}
   return r
  self.fake.call=capture
  self.assertEqual(self.b.capture(app='Editor').elements[0].bounds,(30,40,10,20))

 def test_fresh_install_loads_through_real_hermes_category_loader(self):
  import os, subprocess
  root=Path(__file__).parents[1]
  home=Path(self.tmp.name)/'fresh-hermes'
  subprocess.run([sys.executable,str(root/'scripts/install-hermes.py'),
   '--hermes-home',str(home),'--host-alias','example',
   '--control-dir',str(Path(self.tmp.name)/'control')],check=True,capture_output=True)
  code="from plugins.computer_use import get_active_provider; p=get_active_provider(); assert type(p).__name__ == 'OwnMachineProvider'"
  code += "; import json; from pathlib import Path; from model_tools import _select_tool_names; from toolsets import resolve_toolset; cfg=json.loads(Path(__import__('os').environ['HERMES_HOME']).joinpath('config.yaml').read_text()); disabled=cfg['agent']['disabled_toolsets']; selected=_select_tool_names(['terminal','file','code_execution','computer_use'],disabled,True); assert not (set(resolve_toolset('terminal')+resolve_toolset('file')+resolve_toolset('code_execution')) & selected); assert resolve_toolset('computer_use') and set(resolve_toolset('computer_use')) <= selected"
  result=subprocess.run([sys.executable,'-c',code],env={**os.environ,'HERMES_HOME':str(home)},capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stderr)

 def test_omarchy_defaults_foreground_and_refuses_background(self):
  from dataclasses import replace
  self.b.config=replace(self.config,guest_profile='omarchy')
  self.b.lease.transfer('agent');self.b.capture(app='Editor')
  self.b.type_text('foreground test')
  self.assertEqual(self.fake.calls[-1][1]['delivery_mode'],'foreground')
  count=len(self.fake.calls)
  self.assertEqual(self.b.type_text('blocked',delivery_mode='background').code,'linux_background_input_not_certified')
  self.assertEqual(len(self.fake.calls),count)
