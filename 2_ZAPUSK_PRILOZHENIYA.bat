@echo off
chcp 65001 >nul
title Luvvix - PRILOZHENIE
call "%~dp0_find_python.bat" || exit /b
cd /d "%~dp0mobile"
echo Ustanovka Kivy (pervyi raz dolgo)...
%PY% -m pip install kivy==2.3.1 || (echo OSHIBKA ustanovki & pause & exit /b)
echo Zapusk prilozheniya...
%PY% main.py
pause
