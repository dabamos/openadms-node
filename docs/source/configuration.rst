Configuration
=============

The monitoring system OpenADMS Node is configured by a single configuration file
in JavaScript Object Notation (JSON). The file is loaded once at the start of
OpenADMS Node. The path to the configuration file is passed as a command-line
argument. Example configuration files are located in directory
``config/examples/``. At the moment, configuration files have to be written
manually. This will change in future, once a visual configuration tool is
available.

The configuration consists of several sections. The order of the sections is
arbitrary, but it is recommended to start with the core settings (``core``),
followed by the used sensors with their commands listed under ``sensors``. See
directory ``sensors/`` for sensor configuration files. The configuration of
the dynamically loaded modules must be placed under ``modules``.

.. code:: javascript

    {
      "core": {
        "modules": {
          "myModule": "modules.example.MyModule"
        },
        "project": {
          "name": "Example Project",
          "id": "4a2e8b9d87d849e38bb6911b9f2364ea",
          "description": "Project for testing only."
        },
        "node": {
          "name": "Sensor Node 1",
          "id": "6426bf58c20840768912f116740c4974",
          "description": "The only sensor node in this project."
        },
        "intercom": {
          "mqtt": {
            "host": "127.0.0.1",
            "port": 8883,
            "keepAlive": 60,
            "topic": "openadms",
            "user": "client1".
            "password": "secret",
            "tls": false,
            "caCerts": "mqtt_ca.crt"
          }
        }
      },
      "sensors": {
        "mySensor": {
          "description": "My Example Sensor",
          "type": "generic",
          "observations": [
            {
              "name": "doMeasure",
              "description": "Does a measurement.",
              "target": "point1",
              "enabled": true,
              "onetime": false,
              "receivers": [ "preProcessor" ],
              "nextReceiver": 0,
              "requestSets": {
                "doMeasure": {
                  "enabled": true,
                  "request": "m\r",
                  "responsePattern": "(?P<x>[+-]?\\d+\\.+\\d)",
                  "responseDelimiter": "\r",
                  "sleepTime": 1.0,
                  "timeout": 1.0
                }
              },
              "requestsOrder": [ "doMeasure" ],
              "responseSets": {
                "x": {
                  "type": "float",
                  "unit": "m"
                }
              },
                "sleepTime": 5.0
            }
          ]
        }
      },
      "modules": {
        "myModule": {
          "enabled": true
        }
      }
    }

+-------------+--------+----------------------------------------------------+
| **core**    | Object | Core configuration.                                |
+-------------+--------+----------------------------------------------------+
| modules     | Object | List of OpenADMS Node modules to load.             |
+-------------+--------+----------------------------------------------------+
| project     | Object | Project information.                               |
+-------------+--------+----------------------------------------------------+
| node        | Object | Sensor node information.                           |
+-------------+--------+----------------------------------------------------+
| intercom    | Object | MQTT configuration for inter-module communication. |
+-------------+--------+----------------------------------------------------+
| **sensors** | Object | Sensors and their commands.                        |
+-------------+--------+----------------------------------------------------+
| **modules** | Object | Configuration of loaded modules.                   |
+-------------+--------+----------------------------------------------------+

Example
-------
Geodetic inclinometers are not only used in industrial surveying but also in
deformation monitoring. This tutorial explains how the OpenADMS monitoring
system has to be configured in order to be used with a Leica Nivel210
inclinometer. More sensors can be added easily. This setup works on all
operating systems (Microsoft Windows, Linux, Unix).

The example requires a Leica Nivel210 inclinometer with data cable and
power supply unit, as well as a computer with an RS-232 port or USB serial
adapter.

Create an empty configuration file under ``config/nivel210.json`` and copy the
following JSON structure into it:

.. code:: javascript

    {
      "core": {
        "modules": {},
        "project": {},
        "node": {},
        "intercom": {}
      },
      "sensors": {},
      "modules": {}
    }

After that, fill the JSON objects with the actual configuration.

Loading the Modules
~~~~~~~~~~~~~~~~~~~
Modules used for the monitoring job have to be added to the modules object in
the ``core`` section of the configuration file. The control of a Leica
Nivel210 sensor requires at least four modules:

- *Scheduler* for starting the observation,
- *SerialPort* for sensor communication,
- *PreProcessor* for sensor data extraction,
- *FileExporter* to save the sensor data to a CSV file.

The name of each module instance can be chosen freely (spaces and special
characters are not allowed). It is recommended to write all names in lower camel
case. As a sane practice, the scheduler and the serial port are named according
to the used COM port (for example, ``COM1`` on Microsoft Windows and ``ttyU0``
on Linux/Unix). All modules listed in the modules object are loaded
automatically at run-time:

.. code:: javascript

    {
      "core": {
        "modules": {
          "schedulerCom1": "module.schedule.Scheduler",
          "com1": "module.port.SerialPort",
          "preProcessor": "module.processing.PreProcessor",
          "fileExporter": "module.export.FileExporter"
        }
      }
    }

Project Details
~~~~~~~~~~~~~~~
Some meta information about the monitoring project must be defined in the
``project`` section of the core configuration. Use a hex-only UUID4 as the
project id.

.. code:: javascript

    {
      "core": {
        "project": {
          "name": "Example Project",
          "id": "19481e0791604b489a8a9c4a25e9dd80",
          "description": "Project for testing the Leica Nivel210."
        }
      }
    }

Sensor Node Details
~~~~~~~~~~~~~~~~~~~
Each monitoring project consists of one or more sensor nodes. It is required to
set a node name, a node id, and a node description. Use a hex-only UUID4 as the
node id.

.. code:: javascript

    {
      "core": {
        "node": {
          "name": "Sensor Node 1",
          "id": "21bcf8c16a664b17bbc9cd4221fd8541",
          "description": "The only sensor node in this project."
        }
      }
    }

Communication
~~~~~~~~~~~~~
The modules communicate by using the MQTT messaging protocol. For this reason,
an MQTT message broker is required. Either run OpenADMS with the parameter
``--with-mqtt-broker`` or start an external one. The default configuration uses
the IP address ``127.0.0.1`` and the port ``1883``, but can be altered to the
values set for the used MQTT message broker.

.. code:: javascript

    {
      "core": {
        "intercom": {
          "mqtt": {
            "host": "127.0.0.1",
            "port": 8883,
            "keepAlive": 60,
            "topic": "example",
            "user": "client1",
            "password": "secret",
            "tls": false,
            "caCerts": "mqtt_ca.crt"
          }
        }
      }
    }

User and password are optional and not required for anonymous sessions. If TLS
encryption is enabled by setting ``tls`` to ``true``, a CA certificate has to be
provided most likely.  ``caCerts`` is the path to the CA certificate of the MQTT
server.

Sensor
~~~~~~
Add the sensor details and used commands to the configuration file:

.. code:: javascript

    {
      "sensors": {
        "nivel210": {
          "description": "Leica Nivel210",
          "type": "inclinometer",
          "observations": [
            {
              "name": "getValues",
              "description": "gets inclination and temperature",
              "receivers": [
                "preProcessor",
                "fileExporter"
              ],
              "nextReceiver":0,
              "enabled": true,
              "onetime": false,
              "target": "nivel210",
              "requestsOrder": [
                "getXYTemp"
              ],
              "requestSets": {
                "getXYTemp": {
                  "enabled": true,
                  "request": "\\x16\\x02N0C0 G A\\x03\\x0d\\x0a",
                  "response": "",
                  "responseDelimiter": "\\x03",
                  "responsePattern": "X:(?P[-+]?[0-9]*\\.?[0-9]+) Y:(?P[-+]?[0-9]*\\.?[0-9]+) T:(?P[-+]?[0-9]*\\.?[0-9]+)",
                  "sleepTime":0.0,
                  "timeout":1.0
                }
              },
              "responseSets": {
                "temperature": {
                  "type": "float",
                  "unit": "C"
                },
                "x": {
                  "type": "float",
                  "unit": "mrad"
                },
                "y": {
                  "type": "float",
                  "unit": "mrad"
                }
              },
              "sleepTime":0.30
            }
          ]
        }
      }
    }

Serial Port
~~~~~~~~~~~
The configuration of serial port modules is stored under ``ports`` → ``serial``
→ *module name*. On Microsoft Windows, the port is ``COMx``, on Linux and Unix
``/dev/ttyx`` or ``/dev/ttyUx``, whereas ``x`` is the number of the port. The
baud rate has to be set to the value the Nivel210 is configured to, most likely
``9600``.

.. code:: javascript

    {
      "modules": {
        "ports": {
          "serial": {
            "com1": {
              "port": "COM1",
              "baudRate": 9600,
              "byteSize": 8,
              "stopBits": 1,
              "parity": "none",
              "timeout": 2.0,
              "softwareFlowControl": false,
              "hardwareFlowControl": false,
              "maxAttepts": 1
            }
          }
        }
      }
    }

Scheduler
~~~~~~~~~
Use a scheduler module to send commands to the sensor:

.. code:: javascript

    {
      "modules": {
        "schedulers": {
          "schedulerCom1": {
            "port": "com1",
            "sensor": "nivel210",
            "schedules": [
              {
                "enabled": true,
                "startDate": "2017-01-01",
                "endDate": "2020-12-31",
                "weekdays": {},
                "observations": [
                  "getValues"
                ]
              }
            ]
          }
        }
      }
    }

Set ``port`` to the name of the serial port configuration name and ``sensor`` to
the name of the sensor configuration. Multiple schedules can be defined.
Commands to send to the sensor must be listed in ``observations`` in their
correct order. Only listed observations will be performed.

Pre-Processor
~~~~~~~~~~~~~
The PreProcessor is called right after the SerialPort module and extracts the
values (temperature, inclination in X and Y) from the raw response of the
Nivel210. The response pattern of the request set ``getXYTemp`` is used for the
extraction.

File Exporter
~~~~~~~~~~~~~
The name of the CSV file may be ``com1_nivel210_2019-05.csv`` or similar and be
stored in directory ``data/``.

.. code:: javascript

    {
      "modules": {
        "fileExporter": {
          "fileExtension": ".csv",
          "fileName": "{{port}}_{{id}}_{{date}}",
          "fileRotation": "monthly",
          "paths": [
            "./data"
          ],
          "separator": ",",
          "dateTimeFormat": "YYYY-MM-DDTHH:mm:ss.SSSSS"
        }
      }
    }

Complete Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The complete configuration is listed below.

.. code:: javascript

    {
      "core": {
        "modules": {
          "schedulerCom1": "modules.schedule.Scheduler",
          "com1": "modules.port.SerialPort",
          "preProcessor": "modules.processing.PreProcessor",
          "fileExporter": "modules.export.FileExporter"
        },
        "project": {
          "name": "Example Project",
          "id": "19481e0791604b489a8a9c4a25e9dd80",
          "description": "Project for testing the Leica Nivel210."
        },
        "node": {
          "name": "Sensor Node 1",
          "id": "21bcf8c16a664b17bbc9cd4221fd8541",
          "description": "The only sensor node in this project."
        },
        "intercom": {
          "mqtt": {
            "host": "127.0.0.1",
            "port": 1883,
            "keepAlive": 60,
            "topic": "example",
            "user": "client1".
            "password": "secret",
            "tls": false,
            "caCerts": "mqtt_ca.crt"
          }
        }
      },
      "sensors": {
        "nivel210": {
          "description": "Leica Nivel210",
          "type": "inclinometer",
          "observations": [
            {
              "name": "getValues",
              "description": "gets inclination and temperature",
              "receivers": [
                "preProcessor",
                "fileExporter"
              ],
              "nextReceiver": 0,
              "enabled": true,
              "onetime": false,
              "target": "nivel210",
              "requestsOrder": [
                "getXYTemp"
              ],
              "requestSets": {
                "getXYTemp": {
                  "enabled": true,
                  "request": "\\x16\\x02N0C0 G A\\x03\\x0d\\x0a",
                  "response": "",
                  "responseDelimiter": "\\x03",
                  "responsePattern": "X:(?P[-+]?[0-9]*\\.?[0-9]+) Y:(?P[-+]?[0-9]*\\.?[0-9]+) T:(?P[-+]?[0-9]*\\.?[0-9]+)",
                  "sleepTime": 0.0,
                  "timeout": 1.0
                }
              },
              "responseSets": {
                "temperature": {
                  "type": "float",
                  "unit": "C"
                },
                "x": {
                  "type": "float",
                  "unit": "mrad"
                },
                "y": {
                  "type": "float",
                  "unit": "mrad"
                }
              },
              "sleepTime": 0.30
            }
          ]
        }
      },
      "modules": {
        "ports": {
          "serial": {
            "com1": {
              "port": "COM1",
              "baudRate": 9600,
              "byteSize": 8,
              "stopBits": 1,
              "parity": "none",
              "timeout": 2.0,
              "softwareFlowControl": false,
              "hardwareFlowControl": false,
              "maxAttepts": 1
            }
          }
        },
        "schedulers": {
          "schedulerCom1": {
            "port": "com1",
            "sensor": "nivel210",
            "schedules": [
              {
                "enabled": true,
                "startDate": "2017-01-01",
                "endDate": "2020-12-31",
                "weekdays": {

                },
                "observations": [
                  "getValues"
                ]
              }
            ]
          }
        },
        "fileExporter": {
          "fileExtension": ".csv",
          "fileName": "{{port}}_{{id}}_{{date}}",
          "fileRotation": "monthly",
          "paths": [
            "./data"
          ],
          "separator": ",",
          "dateTimeFormat": "YYYY-MM-DDTHH:mm:ss.SSSSS"
        }
      }
    }

Running OpenADMS
~~~~~~~~~~~~~~~~
To start the monitoring, change to the OpenADMS directory and run the
following command from the command-line:

::

    $ pipenv run ./openadms-node.py --config config/nivel210.json --with-mqtt-broker --debug
