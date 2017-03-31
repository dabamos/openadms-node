@echo off

echo Create executable ...
C:\Python34\python.exe setup.py py2exe

echo Copy configuration ...
xcopy config dist\config /E /I

echo Copy modules ...
xcopy modules dist\modules /E /I

echo Done.
pause