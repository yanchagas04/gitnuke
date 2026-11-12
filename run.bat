@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo Erro: uv nao encontrado. Instale em https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)

uv sync
if errorlevel 1 exit /b %errorlevel%

uv run delete-github-repos
exit /b %errorlevel%
