@echo off
chcp 65001 >nul
title Luvvix - SERVER (ne zakryvayte eto okno)
call "%~dp0_find_python.bat" || exit /b
cd /d "%~dp0backend"
echo Ustanovka bibliotek servera (pervyi raz dolgo)...
%PY% -m pip install -r requirements.txt || (echo OSHIBKA ustanovki & pause & exit /b)
echo.
echo ================================================================
echo  Server zapuskaetsya. Kod dlya vhoda poyavitsya v etom okne.
echo  NE ZAKRYVAYTE eto okno, poka polzuetes prilozheniem.
echo ================================================================
%PY% -m uvicorn app.main:app --port 8000
pause
