"""Show what happened in a GitHub Copilot chat session (Copilot harness).

Reads ~/.copilot/session-state/<session>/events.jsonl and prints a readable
timeline: agent and tools, model, prompt sections, tool calls, permissions
and token usage. Read-only: it never changes any file.

Usage:
    python scripts/ver_sesion.py          # most recent session
    python scripts/ver_sesion.py 2        # second most recent session
    python scripts/ver_sesion.py <path>   # a specific events.jsonl file
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

SESSIONS = Path.home() / ".copilot" / "session-state"


def find_events_file(arg: str | None) -> Path:
    if arg and Path(arg).is_file():
        return Path(arg)
    index = int(arg) - 1 if arg and arg.isdigit() else 0
    folders = sorted(
        (f for f in SESSIONS.iterdir() if (f / "events.jsonl").is_file()),
        key=lambda f: (f / "events.jsonl").stat().st_mtime,
        reverse=True,
    )
    if index >= len(folders):
        sys.exit(f"No session number {index + 1} in {SESSIONS}")
    return folders[index] / "events.jsonl"


def short(text: object, limit: int = 110) -> str:
    value = " ".join(str(text).split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def show(time: str, label: str, text: str) -> None:
    print(f"{time}  {label:<8}{text}")


def describe_system_prompt(content: str) -> None:
    print(f"    Prompt de sistema: {len(content):,} caracteres. Incluye:")
    tools = re.search(r"<tools>(.*?)</tools>", content, re.S)
    if tools:
        names = list(dict.fromkeys(re.findall(r"^<([a-z_]+)>", tools.group(1), re.M)))
        names = [n for n in names if n != "available_skills"]
        print(f"      - apartados sobre herramientas: {', '.join(names)}")
    for match in re.finditer(r"<custom_instruction>(.*?)</custom_instruction>", content, re.S):
        first_line = match.group(1).strip().splitlines()[0]
        print(f"      - instrucciones del repositorio: «{short(first_line, 60)}»")
    agent = re.search(r"<agent_instructions>(.*?)</agent_instructions>", content, re.S)
    if agent:
        lines = [line for line in agent.group(1).strip().splitlines() if line.strip()]
        print(f"      - instrucciones del agente: «{short(lines[0], 70)}»")
        if len(lines) > 1:
            print(f"        «{short(lines[1], 80)}»")


def describe(kind: str, data: dict[str, Any], time: str, calls: int) -> int:
    if kind == "session.start":
        version = data.get("copilotVersion", "")
        show(time, "INICIO", f"harness Copilot CLI {version}, modelo: {data.get('selectedModel')}")
    elif kind == "subagent.selected":
        show(time, "AGENTE", f"{data.get('agentName')}  ·  herramientas: {data.get('tools')}")
    elif kind == "session.auto_mode_resolved":
        reason = short(data.get("selectionReason", ""), 80)
        show(time, "MODELO", f"{data.get('chosenModel')}  ({reason})")
    elif kind == "user.message":
        show(time, "TÚ", f"«{short(data.get('content', ''))}»")
        extra = len(data.get("transformedContent", "")) - len(data.get("content", ""))
        if extra > 0:
            print(f"{'':18}el harness añade {extra:,} caracteres (fecha, estructura…)")
    elif kind == "system.message":
        describe_system_prompt(data.get("content", ""))
    elif kind == "assistant.message":
        for request in data.get("toolRequests") or []:
            args = short(json.dumps(request.get("arguments", {}), ensure_ascii=False), 90)
            show(time, "MODELO", f"pide la herramienta «{request.get('name')}» con {args}")
        if data.get("content"):
            show(time, "MODELO", f"responde: «{short(data['content'], 120)}»")
    elif kind == "permission.requested":
        request = data.get("permissionRequest", {})
        intention = short(request.get("intention", ""), 90)
        show(time, "PERMISO", f"pedido ({request.get('kind')}): {intention}")
    elif kind == "permission.completed":
        result = (data.get("result") or {}).get("kind")
        show(time, "PERMISO", f"{result}  (decide: {data.get('decisionSource', '?')})")
    elif kind == "tool.execution_complete":
        ok = "correcta" if data.get("success") else "FALLIDA"
        size = len(str((data.get("result") or {}).get("content", "")))
        show(time, "HARNESS", f"ejecuta la herramienta: {ok}; devuelve {size:,} caracteres")
    elif kind == "session.usage_record":
        usage = data.get("usage", {})
        calls += 1
        tokens_in = usage.get("inputTokens", 0)
        tokens_out = usage.get("outputTokens", 0)
        show(
            time,
            "LLAMADA",
            f"al modelo nº {calls}: {tokens_in:,} tokens de entrada, {tokens_out:,} de salida",
        )
    return calls


def main() -> None:
    path = find_events_file(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"Archivo: {path}")
    print(f'Para verlo en bruto: code "{path}"\n')
    calls = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        time = str(event.get("timestamp", ""))[11:19]
        calls = describe(event.get("type", ""), event.get("data") or {}, time, calls)
    print(f"\nTotal: {calls} llamadas al modelo.")


if __name__ == "__main__":
    main()
