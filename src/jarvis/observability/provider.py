"""Registra cada llamada sin almacenar prompts, respuestas ni credenciales."""
import asyncio
import time
from uuid import uuid4


class ObservedProvider:
    def __init__(self, provider, store, session, task_id=None, phase="agent", settings=None):
        self.provider = provider
        self.store = store
        self.session = session
        self.task_id = task_id or uuid4().hex
        self.phase = phase
        self.settings = settings

    async def generate(self, request):
        from jarvis.agent.context import enforce_budget
        if self.settings:
            enforce_budget(request, self.settings.max_request_characters)
        started = time.monotonic()
        response = None
        status = "ok"
        try:
            response = await self.provider.generate(request)
            return response
        except asyncio.CancelledError:
            status = "cancelled"
            raise
        except Exception as error:
            status = type(error).__name__
            raise
        finally:
            if self.store is not None:
                self.store.record_call(self.session, self.task_id, self.phase, request.model,
                    response.provider if response else None, status,
                    int((time.monotonic() - started) * 1000), response.usage if response else None)
