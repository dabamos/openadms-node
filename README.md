![OpenADMS](https://www.dabamos.de/github/openadms.png)

OpenADMS is an open source automatic deformation monitoring system for
geodetical and geotechnical observations in the Internet of Things.  The
software obtaines the measured data of arbitrary sensors, like total stations,
digital levels, inclinometers, weather stations, or GNSS receivers. The raw
sensor data is then processed, analysed, stored, and transmitted. OpenADMS
can be used to observe objects like:

* bridges, tunnels, dams;
* landslides, cliffs, glaciers;
* construction sites, mining areas;
* churches, monasteries, and other historic buildings.

The software is written in Python 3 and has been tested on:

* Microsoft Windows 7 (x86, x86-64)
* Debian 9, Raspbian Jessie (ARMv7)
* Fedora 25 (x86-64)
* FreeBSD 11 (x86-64, ARMv7)
* NetBSD 7 (ARMv7)

OpenADMS can either be used with CPython 3.6 or PyPy3.5.

The current development version of OpenADMS is 0.6 (code name “Fukuyama”). For
more information, please see https://www.dabamos.de/.

## Installation
Before you can start OpenADMS, you have to clone the master branch and install
all dependencies:
```
$ git clone https://github.com/dabamos/openadms.git
$ cd openadms
$ python3 -m pip install -U -r requirements.txt
```
Run OpenADMS from the command line:
```
$ python3 openadms.py --config ./config/my_config.json --with-mqtt-broker --debug
```
OpenADMS also features a graphical launcher. At first, run `win_install.bat` on
Microsoft Windows or install the dependencies manually:
```
$ python3 -m pip install Gooey
```
Execute `openadms-launcher.pyw` to start the graphical launcher.

### Dependencies
OpenADMS depends on the following Python libraries:

* [arrow](https://pypi.python.org/pypi/arrow) (Apache 2.0 Licence)
* [coloredlogs](https://pypi.python.org/pypi/coloredlogs) (MIT Licence)
* [hbmqtt](https://pypi.python.org/pypi/hbmqtt) (MIT Licence)
* [jsonschema](https://pypi.python.org/pypi/jsonschema) (MIT Licence)
* [paho-mqtt](https://pypi.python.org/pypi/paho-mqtt) (Eclipse Public Licence)
* [pyserial](https://pypi.python.org/pypi/pyserial) (Python Software Foundation Licence)
* [uptime](https://pypi.python.org/pypi/uptime) (BSD-2-Clause Licence)

The graphical launcher uses [Gooey](https://pypi.python.org/pypi/Gooey) (MIT
Licence).

## Message Broker
The MQTT protocol is used for the message exchange in OpenADMS. You can either
use an external MQTT message broker, like
[Eclipse Mosquitto](https://mosquitto.org/), or start the internal one by using
the parameter `--with-mqtt-broker`.

For testing only, the public sandbox broker of
[Eclipse IoT](https://iot.eclipse.org/getting-started) can be used. The server
supports MQTT and WebSockets, both plain and TLS secured. Access the server
using the hostname `iot.eclipse.org` and port `1883`. For encryption, use port
`8883`. MQTT over WebSockets runs on the ports `80` and `443`.

## Configuration
The configuration of OpenADMS is done by using a JSON-based text file, located
in the directory `./config`. Please define modules, serial ports, sensors, and
so on there. OpenADMS takes the file name of your custom configuration as an
argument. For instance, run:
```
$ python3 openadms.py --config ./config/myconfig.json --with-mqtt-broker --debug
```

## Virtual Environment
The Python tool `venv` can create a virtual Python environment for development
(with `csh`/`tcsh` on Unix):
```
$ python3 -m venv virtual-environment
$ source ./virtual-environment/bin/activate.csh
$ git clone https://github.com/dabamos/openadms
$ cd openadms
$ python3 -m pip install -U -r requirements.txt
$ python3 openadms.py --config ./config/myconfig.json --with-mqtt-broker --debug
```

## Manual
The [on-line manual](https://www.dabamos.de/manual/index.html) is available on
the project website.

## Licence
OpenADMS is licenced under the [European Union Public
Licence](https://joinup.ec.europa.eu/community/eupl/og_page/eupl) (EUPL) v1.1.
