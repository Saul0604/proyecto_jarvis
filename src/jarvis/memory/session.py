"""Combina historial persistente con la ejecución del agente."""
from jarvis.agent.runner import run_task
from jarvis.config.settings import AgentSettings
from jarvis.domain.providers import ProviderError
from jarvis.observability.provider import ObservedProvider
from uuid import uuid4
from jarvis.memory.summarizer import compact_if_needed
from jarvis.domain.messages import FinishReason
from jarvis.storage.sqlite.conversations import ConversationStore


class ConversationSession:
    def __init__(self, provider, model, registry, store: ConversationStore | None, name="principal", *, settings=None, on_event=None):
        if not name.strip() or len(name) > 100:
            raise ValueError("El nombre de sesión debe tener entre 1 y 100 caracteres.")
        self.provider = provider
        self.model = model
        self.registry = registry
        self.store = store
        self.name = name
        self.settings = settings or AgentSettings()
        self.on_event = on_event or (lambda event: None)
        self.warnings = []

    async def ask(self, prompt):
        """Carga contexto, genera y guarda solo un turno que obtuvo respuesta."""
        if not prompt.strip():
            raise ValueError("Escribe un mensaje.")
        self.warnings = []
        task_id = uuid4().hex
        def emit(event):
            if event == "context_trimmed" and "Se omitió historial antiguo para respetar el presupuesto de la solicitud." not in self.warnings:
                self.warnings.append("Se omitió historial antiguo para respetar el presupuesto de la solicitud.")
            if self.store is not None:
                self.store.record_event(self.name, task_id, event)
            self.on_event(event)
        observed = ObservedProvider(self.provider, self.store, self.name, task_id, settings=self.settings)
        revision, history, omitted = (0, (), 0)
        if self.store is not None:
            try:
                summary_provider = ObservedProvider(self.provider, self.store, self.name, task_id, "summary", self.settings)
                emit("memory_check")
                await compact_if_needed(self.store, self.name, summary_provider, self.model)
            except ProviderError:
                warning = "No se pudo resumir la memoria. Se conserva el historial y se continúa con contexto reciente acotado."
                self.warnings.append(warning)
                emit("memory_fallback")
            revision, history, omitted = self.store.snapshot(self.name)
        response = await run_task(observed, self.model, prompt, self.registry, history=history,
                                  settings=self.settings, on_event=emit)
        if (self.store is not None and response.message.content
                and response.finish_reason is not FinishReason.CONTENT_FILTER):
            self.store.append(self.name, revision, prompt, response)
        return response, omitted
