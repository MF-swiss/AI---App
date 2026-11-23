# OpenAI Code Assistant

Ein FastAPI-Dienst, der OpenAI-Chat-Streaming mit Projektdatei-Kontext und isolierter Code-Ausführung bereitstellt.

## Voraussetzungen

- Python 3.11+
- OpenAI API-Key
- Docker für `/execute` (optional)

## Start

```powershell
Copy-Item .env.example .env
# .env mit deinem OpenAI-Key und APP_API_KEY ausfüllen
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[test]"
uvicorn app.main:app --reload
```

Danach `http://localhost:8000` öffnen. Dort den in `.env` konfigurierten
`APP_API_KEY` in das Feld „API-Key“ eintragen. Der Schlüssel wird nur lokal im
Browser (`localStorage`) gespeichert. Dort den in `.env` konfigurierten
`APP_API_KEY` in das Feld „API-Key“ eintragen. Der Schlüssel wird nur lokal im
Browser (`localStorage`) gespeichert.

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
