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