"""Combina historial persistente con la ejecución del agente."""
from jarvis.agent.runner import run_task
from jarvis.memory.summarizer import compact_if_needed
from jarvis.domain.messages import FinishReason
from jarvis.storage.sqlite.conversations import ConversationStore


class ConversationSession:
    def __init__(self, provider, model, registry, store: ConversationStore | None, name="principal"):
        if not name.strip() or len(name) > 100:
            raise ValueError("El nombre de sesión debe tener entre 1 y 100 caracteres.")
        self.provider = provider
        self.model = model
        self.registry = registry
        self.store = store
        self.name = name

    async def ask(self, prompt):
        """Carga contexto, genera y guarda solo un turno que obtuvo respuesta."""
        if not prompt.strip():
            raise ValueError("Escribe un mensaje.")
        revision, history, omitted = (0, (), 0)
        if self.store is not None:
            await compact_if_needed(self.store, self.name, self.provider, self.model)
            revision, history, omitted = self.store.snapshot(self.name)
        response = await run_task(self.provider, self.model, prompt, self.registry, history=history)
        if (self.store is not None and response.message.content
                and response.finish_reason is not FinishReason.CONTENT_FILTER):
            self.store.append(self.name, revision, prompt, response)
        return response, omitted
