#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    http://ec.europa.eu/idabc/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger('openadms')


class MQTTMessenger(object):

    def __init__(self, host, port=1883, timeout=60):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._topic = '#'

        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def __del__(self):
        self.disconnect()

    def connect(self):
        self._client.connect_async(self._host, self._port, self._timeout)
        self._client.loop_start()

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        self._client.subscribe(self._topic)

    def _on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.error('Unexpected disconnection')

    def _on_message(self, client, userdata, msg):
        self._callback_func(str(msg.payload, encoding='UTF-8'))

    def publish(self, topic, message):
        self._client.publish(topic, message)

    def register(self, callback_func):
        self._callback_func = callback_func

    def subscribe(self, topic):
        self._topic = topic

    @property
    def client(self):
        return self._client
