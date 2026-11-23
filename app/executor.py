import shutil
import subprocess

from fastapi import HTTPException

from app.config import settings

SUPPORTED_LANGUAGES = {
    "python": ("python:3.12-alpine", ["python", "-c"]),
    "javascript": ("node:22-alpine", ["node", "-e"]),
}


def execute_code(language: str, code: str) -> dict:
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Supported languages: python, javascript")
    if not shutil.which("docker"):
        raise HTTPException(
            status_code=503,
            detail="Code execution requires Docker",
        )
    if len(code.encode("utf-8")) > 100_000:
        raise HTTPException(status_code=413, detail="Code exceeds 100 KB")

    image, command = SUPPORTED_LANGUAGES[language]
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "128m",
                "--cpus",
                "0.5",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                image,
                *command,
                code,
            ],
            capture_output=True,
            text=True,
            timeout=settings.execution_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Execution timed out") from exc

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }
