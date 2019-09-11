System Description
==================

Observation Entity
------------------

Information regarding a single measurement of a sensor is stored in a JSON-based
observation entity. Whenever a request is made to a sensor, it must be embedded
into an observation entity along with meta information like name and target of
the observation, name of the serial port, regular expression pattern of the
sensor’s raw response, and so on.

All observations that will be send to a sensor are stored prior in a
configuration file in JSON format. OpenADMS Node reads the configuration file
and processes the observations according to their properties.

Observation entities can be enhanced by adding optional key-value pairs. But
most elements in an observation entity are mandatory. The following basic
object stores the finished observation ``getValues`` with two requests
``getTemperature`` and ``getPressure`` of the STS DTM meteorological sensor. The
observation was send to the modules ``com1``, ``preProcessor``, and
``fileExporter``.

.. code:: javascript

    {
      "name": "getValues",
      "type": "observation",
      "description": "get sensor values (temperature, pressure)",
      "sensorName": "stsDTM",
      "timestamp": "2017-04-05T21:48:00.805527",
      "target": "TempPress",
      "id": "6dc84c06018043ba84ac90636ed0f677",
      "pid": "6600055d61ce4d8698f77596e436785f",
      "nid": "21bcf8c16a664b17bbc9cd4221fd8541",
      "enabled": true,
      "onetime": false,
      "receivers": [
        "com1",
        "preProcessor",
        "fileExporter"
      ],
      "nextReceiver": 4,
      "portName": "COM1",
      "passiveMode": false,
      "requestsOrder": [
        "getTemperature",
        "getPressure"
      ],
      "requestSets": {
        "getTemperature": {
          "enabled": true,
          "request": "TEMP ?\r",
          "response": ">+23.1",
          "responseDelimiter": "\r",
          "responsePattern": "(?P<temperature>[+-]?\\d+\\.+\\d)",
          "sleepTime": 1.0,
          "timeout": 1.0
        },
        "getPressure": {
          "enabled": true,
          "request": "PRES ?\r",
          "response": ">+1011.3",
          "responseDelimiter": "\r",
          "responsePattern": "(?P<pressure>[+-]?\\d+\\.+\\d)",
          "sleepTime": 1.0,
          "timeout": 1.0
        }
      },
      "responseSets": {
        "temperature": {
          "type": "float",
          "unit": "C",
          "value": "23.1"
        },
        "pressure": {
          "type": "float",
          "unit": "mbar",
          "value": "1011.3"
        }
      },
      "sleepTime": 20.0
    }

The single elements of this observation entity are explained below.

+-------------------+-----------+-------------------------------------------------------------------------+
| Name              | Data Type | Description                                                             |
+===================+===========+=========================================================================+
| ``description``   | String    | Short description of the observation (optional).                        |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``enabled``       | Boolean   | Condition of the observation (enabled/disabled).                        |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``id``            | String    | ID of the observation (UUID4 hex only).                                 |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``name``          | String    | Name of the observation.                                                |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``nextReceiver``  | Integer   | Index of the next receiver (0 … n).                                     |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``nid``           | String    | Sensor node ID (UUID4 hex).                                             |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``onetime``       | Boolean   | If true, observation will be send one time only.                        |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``passiveMode``   | Boolean   | If true, serial port communication is passive only (depends on sensor). |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``portName``      | String    | Name of the serial port (will be added automatically).                  |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``pid``           | String    | Project ID (UUID4 hex).                                                 |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``receivers``     | Array     | Array of modules the observation will be send to sequentially.          |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``requestSets``   | Object    | Requests to the sensor, response patterns, etc.                         |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``requestsOrder`` | Array     | Defines the order of the requests.                                      |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``responseSets``  | Object    | Response units, types, and values.                                      |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``sensorName``    | String    | Name of the sensor (will be added by the scheduler).                    |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``sensorType``    | String    | Type of sensor (e.g., total station, GNSS receiver, …).                 |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``sleepTime``     | Float     | Time in seconds to wait before the next observation.                    |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``target``        | String    | Target name of the observation (e.g., point name, target location).     |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``timestamp``     | String    | Time stamp of the observation (UTC in ISO 8601).                        |
+-------------------+-----------+-------------------------------------------------------------------------+
| ``type``          | String    | Name of data type (always ``observation``).                             |
+-------------------+-----------+-------------------------------------------------------------------------+
