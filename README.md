# Lokaler Code-Assistent

Ein FastAPI-Dienst mit lokaler Projektanalyse, Chat-Streaming und isolierter Code-Ausführung ohne externe API.

## Voraussetzungen

- Python 3.11+
- Docker für `/execute` (optional)

## Start

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[test]"
uvicorn app.main:app --reload
```

Danach `http://localhost:8000` öffnen. Es werden keine API-Keys benötigt.

## API

Alle geschützten Endpunkte benötigen:

```text
X-API-Key: <APP_API_KEY>
```

- `GET /health`
- `GET /context/files`
- `POST /context/read` mit `{"paths":["app/main.py"]}`
- `POST /chat` mit `{"messages":[{"role":"user","content":"..."}],"project_files":["app/main.py"]}`
- `POST /execute` mit `{"language":"python","code":"print('hello')"}` oder `javascript`

Der Chat ist Server-Sent Events: Jede Nachricht enthält `data: {"delta":"..."}` und endet mit `data: [DONE]`.

## Sicherheit

- Niemals den OpenAI-Key oder `APP_API_KEY` in das Frontend oder Git committen.
- `/execute` läuft nur mit Docker, ohne Netzwerkzugang und mit Ressourcenlimits.
- Projektkontext ist auf `PROJECT_ROOT`, UTF-8 und eine Gesamtgröße von 2 MB begrenzt.
