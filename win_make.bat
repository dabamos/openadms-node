@echo off

echo Creating executables with Python 3.6 ...

:: PyInstaller does not support Python 3.6 yet
:: "C:\Program Files\Python\Python36-64\Scripts\pyinstaller-script.py" --clean --noconfirm --icon="res\img\dabamos.ico" --hidden-import "openadms" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.linux" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms-gui.pyw

:: Using cx_Freeze instead ...
python setup.py build

echo Done.
pause
