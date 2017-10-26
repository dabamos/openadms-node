Running OpenADMS Node
=====================

OpenADMS can either be started from the command-line or by executing the
graphical launcher ``openadms-launcher.pyw``. The path to the configuration file
as well as additional options have to be set by using command-line parameters.

Microsoft Windows
-----------------

The easiest way to run OpenADMS on Microsoft Windows is to use the graphical
launcher ``openadms-launcher.pyw`` (see :numref:`openadms-launcher-screenshot`).
Please make sure that all dependencies are installed (execute ``install.bat``
with administrator privileges).

.. _openadms-launcher-screenshot:
.. figure:: _static/openadms_graphical_launcher.png
   :alt: Graphical launcher for OpenADMS
   :align: center
   :scale: 80%

   Graphical launcher for OpenADMS

Run ``cmd.exe`` or ``PowerShell.exe`` to start OpenADMS from command-line:

::

    > python openadms.py --config config\myconfig.json --with-mqtt-broker

Linux, Unix, and macOS
----------------------

OpenADMS can be started with an installed Python 3.6 interpreter
(:numref:`openadms-freebsd`):

::

    $ python openadms.py --config config/myconfig.json --with-mqtt-broker

Depending on the used operating system, the name of the Python binary may be
``python36`` or ``python3.6``. On Unix-like operating systems, ``openadms.py``
can be executed directly once the proper permissions are set:

::

    $ chmod ug+x openadms.py
    $ ./openadms.py --config config/my_config.json --with-mqtt-broker

.. _openadms-freebsd:
.. figure:: _static/openadms_urxvt.png
   :alt: Running OpenADMS on FreeBSD
   :align: center

   Running OpenADMS on FreeBSD

Additional Parameters
---------------------

OpenADMS Node can be started with parameters, for instance:

::

    $ python3 openadms.py -c ./config/my_config.json -m -d

The following parameters will be accepted:

+------------------------+------------+--------------------------+---------------------------+
| Parameter              | Short form | Default value            | Description               |
+========================+============+==========================+===========================+
| ``--config``           | ``-c``     | ``./config/config.json`` | Path to the configuration |
|                        |            |                          | file.                     |
+------------------------+------------+--------------------------+---------------------------+
| ``--debug``            | ``-d``     | off                      | Print debug messages.     |
+------------------------+------------+--------------------------+---------------------------+
| ``--verbosity``        | ``-v``     | ``6`` (info)             | Log more diagnostic       |
|                        |            |                          | messages (level 1 to 9).  |
+------------------------+------------+--------------------------+---------------------------+
| ``--log-file``         | ``-l``     | ``./openadms.log``       | Path and name of the log  |
|                        |            |                          | file.                     |
+------------------------+------------+--------------------------+---------------------------+
| ``--with-mqtt-broker`` | ``-m``     | off                      | Start internal MQTT       |
|                        |            |                          | message broker.           |
+------------------------+------------+--------------------------+---------------------------+
| ``--bind``             | ``-b``     | ``127.0.0.1``            | IP address or FQDN of     |
|                        |            |                          | internal MQTT message     |
|                        |            |                          | broker.                   |
+------------------------+------------+--------------------------+---------------------------+
| ``--port``             | ``-p``     | ``1883``                 | Port of internal MQTT     |
|                        |            |                          | message broker.           |
+------------------------+------------+--------------------------+---------------------------+
| ``--quiet``            | ``-q``     | off                      | Disable logging.          |
+------------------------+------------+--------------------------+---------------------------+

Available verbosity levels for the ``--verbosity`` parameter:

+-------+----------+
| Level | Name     |
+=======+==========+
| 1     | critical |
+-------+----------+
| 2     | error    |
+-------+----------+
| 3     | success  |
+-------+----------+
| 4     | warning  |
+-------+----------+
| 5     | notice   |
+-------+----------+
| 6     | info     |
+-------+----------+
| 7     | verbose  |
+-------+----------+
| 8     | debug    |
+-------+----------+
| 9     | spam     |
+-------+----------+

Running OpenADMS Node as a Service
----------------------------------

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

    $ systemctl start openadms

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

    > pyinstaller --clean --noconfirm --icon="res\img\dabamos.ico" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.testing" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms.py

Build the graphical launcher with:

::

    > pyinstaller --clean --windowed --noconfirm --icon="res\img\dabamos.ico" --hidden-import "gooey" --hidden-import "openadms" --hidden-import "module.database" --hidden-import "module.export" --hidden-import "module.notification" --hidden-import "module.port" --hidden-import "module.processing" --hidden-import "module.prototype" --hidden-import "module.schedule" --hidden-import "module.server" --hidden-import "module.testing" --hidden-import "module.totalstation" --hidden-import "module.virtual" openadms-launcher.pyw


The binaries will be located in the sub-folder ``dist``. Copy the folders
``data``, ``config``, ``core``, ``module``, ``res``, ``schema``, and ``sensor``
into ``dist``. Furthermore, copy folder ``C:\Python36\Lib\site-packages\gooey``
to ``dist\openadms-launcher\``. Execute ``openadms-launcher.exe`` to start the
OpenADMS graphical launcher.

cx\_Freeze
~~~~~~~~~~

Like PyInstaller, cx\_Freeze is cross platform library to create executables of
Python scripts. Install it with ``pip`` at first:

::

    > python -m pip install cx_Freeze

Create a file ``setup.py`` with the following contents:

::

    #!/usr/bin/env python3.6

    """Setup for cx_Freeze

    This script creates executables for Microsoft Windows by using cx_Freeze.
    Just run::

        $ python setup.py build

    All files will be stored under `./dist/`."""

    import sys

    from cx_Freeze import setup, Executable

    from core import version


    build_exe_options = {
        'build_exe': 'dist',
        'packages': ['asyncio',
                     'appdirs',
                     'packaging',
                     'module.database',
                     'module.export',
                     'module.notification',
                     'module.port',
                     'module.processing',
                     'module.prototype',
                     'module.schedule',
                     'module.server',
                     'module.testing',
                     'module.totalstation',
                     'module.virtual'],
        'excludes': ['tkinter'],
        'include_files': [
            'config',
            'data',
            'extra',
            'module',
            'schema',
            'sensor',
            'res'
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
          version=OPENADMS_VERSION,
          description='OpenADMS Node',
          options={
              'build_exe': build_exe_options
          },
          executables=executables)

Build OpenADMS Node by running:

::

    > python setup.py build


You can then start the graphical launcher ``openadms-launcher.exe`` in
directory ``./dist/``.

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

    > nuitka --standalone --python-version=3.6 --recurse-all --recurse-plugins=core --recurse-plugins=module --recurse-not-to=module.tests --recurse-not-to=module.linux --recurse-not-to=module.unix --show-progress --windows-disable-console --windows-icon=res/img/dabamos.ico openadms-launcher.pyw

The compilation may take some time.

.. _Arch Linux Wiki: https://wiki.archlinux.org/index.php/systemd
.. _Mosquitto: http://www.freshports.org/net/mosquitto/
.. _PyInstaller: http://www.pyinstaller.org/
.. _cx\_Freeze: https://anthony-tuininga.github.io/cx_Freeze/
.. _Nuitka: http://nuitka.net/
.. _Microsoft Visual C++ 2010 Redistributable Package: https://www.microsoft.com/de-de/download/details.aspx?id=14632
.. _SCons: http://scons.org/
