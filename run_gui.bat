@echo off
setlocal

:: Intentar encontrar Python en diferentes ubicaciones comunes
set PYTHON_PATHS=^
python.exe;^
py.exe;^
C:\Python311\python.exe;^
C:\Python310\python.exe;^
C:\Python39\python.exe;^
C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe;^
C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe;^
C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe

cd /d "%~dp0"

:: 1. Preferir el Python del entorno virtual del proyecto
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    echo Usando Python del entorno virtual: %VENV_PYTHON%
    "%VENV_PYTHON%" main.py --gui
    goto :eof
)

:: 2. Si no hay .venv, usar el Python del sistema
for %%p in (%PYTHON_PATHS%) do (
    where /Q %%p
    if not errorlevel 1 (
        echo Usando Python encontrado en: %%p
        %%p main.py --gui
        goto :eof
    )
)

echo No se pudo encontrar Python instalado en el sistema.
echo Por favor, instala Python desde https://www.python.org/downloads/
echo Asegurate de marcar la opcion "Add Python to PATH" durante la instalacion.
pause