![NetADMS](http://www.dabamos.de/github/netadms.png)

NetADMS is an open source automatic deformation monitoring system for geodetical
and geotechnical surveillance measurements. The software is written in Python 3
and should run on Python 3.3 upwards. So far, it has been tested under FreeBSD
10 (x86-64), NetBSD 7 (ARMv7), and Windows 7 (x86). For more information, please
see http://www.dabamos.de/.

## Installation
To run NetADMS, clone the branch and execute `netadms.py`:

```
$ git clone https://github.com/dabamos/netadms.git
$ cd netadms
$ python3 netadms.py
```

### Libraries
Some additional modules have to be installed in order to use NetADMS:

* [coloredlogs](https://pypi.python.org/pypi/coloredlogs) (MIT License)
* [pyserial](https://pypi.python.org/pypi/pyserial) (Python Software Foundation Licence)

The installation can be done with `pip`:

```
$ python3 -m pip install coloredlogs pyserial
```

## Configuration
The configuration of NetADMS is done using a JSON-based text file, located in
the directory `config`. Please define serial ports, sensors, and connections
between them there. NetADMS takes the file name of the configuration as a
parameter. Run:

```
$ python3 netadms.py --config ./config/my_config.json
```

### Virtual Environment
For the set-up of an independent Python environment the tool `pyvenv` can be
used, which is part of Python 3:

```
$ pyvenv-3.5 ~/virtual-environment
$ bash
$ source ~/virtual-environment/bin/activate
$ python3 -m pip install coloredlogs pyserial
$ cd ~/virtual-environment
$ git clone https://github.com/dabamos/netadms
$ cd netadms
$ python3 netadms.py
```

## Licence
NetADMS is licenced under the [European Union Public
Licence](https://joinup.ec.europa.eu/community/eupl/og_page/eupl) (EUPL) v1.1.

