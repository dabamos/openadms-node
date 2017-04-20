@echo off

echo Creating executables ...
"C:\Program Files\Python\Python35-32\Scripts\pyinstaller-script.py" --clean --noconfirm --icon=dabamos.ico --hidden-import "hbmqtt" launcher.py
"C:\Program Files\Python\Python35-32\Scripts\pyinstaller-script.py" --clean --noconfirm --icon=dabamos.ico --hidden-import "modules.database" --hidden-import "modules.export" --hidden-import "modules.gpio" --hidden-import "modules.notification" --hidden-import "modules.port" --hidden-import "modules.processing" --hidden-import "modules.prototype" --hidden-import "modules.schedule" --hidden-import "modules.totalstation" --hidden-import "modules.virtual" openadms.py

echo Copying OpenADMS.exe
xcopy dist\openadms\openadms.exe dist\launcher /E /I

echo Copying configuration ...
xcopy config dist\launcher\config /E /I

echo Copying modules ...
xcopy modules dist\launcher\modules /E /I

echo Copying readme file ...
copy README.md dist\launcher

echo Copying licence file ...
copy LICENCE dist\launcher

echo Cleaning up ...
del launcher.spec /q
del openadms.spec /q
rmdir dist\openadms /s /q
move dist\launcher dist\openadms

echo Done.
pause