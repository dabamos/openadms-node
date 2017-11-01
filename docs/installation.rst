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
   ``./config/examples/`` for examples).

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
    $ cd openadms-node
    $ python -m pip install -U -r requirements.txt
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
