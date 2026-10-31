@echo off
rem Compila "JT Conversor Multimedia.exe" en dist\  (requiere Python 3.10-3.15 de python.org)
setlocal
rem Si se lanza desde PowerShell 7, su PSModulePath rompe los cmdlets de Windows PowerShell 5.1
set "PSModulePath="
cd /d "%~dp0"
if not defined PY (where py >nul 2>&1 && set "PY=py -3" || set "PY=python")
if not exist .venv\Scripts\python.exe %PY% -m venv .venv || goto :error
.venv\Scripts\python -m pip install --disable-pip-version-check --require-hashes -r requirements.txt || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -File get-deps.ps1 || goto :error
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name "JT Conversor Multimedia" ^
  --icon assets\icon.ico --add-data "assets;assets" --add-binary "ffmpeg\ffmpeg.exe;ffmpeg" ^
  --add-data "libreoffice.zip;." --collect-data numbers_parser main.py || goto :error
echo.
echo Listo: dist\JT Conversor Multimedia.exe
exit /b 0
:error
echo.
echo ERROR: la compilacion ha fallado.
exit /b 1
