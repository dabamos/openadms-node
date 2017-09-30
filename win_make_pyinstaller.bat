@echo off

echo Creating executables with Python 3.6 ...

"C:\Python36\Scripts\pyinstaller-script.py" --clean --noconfirm --icon="res\img\dabamos.ico" --hidden-import "openadms" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.testing" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms-launcher.pyw

echo Done.
pause
