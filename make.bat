@echo off

echo Creating executable ...
C:\Python34\python.exe setup.py py2exe

echo Copying configuration ...
xcopy config dist\config /E /I

echo Copying modules ...
xcopy modules dist\modules /E /I

echo Copying readme file ...
copy README.md dist

echo Copying licence file ...
copy LICENCE dist

echo Done.
pause