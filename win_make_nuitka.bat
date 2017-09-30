@echo off

echo Compiling OpenADMS ...

nuitka --standalone --python-version=3.6 --python-arch=x86_64 --recurse-stdlib --python-flag=no_site --recurse-to=multiprocessing --recurse-to=six --recurse-to=urllib3 --recurse-plugins=core --recurse-plugins=module --recurse-not-to=module.tests --recurse-not-to=module.linux --recurse-not-to=module.unix --output-dir=dist --jobs 4 --show-progress --windows-disable-console --windows-icon=res/img/dabamos.ico openadms.py

echo Done.
pause