@echo off
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
echo Instalando dependencias (so demora na primeira vez)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO: nao foi possivel instalar. Verifique se o Python esta instalado e se ha internet.
  pause
  exit /b 1
)
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:5000"
echo.
echo Servidor rodando. O navegador vai abrir sozinho. Para encerrar, feche esta janela.
%PY% app.py
pause
