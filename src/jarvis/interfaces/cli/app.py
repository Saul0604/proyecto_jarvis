"""Conversación por terminal con sesiones persistentes."""
import argparse
import asyncio
import sqlite3
from pathlib import Path

from jarvis.bootstrap import build_provider
from jarvis.domain.messages import FinishReason
from jarvis.domain.providers import ProviderError
from jarvis.memory.session import ConversationSession
from jarvis.storage.sqlite.conversations import ConversationStore
from jarvis.tools.registry import build_tools


def show_response(response, omitted):
    if omitted:
        print(f"[Contexto: {omitted} turnos antiguos quedaron fuera de esta consulta.]")
    if response.message.content:
        print(response.message.content)
    if response.finish_reason is FinishReason.CONTENT_FILTER:
        print("Bedrock interrumpió la generación por un filtro de contenido.")
    elif response.finish_reason is FinishReason.LENGTH:
        print("La respuesta puede estar incompleta porque se alcanzó un límite.")


async def chat(session):
    print(f"Sesión {session.name}. Escribe /salir para terminar.")
    while True:
        try:
            prompt = input("Tú> ")
        except EOFError:
            return
        if prompt.strip().lower() == "/salir":
            return
        if not prompt.strip():
            continue
        try:
            response, omitted = await session.ask(prompt)
            show_response(response, omitted)
        except (ProviderError, ValueError, OSError, sqlite3.Error) as error:
            print(f"Jarvis: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversa con Jarvis usando memoria local.")
    parser.add_argument("prompt", nargs="?", help="Mensaje; omítelo para conversar de forma interactiva.")
    parser.add_argument("--profile", help="Perfil de config/models.json.")
    parser.add_argument("--config", type=Path, default=Path("config/models.json"))
    parser.add_argument("--files-root", type=Path, help="Carpeta autorizada para lectura.")
    parser.add_argument("--web", action="store_true", help="Habilita lectura y búsqueda web.")
    parser.add_argument("--session", default="principal", help="Nombre de la sesión que se guarda o retoma.")
    parser.add_argument("--db", type=Path, help="Archivo SQLite; por defecto var/jarvis.sqlite3 junto a config.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--history", action="store_true", help="Muestra el historial de la sesión.")
    actions.add_argument("--clear-memory", action="store_true", help="Borra el historial de la sesión.")
    actions.add_argument("--list-sessions", action="store_true", help="Lista las sesiones guardadas.")
    actions.add_argument("--no-memory", action="store_true", help="Ejecuta una consulta sin guardar ni recuperar historial.")
    args = parser.parse_args()
    management = args.history or args.clear_memory or args.list_sessions
    if args.prompt is not None and not args.prompt.strip():
        parser.error("Escribe un mensaje.")
    if management and args.prompt is not None:
        parser.error("Usa las opciones de gestión de memoria sin un mensaje.")
    if args.no_memory and args.prompt is None:
        parser.error("--no-memory requiere un mensaje.")
    if not args.session.strip() or len(args.session) > 100:
        parser.error("El nombre de sesión debe tener entre 1 y 100 caracteres.")

    try:
        store = None
        if not args.no_memory:
            database = args.db or args.config.resolve().parent.parent / "var" / "jarvis.sqlite3"
            store = ConversationStore(database)
        if args.list_sessions:
            for item in store.sessions():
                print(f"{item['name']}: {item['turns']} turnos")
            return 0
        if args.clear_memory:
            store.clear(args.session)
            print(f"Historial borrado: {args.session}")
            return 0
        if args.history:
            summary = store.summary(args.session)
            if summary:
                print(f"[Resumen acumulado]\n{summary}\n")
            for turn in store.history(args.session):
                print(f"[{turn['created_at']}] Tú: {turn['prompt']}")
                print(f"Jarvis ({turn['model']}): {turn['reply']}")
            return 0

        provider, model = build_provider(args.config, args.profile)
        session = ConversationSession(provider, model, build_tools(args.files_root, args.web), store, args.session)
        if args.prompt is None:
            asyncio.run(chat(session))
        else:
            response, omitted = asyncio.run(session.ask(args.prompt))
            show_response(response, omitted)
    except KeyboardInterrupt:
        print("\nConversación interrumpida.")
        return 130
    except (OSError, ValueError, ProviderError, sqlite3.Error) as error:
        parser.exit(1, f"Jarvis: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
