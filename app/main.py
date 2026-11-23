import asyncio
import json
import re
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.context import discover_project_files, read_project_context
from app.executor import execute_code


app = FastAPI(title="Lokaler Code-Assistent", version="1.0.0")


def build_local_answer(prompt: str, context: list[dict[str, str]]) -> str:
    text = prompt.lower()
    file_names = [item["path"] for item in context]

    if not context:
        if any(word in text for word in ("starte", "start", "laufen", "docker")):
            return ("Die Anwendung lässt sich vollständig lokal mit Docker starten:\n\n"
                    "```powershell\n"
                    "docker compose up -d --build\n"
                    "docker compose ps\n"
                    "```\n\n"
                    "Danach ist die App unter http://localhost:8000 erreichbar.")
        if any(word in text for word in ("test", "pytest")):
            return ("Für die Tests wird ein Python-Interpreter benötigt:\n\n"
                    "```powershell\n"
                    "python -m pytest tests/test_api.py -q\n"
                    "```\n\n"
                    "In Docker ist Python bereits Teil des Containers.")
        if any(word in text for word in ("hallo", "hi", "hey")):
            return "Hallo! Wähle Projektdateien als Kontext aus, dann kann ich sie analysieren und konkrete Verbesserungen ableiten."
        return ("Ich habe noch keinen Projektkontext erhalten. Wähle links Dateien aus oder stelle eine Frage zu Docker, Tests oder Architektur.")

    lines = [
        "## Projektanalyse",
        f"Ich habe **{len(context)} {('Datei' if len(context) == 1 else 'Dateien')}** ausgewertet:",
    ]
    lines.extend(f"- `{path}`" for path in file_names)

    if any(word in text for word in ("zusammen", "summary", "übersicht", "analys")):
        summaries = []
        for item in context:
            path = item["path"]
            content = item["content"]
            imports = re.findall(r"^(?:import|from)\s+([A-Za-z0-9_.]+)", content, re.MULTILINE)
            definitions = re.findall(r"^(?:def|class)\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
            details = []
            if imports:
                details.append(f"Abhängigkeiten: {', '.join(sorted(set(imports))[:8])}")
            if definitions:
                details.append(f"Symbole: {', '.join(definitions[:12])}")
            details.append(f"Größe: {len(content.splitlines())} Zeilen")
            summaries.append(f"### `{path}`\n" + "\n".join(f"- {detail}" for detail in details))
        lines.extend(["", *summaries])
    elif any(word in text for word in ("bug", "fehler", "problem", "prüf", "review")):
        findings = []
        for item in context:
            path = item["path"]
            content = item["content"]
            if "except:" in content:
                findings.append(f"`{path}` enthält einen zu breiten `except:`-Block.")
            if "TODO" in content:
                findings.append(f"`{path}` enthält offene TODO-Markierungen.")
            if len(content.splitlines()) > 500:
                findings.append(f"`{path}` ist mit über 500 Zeilen umfangreich und könnte modularisiert werden.")
            if path.endswith(".js") and "innerHTML" in content:
                findings.append(f"`{path}` verwendet `innerHTML`; dynamische Inhalte sollten escaped werden.")
            if path.endswith(".py") and "subprocess.run" in content:
                findings.append(f"`{path}` führt Prozesse aus; Timeout und argumentbasiertes Aufrufen sollten erhalten bleiben.")
        lines.extend(["", "## Prüfbefund"])
        lines.extend(f"- {finding}" for finding in findings[:12])
        if not findings:
            lines.append("- Keine offensichtlichen statischen Auffälligkeiten gefunden.")
    elif any(word in text for word in ("verbesser", "modern", "refactor", "code")):
        lines.extend([
            "",
            "## Empfehlungen",
            "- Fehlerbehandlung mit strukturierten HTTP-Responses konsistent halten.",
            "- Funktionsnamen und Datentypen klar und klein halten.",
            "- Neue Verhalten zunächst mit fokussierten API-Tests absichern.",
            "- Geheimnisse ausschließlich in `.env` halten und nie an den Browser senden.",
        ])
    else:
        selected = context[0]
        snippet = "\n".join(selected["content"].splitlines()[:30])
        lines.extend([
            "",
            "## Ausgewählte Datei",
            f"`{selected['path']}`",
            "",
            "```",
            snippet,
            "```",
            "",
            "Für eine gezielte Antwort verwende Begriffe wie **zusammenfassen**, **Fehler prüfen** oder **verbessern**.",
        ])
    return "\n".join(lines)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    project_files: list[str] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0, le=2)


class ContextRequest(BaseModel):
    paths: list[str]


class ExecuteRequest(BaseModel):
    language: Literal["python", "javascript"]
    code: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": "lokal"}


@app.get("/context/files")
def context_files() -> dict:
    return {"files": discover_project_files()}

@app.post("/context/read")
def context_read(request: ContextRequest) -> dict:
    return {"files": read_project_context(request.paths)}

@app.post("/chat")
async def chat(request: ChatRequest):
    context_files = read_project_context(request.project_files)
    prompt = request.messages[-1].content if request.messages else ""
    answer = build_local_answer(prompt, context_files)

    async def event_stream():
        for word in answer.split():
            yield f"data: {json.dumps({'delta': word + ' '}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.015)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/execute")
def execute(request: ExecuteRequest) -> dict:
    return execute_code(request.language, request.code)


app.mount("/", StaticFiles(directory="web", html=True), name="web")
