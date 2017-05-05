![OpenADMS](https://www.dabamos.de/github/openadms.png)

OpenADMS is an open source automatic deformation monitoring system for
geodetical and geotechnical observations. The software is written in Python 3
and should run on Python 3.5 upwards. So far, it has been tested with CPython
3.5/3.6 on:

* Windows 7 (x86, x86-64)
* FreeBSD 11 (x86-64, ARMv7)
* NetBSD 7 (ARMv7)
* Debian 9 (ARMv7)
* Fedora 25 (x86-64)

PyPy3.5 is currently not supported, due to incompatibilities with the `psutil`
module.

The current development version of OpenADMS is 0.5 (code name “Eindhoven”). For
more information, please see https://www.dabamos.de/.

## Installation
To run OpenADMS, clone the branch and execute `openadms.py`:

```
$ git clone https://github.com/dabamos/openadms.git
$ cd openadms
$ pip install -U -r requirements.txt
$ python3 openadms.py --config ./config/myconfig.json --debug
```

Some additional modules are used by OpenADMS:

* [coloredlogs](https://pypi.python.org/pypi/coloredlogs) (MIT Licence)
* [paho-mqtt](https://pypi.python.org/pypi/paho-mqtt) (Eclipse Public Licence)
* [psutil](https://pypi.python.org/pypi/psutil) (BSD-3-Clause)
* [pyserial](https://pypi.python.org/pypi/pyserial) (Python Software Foundation Licence)
* [uptime](https://pypi.python.org/pypi/uptime) (BSD-2-Clause)

On Linux, you need to install the development headers for Python 3 in order to
build the module `psutil`.

## Message Broker
The MQTT protocol is used for the internal and external message exchange in
OpenADMS. An MQTT message broker, like [Eclipse Mosquitto](https://mosquitto.org/)
or [HBMQTT](https://github.com/beerfactory/hbmqtt), must be installed and
running before starting OpenADMS.

For testing only, the public sandbox broker of
[Eclipse IoT](https://iot.eclipse.org/getting-started) can be used. The server
supports MQTT and WebSockets, both plain and TLS secured. Access the server
using the hostname `iot.eclipse.org` and port `1883`. For encryption, use port
`8883`. MQTT over WebSockets runs on the ports `80` and `443`.

## Configuration
The configuration of OpenADMS is done by using a JSON-based text file, located
in the directory `./config`. Please define modules, serial ports, sensors, and
so on there. OpenADMS takes the file name of your custom configuration as an
argument. Run:

```
$ python3 openadms.py --config ./config/myconfig.json --debug
```

## Virtual Environment
The Python tool `pyvenv` can be used to set-up a virtual environment for
development (with `csh`/`tcsh` on Unix):

```
$ python3 -m venv virtual-environment
$ source ./virtual-environment/bin/activate.csh
$ cd ./virtual-environment
$ git clone https://github.com/dabamos/openadms
$ cd openadms
$ python3 -m pip install -U -r requirements.txt
$ python3 openadms.py
```

## Licence
OpenADMS is licenced under the [European Union Public
Licence](https://joinup.ec.europa.eu/community/eupl/og_page/eupl) (EUPL) v1.1.

