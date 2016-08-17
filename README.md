![OpenADMS](http://www.dabamos.de/github/openadms.png)

OpenADMS is an open source automatic deformation monitoring system for
geodetical and geotechnical surveillance measurements. The software is written
in Python 3 and should run on Python 3.3 upwards. So far, it has been tested
with CPython under FreeBSD 10 (x86-64), NetBSD 7 (ARMv7), and Windows 7 (x86).
For more information, please see http://www.dabamos.de/.

## Installation
To run OpenADMS, clone the branch and execute `openadms.py`:

```
$ git clone https://github.com/dabamos/openadms.git
$ cd openadms
$ python3 openadms.py
```

### Libraries
Some additional modules have to be installed in order to use OpenADMS:

* [coloredlogs](https://pypi.python.org/pypi/coloredlogs) (MIT License)
* [paho-mqtt](https://pypi.python.org/pypi/paho-mqtt) (Eclipse Public License)
* [pyserial](https://pypi.python.org/pypi/pyserial) (Python Software Foundation Licence)

The installation can be done with `pip`:

```
$ python3 -m pip install coloredlogs paho-mqtt pyserial
```
## Message Broker
The MQTT protocol is used for the internal message exchange in OpenADMS. An MQTT
message broker, like [Eclipse Mosquitto](http://mosquitto.org/), must be
installed and running before starting OpenADMS. On Unix-like operating systems
an installed Mosquitto MQTT message broker can be launched with:

```
# service mosquitto onestart
```

## Configuration
The configuration of OpenADMS is done by using a JSON-based text file, located
in the directory `./config`. Please define serial ports, sensors, and connections
between them there. OpenADMS takes the file name of the configuration as an
argument. Run:

```
$ python3 openadms.py --config ./config/my_config.json
```

## Virtual Environment
For the set-up of an independent Python environment the tool `pyvenv` can be
used, which is part of Python 3:

```
$ pyvenv-3.5 ~/virtual-environment
$ bash
$ source ~/virtual-environment/bin/activate
$ python3 -m pip install coloredlogs paho-mqtt pyserial
$ cd ~/virtual-environment
$ git clone https://github.com/dabamos/openadms
$ cd openadms
$ python3 openadms.py
```

## Licence
OpenADMS is licenced under the [European Union Public
Licence](https://joinup.ec.europa.eu/community/eupl/og_page/eupl) (EUPL) v1.1.

