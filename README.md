![license](https://img.shields.io/github/license/dabamos/openadms.svg)
![release](https://img.shields.io/github/release/dabamos/openadms-node.svg)
![ci](https://img.shields.io/travis/dabamos/openadms-node.svg)

![OpenADMS Node](https://www.dabamos.de/github/openadms.png)

The **Open Automatic Deformation Monitoring System** (OpenADMS) is a free and
open-source software for sensor control, observation data processing, and
spatial , and sensor data exchangedata storage in the Internet of Things (IoT).

The **OpenADMS Node** software runs on single sensor node instances in a sensor
network to obtain the measured data of total stations, digital levels,
inclinometers, weather stations, GNSS receivers, and other sensors.  The raw
data is then processed, analysed, stored, and transmitted. OpenADMS Node can be
used to observe objects like:

* bridges, tunnels, dams;
* landslides, cliffs, glaciers;
* construction sites, mining areas;
* churches, monasteries, and other historic buildings.

The software is written in Python 3.6 and has been tested on:

* Microsoft Windows 7 (x86, x86-64)
* Debian 9, Raspbian Jessie (ARMv7)
* Fedora 25 (x86-64)
* FreeBSD 11 (x86-64, ARMv7)
* NetBSD 7 (ARMv7)

OpenADMS Node can either be used with [CPython 3.6+](https://www.python.org/) or
[PyPy3.5](https://pypy.org/).

The current development version of OpenADMS Node is 0.8 (code name “Hanoi”).
For more information, see https://www.dabamos.de/.

## Installation
Either CPython 3.6+ or PyPy3.5 has to be installed. OpenADMS Node uses `pipenv`
for dependency management and virtual environments. Make sure that `pipenv` is
installed or run:
```
$ pip3 install --user pipenv
```
Download the [Zip archive](https://github.com/dabamos/openadms-node/archive/master.zip)
with the latest version of OpenADMS Node or clone the master branch with Git.
Then, create a virtual environment with `pipenv`:
```
$ git clone https://github.com/dabamos/openadms-node.git
$ cd openadms-node/
$ pipenv sync
```

## Run
Run OpenADMS Node from the command line:
```
$ pipenv run ./openadms.py --config ./config/config.json --with-mqtt-broker --debug
```
OpenADMS Node also features a graphical launcher. At first, run `install.bat` on
Microsoft Windows or install the dependencies manually:
```
$ pipenv install Gooey
```
Execute `pipenv run ./openadms-launcher.pyw` to start the graphical launcher.

## Message Broker
The MQTT protocol is used for the message exchange in OpenADMS Node. You can
either use an external MQTT message broker, like
[Eclipse Mosquitto](https://mosquitto.org/), or start the internal one by using
the parameter `--with-mqtt-broker`.

## Configuration
OpenADMS Node must be configured by a JSON-based text file. Please define
modules, serial ports, sensors, etc. in there. The file name of your custom
configuration is taken as an argument. For instance, run:
```
$ pipenv run ./openadms.py --config ./config/example.json
```

## Documentation and Supported Sensors
The documentation is hosted on the
[project website](https://www.dabamos.de/manual/openadms-node/).
See `./docs` for how to build the documentation from source.

For a list of tested sensors, see https://dabamos.de/sensors/.

## Running Tests
Development dependencies must be installed to run test:
```
$ pipenv install --dev
```
Execute the unit tests with:

```
$ pipenv shell
$ python3 -m pytest
$ exit
```
These are work in progress. You can run passive checks with
[pyflakes](https://pypi.python.org/pypi/pyflakes):
```
$ pipenv run pyflakes *.py *.pyw core/*.py modules/*.py
```

## Licence
OpenADMS is licenced under BSD (2-Clause).
