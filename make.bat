@echo off

echo Creating executables ...
"C:\Program Files\Python\Python35-32\Scripts\pyinstaller-script.py" --clean --noconfirm --icon=dabamos.ico --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.gpio" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms.py

echo Done.
pause
