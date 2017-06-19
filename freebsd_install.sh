#!/bin/sh

OPENADMS_PATH=/usr/local/sbin/openadms
OPENADMS_CONFIG_PATH=/usr/local/etc/openadms
OPENADMS_USER="openadms"

create_dirs() {
  mkdir -p $OPENADMS_PATH
  mkdir -p $OPENADMS_CONFIG_PATH
}

copy_files() {
  cp -r . $OPENADMS_PATH
  chown -R $OPENADMS_USER $OPENADMS_PATH

  cp -r ./config/ $OPENADMS_CONFIG_PATH
  chown -R $OPENADMS_USER $OPENADMS_CONFIG_PATH
}

install_pip() {
  python3.6 -m ensurepip
}

install_modules() {
  python3.6 -m pip install -U -r $OPENADMS_PATH/requirements.txt
}

copy_rc() {
  cp freebsd.rc /usr/local/etc/rc.d/openadms
}

clear

DIALOG=dialog
(
echo "10" ; sleep 1
echo "XXX"; echo "Creating directories ..." ; echo "XXX"
create_dirs

echo "30" ; sleep 1
echo "XXX"; echo "Copying files ..." ; echo "XXX"
copy_files

echo "50" ; sleep 1
echo "XXX"; echo "Installing pip for Python 3.6 ..." ; echo "XXX"
install_pip

echo "70" ; sleep 1
echo "XXX"; echo "Installing Python dependencies ..." ; echo "XXX"
install_modules

echo "80" ; sleep 1
echo "XXX"; echo "Installing rc.d script ..." ; echo "XXX"
copy_rc

echo "100"
echo "XXX"; echo "Done." ; echo "XXX"; sleep 2
) |
$DIALOG --title "Installation of OpenADMS" --gauge "Please wait ..." 8 60
$DIALOG --clear

