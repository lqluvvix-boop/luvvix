@echo off
rem Find real python.exe (not Microsoft Store stub)
set PY=
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY (
  py -3 --version >nul 2>nul && set PY=py -3
)
if not defined PY (
  echo.
  echo ================================================================
  echo  PYTHON NE USTANOVLEN.
  echo  Skachayte i ustanovite:
  echo  https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
  echo  V pervom okne postavte galochku "Add python.exe to PATH",
  echo  nazhmite "Install Now", potom snova zapustite etot fayl.
  echo ================================================================
  echo.
  pause
  exit /b 1
)
echo Naiden Python: %PY%
exit /b 0
