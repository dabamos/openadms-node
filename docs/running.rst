Running OpenADMS Node
=====================

OpenADMS can either be started from the command-line or by executing the
graphical launcher ``openadms-launcher.pyw``. The path to the configuration file
as well as additional options have to be set by using command-line arguments.

.. _openadms-launcher-screenshot:
.. figure:: _static/openadms_graphical_launcher.png
   :alt: Graphical launcher for OpenADMS
   :align: center
   :scale: 80%

   Graphical launcher for OpenADMS

Microsoft Windows
-----------------

The easiest way to run OpenADMS on Microsoft Windows is to use the graphical
launcher ``openadms-launcher.pyw`` (see :numref:`openadms-launcher-screenshot`).
Please make sure that all dependencies are installed (execute ``install.bat``
with administrator privileges).

Run ``cmd.exe`` or ``PowerShell.exe`` to start OpenADMS from command-line:

::

    > python openadms.py --config config\config.json --with-mqtt-broker

Press ``^C`` (``CTRL`` + ``C``) to stop OpenADMS Node.

Linux, Unix, and macOS
----------------------

OpenADMS can be started with an installed Python 3.6 interpreter
(:numref:`openadms-freebsd`):

::

    $ python openadms.py --config config/config.json --with-mqtt-broker

Depending on the used operating system, the name of the Python binary may be
``python36`` or ``python3.6``. On Unix-like operating systems, ``openadms.py``
can be executed directly once the proper permissions are set:

::

    $ chmod ug+x openadms.py
    $ ./openadms.py --config config/config.json --with-mqtt-broker

A running instance of OpenADMS can be restarted by sending a HUP signal:

::

    $ kill -s HUP $PID

``$PID`` is the process ID of the Python interpreter running OpenADMS Node.
The configuration will be re-read from file.

Press ``^C`` (``CTRL`` + ``C``) to stop OpenADMS Node.

.. _openadms-freebsd:
.. figure:: _static/openadms_urxvt.png
   :alt: Running OpenADMS on FreeBSD
   :align: center

   Running OpenADMS on FreeBSD

Additional Parameters
---------------------

OpenADMS Node can be started with parameters, for instance:

::

    $ python3 openadms.py -c config/config.json -m -d

The following parameters will be accepted:

+------------------------+------------+--------------------------+---------------------------+
| Parameter              | Short form | Default value            | Description               |
+========================+============+==========================+===========================+
| ``--config``           | ``-c``     | ``config/config.json``   | Path to the configuration |
|                        |            |                          | file.                     |
+------------------------+------------+--------------------------+---------------------------+
| ``--debug``            | ``-d``     | off                      | Print debug messages.     |
+------------------------+------------+--------------------------+---------------------------+
| ``--verbosity``        | ``-v``     | ``6`` (info)             | Log more diagnostic       |
|                        |            |                          | messages (level 1 to 9).  |
+------------------------+------------+--------------------------+---------------------------+
| ``--log-file``         | ``-l``     | ``openadms.log``         | Path to the log file.     |
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
