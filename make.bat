@echo off

echo Creating executables ...
"C:\Program Files\Python\Python35-32\Scripts\pyinstaller-script.py" --clean --noconfirm --icon=dabamos.ico --hidden-import "modules.database" --hidden-import "modules.export" --hidden-import "modules.gpio" --hidden-import "modules.notification" --hidden-import "modules.port" --hidden-import "modules.processing" --hidden-import "modules.prototype" --hidden-import "modules.schedule" --hidden-import "modules.totalstation" --hidden-import "modules.virtual" openadms.py

echo Done.
pause