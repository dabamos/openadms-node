@echo off

echo Installing Python dependencies ...
pip.exe install -U -r %~dp0\requirements.txt
pip.exe install Gooey

echo Done.
pause