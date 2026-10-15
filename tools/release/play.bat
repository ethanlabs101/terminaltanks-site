@echo off
cd /d "%~dp0"
where py >nul 2>nul && goto usepy
where python >nul 2>nul && goto usepython
echo Python 3.10 or newer was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
pause
exit /b 1
:usepy
py -3 terminaltanks.py %*
goto done
:usepython
python terminaltanks.py %*
:done
if errorlevel 1 pause
