@echo off
setlocal EnableExtensions
set "PY_VERSION="
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  for %%V in (3.14 3.13 3.12) do (
    if not defined PY_VERSION (
      py -%%V -c "import sys; sys.exit(not ((3,12) <= sys.version_info[:2] < (3,15)))" >nul 2>nul
      if not errorlevel 1 set "PY_VERSION=%%V"
    )
  )
)
if defined PY_VERSION (
    py -%PY_VERSION% "%~dp0scripts\bootstrap.py" %*
    goto :finished
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; sys.exit(not ((3,12) <= sys.version_info[:2] < (3,15)))" >nul 2>nul
  if not errorlevel 1 (
    python "%~dp0scripts\bootstrap.py" %*
    goto :finished
  )
)
echo Install Python 3.12, 3.13 or 3.14 from python.org, then run Start-Vridhi-Windows.cmd again.
pause
exit /b 1

:finished
set "RESULT=%ERRORLEVEL%"
if "%~1"=="" pause
exit /b %RESULT%
