import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
from ownmachine.middleware import control_gate_result

class ControlMiddlewareTests(unittest.TestCase):
    def test_review_overrides_retry_once_and_preserves_evidence(self):
        original = {'ok':False,'code':'driver_action_failed_review_required',
                    'meta':{'ownmachine_control_gate':True,'operator_review_required':True,'driver_message':'missing option'},
                    'verdict':{'decision':'escalate'},'escalation':{'recommended':'foreground'}}
        for encoded in (False,True):
            calls=[]
            def execute():
                calls.append(1)
                return json.dumps(original) if encoded else original
            result=control_gate_result(tool_name='computer_use',next_call=execute)
            result=json.loads(result) if encoded else result
            self.assertEqual(calls,[1]);self.assertFalse(result['ok'])
            self.assertEqual(result['verdict']['decision'],'operator_review_required')
            self.assertNotIn('escalation',result)
            self.assertEqual(result['meta'],original['meta'])
            self.assertEqual(original['verdict']['decision'],'escalate')

    def test_other_results_are_unchanged(self):
        for name,result in [('other',{'meta':{'ownmachine_control_gate':True,'operator_review_required':True}}),
                            ('computer_use',{'meta':{'operator_review_required':True}}),
                            ('computer_use',{'ok':True}),('computer_use','not json'),('computer_use','[]')]:
            self.assertIs(control_gate_result(tool_name=name,next_call=lambda:result),result)

    def test_downstream_error_is_not_replayed(self):
        calls=[]
        def execute():
            calls.append(1)
            raise RuntimeError('uncertain')
        with self.assertRaisesRegex(RuntimeError,'uncertain'):
            control_gate_result(tool_name='computer_use',next_call=execute)
        self.assertEqual(calls,[1])
