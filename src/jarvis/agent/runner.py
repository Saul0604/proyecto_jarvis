"""Coordina herramientas y reserva una llamada para cerrar la tarea."""
import asyncio
from dataclasses import replace

from jarvis.agent.context import bounded_result, enforce_budget
from jarvis.config.settings import AgentSettings
from jarvis.domain.messages import Message, Role
from jarvis.domain.providers import ModelRequest, ProviderError
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.registry import ToolRegistry


class TaskIncompleteError(ProviderError):
    def __init__(self, reason, executed_calls):
        self.executed_calls = tuple(executed_calls)
        super().__init__(f"Tarea incompleta: {reason} Herramientas ejecutadas: {len(executed_calls)}. "
                         "No se confirmó un resultado final.")


async def run_task(provider, model, prompt, registry: ToolRegistry, max_steps=None, *, history=(), settings=None, on_event=None):
    settings = settings or AgentSettings()
    if max_steps is not None:
        settings = replace(settings, max_steps=max_steps)
    emit = on_event or (lambda event: None)
    messages = [Message(Role.SYSTEM, settings.system_prompt), *history, Message(Role.USER, prompt)]
    executor = ToolExecutor(registry)
    executed = []
    # Reducir solo historial anterior, por turnos completos. Nunca partir pares tool/result.
    def request():
        return ModelRequest(model, tuple(messages), tools=registry.definitions,
                            max_output_tokens=settings.max_output_tokens_per_call)
    while len(messages) > 2:
        try:
            enforce_budget(request(), settings.max_request_characters)
            break
        except ProviderError:
            del messages[1]
            while len(messages) > 2 and messages[1].role is not Role.USER:
                del messages[1]
            emit("context_trimmed")
    try:
        async with asyncio.timeout(settings.task_timeout_seconds):
            for step in range(settings.max_steps + 1):
                closing = step == settings.max_steps
                if closing:
                    messages.append(Message(Role.USER,
                        "Se agotó el presupuesto de herramientas. Responde con los resultados disponibles, "
                        "indica qué sigue pendiente y no solicites más herramientas."))
                current = request()
                enforce_budget(current, settings.max_request_characters)
                emit("model_started")
                response = await provider.generate(current)
                if not response.message.tool_calls:
                    return response
                if closing:
                    raise TaskIncompleteError("el modelo solicitó más acciones al cerrar.", executed)
                if len(response.message.tool_calls) > 5:
                    raise TaskIncompleteError("demasiadas herramientas en un turno.", executed)
                messages.append(response.message)
                for call in response.message.tool_calls:
                    emit(f"tool_started:{call.name}")
                    result = await executor.execute(call)
                    executed.append((call.id, call.name, result.ok))
                    emit(f"tool_finished:{call.name}:{'ok' if result.ok else 'error'}")
                    messages.append(Message(Role.TOOL,
                        bounded_result(result, settings.max_tool_result_characters), tool_call_id=call.id))
    except TimeoutError:
        raise TaskIncompleteError("se alcanzó el tiempo límite; una operación en un hilo puede seguir activa.", executed) from None
    except TaskIncompleteError:
        raise
    except ProviderError as error:
        if executed:
            raise TaskIncompleteError(str(error), executed) from error
        raise
