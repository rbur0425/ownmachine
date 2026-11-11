"""Supervised progress for an explicitly authorized, conversation-bound setup call."""
import asyncio
import threading
import time
from . import setup_transport


class ChatSetup:
    def __init__(self, ctx):
        self.ctx = ctx
        self.task = None

    async def start(self, args, source):
        from .onboarding import authorized_sender
        if not authorized_sender(self.ctx, source):
            return 'OwnMachine: setup sender is not authorized.'
        if not all(callable(getattr(self.ctx, name, None)) for name in ('spawn_task', 'apost_message')):
            return 'OwnMachine: this Hermes version lacks supervised chat progress; use the operator terminal.'
        if self.task is not None and not self.task.done():
            return 'OwnMachine: a setup call is already active. Use /ownmachine status; do not replay it.'
        interval = self.ctx.get_config('setup_progress_interval_seconds', 30)
        if type(interval) is not int or not 5 <= interval <= 300:
            return 'OwnMachine: setup_progress_interval_seconds must be between 5 and 300.'
        self.task = self.ctx.spawn_task(self.run(args, dict(source), interval), name='ownmachine-setup')
        return 'OwnMachine: setup started. Progress stays in this conversation; completion requires an authenticated result.'

    async def run(self, args, source, interval):
        from .onboarding import execute, authorized_sender
        cancel = threading.Event()
        token = setup_transport.CANCEL.set(cancel)
        latest = {}
        event_token = setup_transport.EVENT.set(lambda event: latest.update(event))
        worker = None
        start = time.monotonic()
        try:
            # Fail before execution if this conversation cannot receive progress.
            handle = await self.ctx.apost_message('OwnMachine: contacting the approved setup endpoint for ' + args.run + '.')
            if not authorized_sender(self.ctx, source): return
            worker = asyncio.create_task(asyncio.to_thread(execute, self.ctx, args))
            updates = 0
            while not worker.done():
                await asyncio.wait({worker}, timeout=interval)
                if not authorized_sender(self.ctx, source):
                    cancel.set()
                    await asyncio.shield(worker)
                    return
                if not worker.done() and updates < 20:
                    updates += 1
                    detail = ('Last authenticated host heartbeat: '+str(latest['elapsed_seconds'])+'s into this stage.' if latest else 'No host heartbeat received yet.')
                    await handle.aedit(f'OwnMachine: {args.run}, {int(time.monotonic()-start)}s elapsed. {detail} Completion remains unverified.')
            _, code = worker.result()
            await handle.aedit('OwnMachine: ' + args.run + (' verified by the setup endpoint. Desktop acceptance is separate.' if code == 0 else ' needs attention. Inspect /ownmachine status before retrying.'))
        except asyncio.CancelledError:
            cancel.set()
            if worker is not None:
                try: await asyncio.shield(worker)
                except (Exception, asyncio.CancelledError): pass
            raise
        except Exception:
            cancel.set()
            if worker is not None:
                try: await asyncio.shield(worker)
                except Exception: pass
            if authorized_sender(self.ctx, source):
                try: await self.ctx.apost_message('OwnMachine: setup result or progress delivery is uncertain. Use setup --run progress before retrying; never replay an uncertain mutation.')
                except Exception: pass
        finally:
            setup_transport.CANCEL.reset(token)
            setup_transport.EVENT.reset(event_token)
