@echo off

echo Installing Python dependencies ...
pip3 install --user pipenv
pipenv sync
pipenv install Gooey

echo Done.
pause