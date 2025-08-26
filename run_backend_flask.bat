@echo off
setlocal
cd /d "%~dp0"

set VENV_DIR=.venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [INFO] Criando venv...
  py -3 -m venv "%VENV_DIR%" 2>nul || python -m venv "%VENV_DIR%"
)

echo [INFO] Atualizando pip/setuptools/wheel...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

echo [INFO] Instalando deps: Pillow, Flask, Flask-CORS, PyMuPDF, PyPDF2, requests...
"%VENV_DIR%\Scripts\python.exe" -m pip install --only-binary=:all: "pillow>=10.4" || ^
"%VENV_DIR%\Scripts\python.exe" -m pip install "pillow>=10.4"
"%VENV_DIR%\Scripts\python.exe" -m pip install flask flask-cors pymupdf PyPDF2==3.0.1 requests

echo.
echo [INFO] Para usar IA em nuvem (OpenAI) defina antes de rodar:
echo   set OPENAI_API_KEY=SEU_TOKEN_AQUI
echo   set OPENAI_MODEL=gpt-4o-mini
echo.
echo [INFO] Para IA local com Ollama: instale o Ollama, execute 'ollama pull mistral' e deixe ativo em http://localhost:11434
echo.

echo [INFO] Subindo servidor Flask em http://127.0.0.1:8000 ...
"%VENV_DIR%\Scripts\python.exe" -m backend.backend_flask

pause
