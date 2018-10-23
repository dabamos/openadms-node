@echo off

echo Installing Python dependencies ...
pip3 install --user pipenv
pipenv lock
pipenv sync
pipenv install Gooey

echo Done.
pause
