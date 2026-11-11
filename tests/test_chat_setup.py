import asyncio
import json
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_onboarding_commands import Context
from ownmachine import onboarding as o, setup_transport as t


class ChatTests(unittest.IsolatedAsyncioTestCase):
    def context(self):
        grant = dict(platform='test', user_id='owner', chat_id='private')
        ctx = Context(dict(setup_allowed_senders=[grant], setup_plan=dict(o.DEFAULTS, target='remote',
            storage_dir='/example/storage', host_alias='runtime'), setup_host_alias='setup', setup_source_sha256='a'*64))
        ctx.messages = []
        async def edit(text): ctx.messages.append(text)
        async def post(text):
            ctx.messages.append(text)
            return SimpleNamespace(aedit=edit)
        def spawn(coro, name):
            ctx.job = asyncio.create_task(coro, name=name)
            return ctx.job
        ctx.apost_message, ctx.spawn_task = post, spawn
        o.register_commands(ctx)
        return ctx, dict(platform='test', source=SimpleNamespace(user_id='owner', chat_id='private'))

    async def test_nonblocking_and_only_authenticated_completion(self):
        ctx, source = self.context()
        release = threading.Event()
        def exchange(argv, request, timeout):
            release.wait(2)
            return {**{k:v for k,v in request.items() if k not in {'apply','stream'}}, 'ok':True,
                'outcomes':{'preflight':{'stage':'observed','observed_at':int(time.time())}}}
        with patch.object(t, 'exchange', side_effect=exchange):
            answer = await ctx.slash('setup --run preflight', **source)
            self.assertIn('started', answer)
            self.assertIn('already active', await ctx.slash('setup --run preflight', **source))
            await asyncio.sleep(.02)
            self.assertEqual(ctx.state.get(t.KEY)['stage'], 'awaiting_remote_result')
            release.set()
            await ctx.job
        self.assertIn('verified', ctx.messages[-1])
        self.assertEqual(ctx.state.get(t.KEY)['stage'], 'remote_observed')

    async def test_cancel_signals_transport_and_preserves_uncertainty(self):
        ctx, source = self.context()
        def exchange(*args):
            cancel = t.CANCEL.get()
            if not cancel.wait(2): raise AssertionError('not cancelled')
            raise ValueError('cancelled')
        with patch.object(t, 'exchange', side_effect=exchange):
            await ctx.slash('setup --run build --apply', **source)
            await asyncio.sleep(.02)
            ctx.job.cancel()
            with self.assertRaises(asyncio.CancelledError): await ctx.job
        self.assertEqual(ctx.state.get(t.KEY)['stage'], 'needs_inspection')

    async def test_sender_revoked_before_execution(self):
        ctx, source = self.context()
        pending = ctx.slash('setup --run preflight', **source)
        ctx.settings['setup_allowed_senders'] = []
        with patch.object(t, 'exchange', side_effect=AssertionError('network')):
            self.assertIn('not authorized', await pending)
        self.assertEqual(ctx.messages, [])

    async def test_delivery_failure_never_starts_remote_work(self):
        ctx, source = self.context()
        async def fail(text): raise RuntimeError('unavailable')
        ctx.apost_message = fail
        with patch.object(t, 'exchange', side_effect=AssertionError('network')):
            await ctx.slash('setup --run preflight', **source)
            await ctx.job
        self.assertIsNone(ctx.state.get(t.KEY))
