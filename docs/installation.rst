.. _installation:

Installation of OpenADMS Node
=============================

The following dependencies have to be installed at first in order to run
OpenADMS Node:

-  `CPython 3.6`_ or `PyPy3.5`_,
-  some additional Python modules (as described below),
-  *optional:* an MQTT message broker,
-  *optional:* the `Git`_ version control system.

Quick Start
-----------

You can run OpenADMS Node by following these steps:

1. Download and install `Python 3.6`_ or higher.

2. Download and unpack `OpenADMS`_.

3. In the OpenADMS Node directory, run ``python -m pip install -U -r
   requirements.txt`` or execute ``install.bat`` as an administrator on
   Microsoft Windows.

4. Write a configuration file for OpenADMS Node (see directory
   ``config/examples/`` for examples).

5. Run ``python3 openadms.py --config config/my_config.json --with-mqtt-broker
   --debug`` or start the graphical launcher ``openadms-launcher.pyw``.

Source Code
-----------

The release versions of OpenADMS Node are hosted on `GitHub`_. If you like to
download a more recent version, you can clone the master branch from the
`GitHub repository`_ using the Git version control system:

::

    $ git clone https://github.com/dabamos/openadms-node.git

The master branch is available as a `Zip archive`_ for those who do not want to
use Git.

Python
------

OpenADMS Node is written in Python. A recent Python 3 interpreter is required to
run the software. `CPython 3.6`_ and `PyPy3.5`_ are supported. Interpreters are
available for all modern operating systems.

Microsoft Windows Vista/7/8/10
    Download the latest release from the Python website and execute the
    installer. Please refer to the official `installation notes`_ of the Python
    documentation. It is strongly recommended to add Python to the ``PATH``
    variable of the system (see :numref:`python-path`).

Linux and Unix
    Install Python 3.6 by using your favourite package managing system or
    compile it from source.

macOS
    The latest version of Python is also available for download on the Python
    website.

.. _python-path:
.. figure:: _static/python_path.png
   :alt: Add Python to the ``PATH`` variable of Microsoft Windows
   :scale: 80%

   Add Python to the ``PATH`` variable of Microsoft Windows

Additional Modules
~~~~~~~~~~~~~~~~~~

OpenADMS Node depends on the following Python modules:

-  `arrow`_ (Apache 2.0 Licence),
-  `coloredlogs`_ (MIT Licence),
-  `CouchDB`_ (BSD Licence),
-  `HBMQTT`_ (MIT Licence),
-  `jsonschema`_ (MIT Licence)
-  `Mastodon.py`_ (MIT Licence)
-  `paho-mqtt`_ (Eclipse Public Licence),
-  `pyserial`_ (Python Software Foundation Licence).
-  `pytest`_ (MIT Licence)
-  `requests`_ (Apache 2.0 Licence),
-  `tinydb`_ (MIT Licence),
-  `uptime`_ (BSD-2-Clause Licence).
-  `verboselogs`_ (MIT Licence).

The (optional) graphical launcher requires `Gooey`_ (MIT Licence).

All modules can be installed with the Python package management system
(``pip``). Open the OpenADMS Node directory in your terminal (or ``cmd.exe``
with administrator privileges on Microsoft Windows) and then run:

::

    $ python3 -m pip install -U -r requirements.txt

Or, if you prefer PyPy3.5:

::

    $ pypy3 -m pip install -U -r requirements.txt

.. note::

    On Microsoft Windows, the script ``install.bat`` will download
    and install all necessary dependencies on CPython. Run the script
    with administrator rights.

Virtual Environment
~~~~~~~~~~~~~~~~~~~

The tool ``venv`` creates an independent Python environment. Further information
is given in the `Python online manual`_. On Linux/Unix with ``csh``/``tcsh``,
run:

::

    $ python -m venv virtual-environment
    $ source virtual-environment/bin/activate.csh
    $ git clone https://github.com/dabamos/openadms-node
    $ cd openadms-node/
    $ python -m pip install --user -U -r requirements.txt
    $ python openadms.py --config config/my_config.json --with-mqtt-broker --debug

Message Broker
--------------

The MQTT protocol is used for the internal and external message exchange in
OpenADMS Node. Therefore, it is necessary to install and run an MQTT message
broker before starting the monitoring system. Many implementations of message
brokers are available (`list of servers`_), some of them are open-source, for
example:

-  `Eclipse Mosquitto`_,
-  `HBMQTT`_,
-  `RabbitMQ`_ (MQTT via plug-in).

HBMQTT is installed as a dependency. The broker will be started by OpenADMS Node
if the parameter ``--with-mqtt-broker`` is used. It is also possible to start
HBMQTT manually in the command line with:

::

    $ hbmqtt


.. note::

    For testing only, the public sandbox broker of `Eclipse IoT`_ can be used.
    The server supports MQTT and WebSockets, both plain and TLS secured.  Access
    the server using the hostname ``iot.eclipse.org`` and port ``1883``. For
    encryption, use port ``8883``. MQTT over WebSockets runs on the ports ``80``
    and ``443``.

System Service
--------------

Microsoft Windows
~~~~~~~~~~~~~~~~~

.. note::

    This section is still under construction.

Linux
~~~~~

In case you are running a Linux distribution with the systemd init system, you
can use the provided unit file to start OpenADMS as a daemon. Copy the file
``openadms.service`` to ``/etc/systemd/system/``.  OpenADMS must be installed in
``/usr/local/sbin/openadms/``. The config will be loaded from
``/usr/local/etc/openadms/config.json``. You can alter these values in the
service file.

Be aware that no MQTT message broker will be started by this service.  You may
want to use an external broker, like Eclipse Mosquitto, or append the parameter
``-m`` to ``ExecStart`` in the service file to enable the internal broker.

The OpenADMS unit has to be loaded with:

::

    $ systemctl daemon-reload

Enable the unit to run OpenADMS as a service:

::

    $ systemctl enable openadms

Start the OpenADMS unit manually:

::

    $ systemctl start openadms

Stop the OpenADMS unit manually:

::

    $ systemctl stop openadms

Show the status of the OpenADMS unit, including whether it is running or not:

::

    $ systemctl status openadms

For more information regarding systemd, see the `Arch Linux Wiki`_.

FreeBSD
~~~~~~~
An rc.d script (``freebsd.rc``) is provided for FreeBSD to start OpenADMS Node
automatically at boot time. The script has to be moved and renamed to
``/usr/local/etc/rc.d/openadms``. It is recommended to run the install script
``freebsd_install.sh``, as it also creates the user ``openadms`` and all
necessary directories:

::

    $ sh ./freebsd_install.sh

Then, add the following line to your ``/etc/rc.conf``:

::

    openadms_enable="YES"

You can alter the default configuration of the daemon by adding the following
lines to ``/etc/rc.conf``:

::

    openadms_user="openadms" ➊
    openadms_config="/usr/local/etc/openadms/openadms.json" ➋
    openadms_path="/usr/local/sbin/openadms/openadms.py" ➌
    openadms_log="/var/log/openadms.log" ➍
    openadms_args="" ➎

1.  User to run OpenADMS Node as.
2.  File path of the configuration.
3.  File path of the Python script.
4.  File path of the log file.
5.  Additional command-line arguments.

OpenADMS Node can be started manually with:

::

    $ service openadms onestart

To stop it, run:

::

    $ service openadms onestop

Please note, that an MQTT message broker, like `Mosquitto`_, has to be started
first. Add the following line to your ``/etc/rc.conf`` to start Mosquitto
automatically:

::

    mosquitto_enable="YES"

The daemon can be started manually with:

::

    $ service mosquitto onestart

Instead of using an external MQTT message broker, you can also enable
the internal broker by adding the appropriate command-line argument to
``openadms_args`` in ``/etc/rc.conf``:

::

    openadms_args="--with-mqtt-broker"

NetBSD
~~~~~~
For NetBSD, the rc.d script ``netbsd.rc`` can be used to start OpenADMS Node as
a service. The script has to be moved and renamed to ``/etc/rc.d/openadms``.
OpenADMS must be installed to ``/usr/sbin/openadms/``. The configuration is
expected to be in ``/usr/etc/openadms/openadms.json`` and the log file will be
located at ``/var/log/openadms.log``. OpenADMS starts with the privileges of
user ``openadms``. You can add the user with:

::

    $ useradd -m -G dialer openadms
    $ passwd openadms

Enable OpenADMS in ``/etc/rc.conf``:

::

    openadms=YES

Add the following lines to ``/etc/rc.conf`` to alter the default configuration:

::

    openadms_user="openadms" ➊
    openadms_path="/usr/sbin/openadms/" ➋
    openadms_config="/usr/etc/openadms/openadms.json" ➌
    openadms_log="/var/log/openadms.log" ➍

1.  User to run OpenADMS Node as.
2.  File path of the configuration file.
3.  Path of the OpenADMS Node directory.
4.  File path of the log file.

Start OpenADMS manually with:

::

    $ service openadms onestart

To stop it, run:

::

    $ service openadms onestop


Stand-Alone Executables for Microsoft Windows
---------------------------------------------

OpenADMS can be compiled to a stand-alone executable (``.exe`` file) that does
not depend on a globally installed Python interpreter by using either
`PyInstaller`_, `cx\_Freeze`_, or `Nuitka`_.

PyInstaller
~~~~~~~~~~~

PyInstaller is capable of creating executables for many operating systems,
including Microsoft Windows. In order to use PyInstaller, `Microsoft Visual C++
2010 Redistributable Package`_ and the Python module itself have to be installed
at first. PyInstaller can be obtained with ``pip``:

::

    > python -m pip install PyInstaller


Build OpenADMS Node by running:

::

    > pyinstaller --clean --noconfirm --icon="extra\dabamos.ico" --hidden-import "modules.database" --hidden-import "modules.export" --hidden-import "modules.notification" --hidden-import "modules.port" --hidden-import "modules.processing" --hidden-import "modules.prototype" --hidden-import "modules.schedule" --hidden-import "modules.server" --hidden-import "modules.testing" --hidden-import "modules.totalstation" --hidden-import "modules.virtual" openadms.py

Build the graphical launcher with:

::

    > pyinstaller --clean --windowed --noconfirm --icon="extra\dabamos.ico" --hidden-import "gooey" --hidden-import "openadms" --hidden-import "modules.database" --hidden-import "modules.export" --hidden-import "modules.notification" --hidden-import "modules.port" --hidden-import "modules.processing" --hidden-import "modules.prototype" --hidden-import "modules.schedule" --hidden-import "modules.server" --hidden-import "modules.testing" --hidden-import "modules.totalstation" --hidden-import "modules.virtual" openadms-launcher.pyw


The binaries will be located in the sub-folder ``dist``. Copy the folders
``data``, ``config``, ``core``, ``modules``, ``schemes``, and ``sensors``
into ``dist``. Furthermore, copy folder ``C:\Python36\Lib\site-packages\gooey``
to ``dist\openadms-launcher\``. Execute ``openadms-launcher.exe`` to start the
OpenADMS graphical launcher.

cx\_Freeze
~~~~~~~~~~

Like PyInstaller, cx\_Freeze is cross platform library to create executables of
Python scripts. Install it with ``pip`` at first:

::

    > python -m pip install cx_Freeze appdirs packaging

Create a file ``setup.py`` with the following contents:

::

    #!/usr/bin/env python3.6

    """Setup for cx_Freeze

    This script creates executables for Microsoft Windows by using cx_Freeze.
    Just run::

        $ python setup.py build

    All files will be stored under ``dist/``."""

    import sys

    from cx_Freeze import setup, Executable

    from core.version import *


    build_exe_options = {
        'build_exe': 'dist',
        'packages': ['asyncio',
                     'appdirs',
                     'packaging',
                     'modules.database',
                     'modules.export',
                     'modules.notification',
                     'modules.port',
                     'modules.processing',
                     'modules.prototype',
                     'modules.schedule',
                     'modules.server',
                     'modules.testing',
                     'modules.totalstation',
                     'modules.virtual'],
        'excludes': ['tkinter'],
        'include_files': [
            'config',
            'data',
            'extra',
            'modules',
            'schemes',
            'sensors'
        ],
        'silent': True
    }

    base = None

    if sys.platform == 'win32':
        base = 'Win32GUI'

    executables = [
        Executable('openadms.py', base=base),
        Executable('openadms-launcher.pyw', base=base)
    ]

    setup(name='OpenADMS Node',
          version=str(OPENADMS_VERSION),
          description='OpenADMS Node',
          options={
              'build_exe': build_exe_options
          },
          executables=executables)

Build OpenADMS Node by running:

::

    > python setup.py build


You can then start the graphical launcher ``openadms-launcher.exe`` in
directory ``dist/``.

Nuitka
~~~~~~

Nuitka is a Python compiler that translates Python code into a C program that
is linked against ``libpython`` to execute it in the same way as CPython does.
Before OpenADMS Node can be compiled, install:

-  Python 3.6,
-  Python 2.7 (for `SCons`_),
-  Microsoft Visual Studio 2017 (and pywin32) or MinGW-w64,
-  Nuitka for Python 3.6.

If you prefer MinGW over Visual Studio, install it to ``C:\MinGW64`` and set the
environment variable ``CC`` to ``C:\MinGW64\mingw64\bin\gcc.exe``.

Build OpenADMS Node with:

::

    > nuitka --standalone --recurse-all --recurse-plugins=core --recurse-plugins=modules --recurse-not-to=modules.tests --recurse-not-to=modules.linux --recurse-not-to=modules.unix --show-progress --windows-disable-console --windows-icon=extra\dabamos.ico openadms-launcher.pyw

The compilation may take some time.

.. _Creative Commons Attribution-ShareAlike 3.0 Germany: https://creativecommons.org/licenses/by-sa/3.0/de/
.. _project website: https://www.dabamos.de/
.. _CPython 3.6: https://www.python.org/
.. _PyPy3.5: https://pypy.org/
.. _Git: https://git-scm.com/
.. _Python 3.6: https://www.python.org/
.. _OpenADMS: https://github.com/dabamos/openadms-node/releases
.. _GitHub: https://github.com/dabamos/openadms-node/releases
.. _GitHub repository: https://github.com/dabamos/openadms-node
.. _Zip archive: https://github.com/dabamos/openadms-node/archive/master.zip
.. _installation notes: https://docs.python.org/3/using/windows.html
.. _arrow: https://pypi.python.org/pypi/arrow
.. _coloredlogs: https://pypi.python.org/pypi/coloredlogs
.. _CouchDB: https://pypi.python.org/pypi/CouchDB
.. _jsonschema: https://pypi.python.org/pypi/jsonschema
.. _Mastodon.py: https://pypi.python.org/pypi/Mastodon.py
.. _paho-mqtt: https://pypi.python.org/pypi/paho-mqtt
.. _pyserial: https://pypi.python.org/pypi/pyserial
.. _pytest: https://pypi.python.org/pypi/pytest
.. _requests: https://pypi.python.org/pypi/requests
.. _tinydb: https://pypi.python.org/pypi/tinydb
.. _uptime: https://pypi.python.org/pypi/uptime
.. _verboselogs: https://pypi.python.org/pypi/verboselogs
.. _Gooey: https://pypi.python.org/pypi/Gooey
.. _Python online manual: https://docs.python.org/3/library/venv.html
.. _list of servers: https://github.com/mqtt/mqtt.github.io/wiki/servers
.. _Eclipse Mosquitto: http://mosquitto.org/
.. _HBMQTT: https://github.com/beerfactory/hbmqtt
.. _RabbitMQ: http://www.rabbitmq.com/
.. _Eclipse IoT: https://iot.eclipse.org/
.. _Arch Linux Wiki: https://wiki.archlinux.org/index.php/systemd
.. _Mosquitto: http://www.freshports.org/net/mosquitto/
.. _PyInstaller: http://www.pyinstaller.org/
.. _cx\_Freeze: https://anthony-tuininga.github.io/cx_Freeze/
.. _Nuitka: http://nuitka.net/
.. _Microsoft Visual C++ 2010 Redistributable Package: https://www.microsoft.com/de-de/download/details.aspx?id=14632
.. _SCons: http://scons.org/
