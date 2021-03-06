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

install_pipenv() {
  pkg install devel/py-pipenv
}

install_modules() {
  pipenv lock
  pipenv sync
}

copy_rc() {
  cp services/openadms.freebsd /usr/local/etc/rc.d/openadms
}

install() {
  echo
  echo "Creating user ..."
  create_user

  echo "Creating directories ..."
  create_dirs

  echo "Copying files ..."
  copy_files

  echo "Installing pipenv ..."
  install_pipenv

  echo "Syncing dependencies ..."
  install_modules

  echo "Installing rc.d script ..."
  copy_rc

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
