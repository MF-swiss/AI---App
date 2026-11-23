import json
from typing import Literal

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.context import discover_project_files, read_project_context
from app.executor import execute_code
from app.security import require_app_key


app = FastAPI(title="OpenAI Code Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a precise senior software engineer.
Help the user understand, modify, debug, and build software.
When editing code, return complete file contents or clearly marked patches.
Explain important tradeoffs concisely and never claim a change was tested unless it was.
Use the supplied project context and keep answers focused."""


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
    return {"status": "ok", "model": settings.openai_model}


@app.get("/context/files", dependencies=[Depends(require_app_key)])
def context_files() -> dict:
    return {"files": discover_project_files()}


@app.post("/context/read", dependencies=[Depends(require_app_key)])
def context_read(request: ContextRequest) -> dict:
    return {"files": read_project_context(request.paths)}


@app.post("/chat", dependencies=[Depends(require_app_key)])
async def chat(request: ChatRequest):
    context_files = read_project_context(request.project_files)
    context_text = "\n\n".join(
        f"### {item['path']}\n```\n{item['content']}\n```"
        for item in context_files
    )

    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context_text:
        openai_messages.append(
            {
                "role": "system",
                "content": f"Project context:\n{context_text}",
            }
        )
    openai_messages.extend(
        {"role": message.role, "content": message.content}
        for message in request.messages
    )

    stream = client.chat.completions.create(
        model=settings.openai_model,
        messages=openai_messages,
        temperature=request.temperature,
        stream=True,
    )

    def event_stream():
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            stream.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/execute", dependencies=[Depends(require_app_key)])
def execute(request: ExecuteRequest) -> dict:
    return execute_code(request.language, request.code)


app.mount("/", StaticFiles(directory="web", html=True), name="web")
