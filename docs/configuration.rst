Configuration
=============

The monitoring system OpenADMS Node is configured by a single configuration file
in JavaScript Object Notation (JSON). The file is loaded once at the start of
OpenADMS Node. The path to the configuration file is passed as a command-line
argument. Example configuration files are located in directory
``./config/example/``. At the moment, configuration files have to be written
manually. This will change in future, once a visual configuration tool will be
available.

The configuration consists of several sections. The order of the sections is
arbitrary, but it is recommended to start with a list of modules to be used for
the monitoring (``modules``), followed by meta information about the project
(``project``) and the sensor node (``node``). In the ``intercom`` section the
settings for the MQTT messaging protocol are defined. All used sensors with
their commands have to be listed under ``sensors``. See directory ``./sensors/``
for sensor configuration files.

.. code:: javascript

    {
      "modules": {
        "myModule": "modules.example.MyModule"
      },
      "project": {
        "name": "Example Project",
        "id": "4a2e8b9d87d849e38bb6911b9f2364ea",
        "description": "Project for testing virtual sensors."
      },
      "node": {
        "name": "Sensor Node 1",
        "id": "6426bf58c20840768912f116740c4974",
        "description": "The only sensor node in this project."
      },
      "intercom": {
        "mqtt": {
          "host": "127.0.0.1",
          "port": 1883,
          "keepAlive": 60,
          "topic": "openadms"
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
      }
    }
