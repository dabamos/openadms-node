#!/bin/sh

OPENADMS_PATH=/usr/local/sbin/openadms
OPENADMS_CONFIG_PATH=/usr/local/etc/openadms
OPENADMS_USER="openadms"

create_user() {
  if pw group show $OPENADMS_USER | grep -qv "^$OPENADMS_USER" ; then
    pw groupadd $OPENADMS_USER -g 5000
  fi

  if pw user show $OPENADMS_USER | grep -qv "^$OPENADMS_USER" ; then
    pw useradd -n $OPENADMS_USER -c OpenADMS Owner -g $OPENADMS_USER -s /usr/sbin/nologin -d /nonexistent
  fi
}

create_dirs() {
  mkdir -p $OPENADMS_PATH
  mkdir -p $OPENADMS_CONFIG_PATH
}

copy_files() {
  cp -r . $OPENADMS_PATH
  rm -r $OPENADMS_PATH/config
  rm -r $OPENADMS_PATH/data
  chown -R $OPENADMS_USER $OPENADMS_PATH

  cp -r ./config/ $OPENADMS_CONFIG_PATH
  chown -R $OPENADMS_USER $OPENADMS_CONFIG_PATH
}

install_pip() {
  if pip3 --version | grep -qv "python 3.6" ; then
    python3.6 -m ensurepip
  fi
}

install_modules() {
  pip3 -q install -U -r $OPENADMS_PATH/requirements.txt
}

copy_rc() {
  cp freebsd.rc /usr/local/etc/rc.d/openadms
}

install() {
  echo
  echo -n "Creating user ...                  "
  create_user
  sleep 0.25 ; echo "[OK]"

  echo -n "Creating directories ...           "
  create_dirs
  sleep 0.25 ; echo "[OK]"

  echo -n "Copying files ...                  "
  copy_files
  sleep 0.25 ; echo "[OK]"

  echo -n "Installing pip for Python 3.6 ...  "
  install_pip
  sleep 0.25 ; echo "[OK]"

  echo -n "Installing Python dependencies ... "
  install_modules
  sleep 0.25 ; echo "[OK]"

  echo -n "Installing rc.d script ...         "
  copy_rc
  sleep 0.25 ; echo "[OK]"

  echo ; echo "Add the following line to /etc/rc.conf:" ; echo
  echo "    openadms_enable=\"YES\"" ; echo
}

if uname | grep -qv "FreeBSD" ; then
  echo "You are not running FreeBSD"
  exit
fi

echo -n "Install OpenADMS? [y/n] "
read answer

if echo "$answer" | grep -iq "^y" ; then
  install
fi
