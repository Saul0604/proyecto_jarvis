"""Conversación por terminal con sesiones persistentes."""
import argparse
import asyncio
import http.client
import subprocess
import sys
import sqlite3
from pathlib import Path

from jarvis.bootstrap import build_provider
from jarvis.config.settings import load_settings
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


def speak_response(voice, response):
    if voice is None or not response.message.content or response.finish_reason is FinishReason.CONTENT_FILTER:
        return
    try:
        voice.speak(response.message.content)
    except (OSError, ValueError, RuntimeError, http.client.HTTPException, subprocess.CalledProcessError) as error:
        print(f"[Voz: {error}]", file=sys.stderr)


async def chat(session, voice=None):
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
            for warning in session.warnings:
                print(f"[Aviso: {warning}]")
            speak_response(voice, response)
        except (ProviderError, ValueError, OSError, sqlite3.Error) as error:
            print(f"Jarvis: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversa con Jarvis usando memoria local.")
    parser.add_argument("prompt", nargs="?", help="Mensaje; omítelo para conversar de forma interactiva.")
    parser.add_argument("--speak", action="store_true", help="Lee las respuestas con las voces de Microsoft.")
    parser.add_argument("--settings", type=Path, help="Ajustes del agente en JSON.")
    parser.add_argument("--activity", action="store_true", help="Muestra actividad sin contenido privado.")
    parser.add_argument("--profile", help="Perfil de config/models.json.")
    parser.add_argument("--config", type=Path, default=Path("config/models.json"))
    parser.add_argument("--files-root", type=Path, help="Carpeta autorizada para lectura.")
    parser.add_argument("--web", action="store_true", help="Habilita lectura y búsqueda web.")
    parser.add_argument("--session", default="principal", help="Nombre de la sesión que se guarda o retoma.")
    parser.add_argument("--db", type=Path, help="Archivo SQLite; por defecto var/jarvis.sqlite3 junto a config.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--usage", action="store_true", help="Muestra consumo por llamada de la sesión.")
    actions.add_argument("--history", action="store_true", help="Muestra el historial de la sesión.")
    actions.add_argument("--clear-memory", action="store_true", help="Borra el historial de la sesión.")
    actions.add_argument("--list-sessions", action="store_true", help="Lista las sesiones guardadas.")
    actions.add_argument("--no-memory", action="store_true", help="Ejecuta una consulta sin guardar ni recuperar historial.")
    args = parser.parse_args()
    management = args.history or args.clear_memory or args.list_sessions or args.usage
    if args.prompt is not None and not args.prompt.strip():
        parser.error("Escribe un mensaje.")
    if management and args.prompt is not None:
        parser.error("Usa las opciones de gestión de memoria sin un mensaje.")
    if args.no_memory and args.prompt is None:
        parser.error("--no-memory requiere un mensaje.")
    if not args.session.strip() or len(args.session) > 100:
        parser.error("El nombre de sesión debe tener entre 1 y 100 caracteres.")

    try:
        settings = load_settings(args.settings)
        store = None
        if not args.no_memory:
            database = args.db or args.config.resolve().parent.parent / "var" / "jarvis.sqlite3"
            store = ConversationStore(database)
        if args.usage:
            for item in store.usage(args.session):
                print(item)
            return 0
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

        from jarvis.config.env import load_local_env

        load_local_env(Path.cwd() / ".env")
        voice = None
        if args.speak:
            if sys.platform != "win32":
                raise ValueError("La voz de Microsoft requiere ejecutar Jarvis con Python de Windows.")
            from jarvis.interfaces.voice.windows import WindowsVoice
            voice = WindowsVoice()
        provider, model = build_provider(args.config, args.profile)
        session = ConversationSession(provider, model, build_tools(args.files_root, args.web), store, args.session,
                                      settings=settings, on_event=(lambda event: print(f"[Actividad: {event}]")) if args.activity else None)
        if args.prompt is None:
            asyncio.run(chat(session, voice))
        else:
            response, omitted = asyncio.run(session.ask(args.prompt))
            show_response(response, omitted)
            for warning in session.warnings:
                print(f"[Aviso: {warning}]")
            speak_response(voice, response)
    except KeyboardInterrupt:
        print("\nConversación interrumpida.")
        return 130
    except (OSError, ValueError, ProviderError, sqlite3.Error) as error:
        parser.exit(1, f"Jarvis: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
