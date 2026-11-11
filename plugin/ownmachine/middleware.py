"""Keep OwnMachine's durable control-gate decision in the model-facing result.

Uses Hermes's supported execution middleware, never rebinds core functions and
never retries a tool. Other providers and ordinary action results are untouched.
"""
import json


def control_gate_result(*, tool_name, next_call, **kwargs):
    result = next_call()
    if tool_name != 'computer_use':
        return result
    encoded = isinstance(result, str)
    try:
        data = json.loads(result) if encoded else result
    except (ValueError, TypeError):
        return result
    if not isinstance(data, dict):
        return result
    meta = data.get('meta')
    if not isinstance(meta, dict) or meta.get('ownmachine_control_gate') is not True or meta.get('operator_review_required') is not True:
        return result
    data = dict(data)
    data.pop('escalation', None)
    data['verdict'] = {
        'decision': 'operator_review_required',
        'hint': 'Stop. Do not retry or escalate input. The operator must inspect the VM and acknowledge the pending action before further writes.'}
    return json.dumps(data) if encoded else data
