![OpenADMS](http://www.dabamos.de/github/openadms.png)

OpenADMS is an open source automatic deformation monitoring system for
geodetical and geotechnical measurements. The software is written in Python 3
and should run on Python 3.5 upwards. So far, it has been tested with CPython on
FreeBSD 10 (x86-64), NetBSD 7 (ARMv7), and Windows 7 (x86).  For more
information, please see http://www.dabamos.de/.

The current development version of OpenADMS is 0.4 (code name “Dar es Salaam”).

## Installation
To run OpenADMS, clone the branch and execute `openadms.py`:

```
$ git clone https://github.com/dabamos/openadms.git
$ cd openadms
$ python3 openadms.py --config ./config/myconfig.json --debug
```

### Libraries
Some additional modules have to be installed in order to use OpenADMS:

* [coloredlogs](https://pypi.python.org/pypi/coloredlogs) (MIT Licence)
* [paho-mqtt](https://pypi.python.org/pypi/paho-mqtt) (Eclipse Public Licence)
* [pyserial](https://pypi.python.org/pypi/pyserial) (Python Software Foundation Licence)

The installation can be done with `pip`:

```
$ pip install -U -r requirements.txt
```
## Message Broker
The MQTT protocol is used for the internal message exchange in OpenADMS. An MQTT
message broker, like [Eclipse Mosquitto](http://mosquitto.org/), must be
installed and running before starting OpenADMS. On Unix-like operating systems
an installed Mosquitto MQTT message broker can be launched with:

```
# service mosquitto onestart
```

For testing only, the public sandbox broker of
[Eclipse IoT](http://iot.eclipse.org/getting-started) can be used. The server
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
For the set-up of an independent Python environment the tool `pyvenv` can be
used, which is part of Python 3:

```
$ pyvenv-3.5 ~/virtual-environment
$ bash
$ source ~/virtual-environment/bin/activate
$ cd ~/virtual-environment
$ git clone https://github.com/dabamos/openadms
$ cd openadms
$ pip install -r requirements.txt
$ python3 openadms.py
```

## Licence
OpenADMS is licenced under the [European Union Public
Licence](https://joinup.ec.europa.eu/community/eupl/og_page/eupl) (EUPL) v1.1.

