@echo off

echo Creating executables with Python 3.6 ...

pyinstaller --clean --windowed --noconfirm --icon="res\img\dabamos.ico" --hidden-import "gooey" --hidden-import "openadms" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.testing" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms-launcher.pyw
pyinstaller --clean --noconfirm --icon="res\img\dabamos.ico" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.testing" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms.py

mkdir dist\openadms-launcher\data

mkdir dist\openadms-launcher\config
robocopy "config" "dist\openadms-launcher\config" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

mkdir dist\openadms-launcher\core
robocopy "core" "dist\openadms-launcher\core" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

mkdir dist\openadms-launcher\module
robocopy "module" "dist\openadms-launcher\module" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

mkdir dist\openadms-launcher\res
robocopy "res" "dist\openadms-launcher\res" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

mkdir dist\openadms-launcher\schema
robocopy "schema" "dist\openadms-launcher\schema" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

mkdir dist\openadms-launcher\sensor
robocopy "sensor" "dist\openadms-launcher\sensor" *.* /e /NFL /NDL /NJH /NJS /nc /ns /np

echo Done.
echo.
echo "!!!!! ATTENTION !!!!!"
echo Copy folder "C:\Python36\Lib\site-packages\gooey" to "dist\openadms-launcher\"
echo.
pause
