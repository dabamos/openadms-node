#!/usr/bin/env python3.6

"""The modules class to bundle an OpenADMS Node worker with a messenger."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import logging
import queue
import threading

from typing import *

from core.intercom import MQTTMessenger
from modules.prototype import Prototype


class Module(threading.Thread):
    """
    Module bundles a worker with a messenger and manages the communication
    between them.
    """

    def __init__(self,
                 messenger: MQTTMessenger,
                 worker: Prototype):
        """
        Args:
            messenger: The messenger object.
            worker: The worker object.
        """
        super().__init__(name=worker.name)

        self.logger = logging.getLogger(worker.name)
        self.daemon = True

        self._messenger = messenger                 # MQTT messenger.
        self._worker = worker                       # Worker instance.

        self._inbox = queue.Queue()                 # Message inbox.
        self._topic = self._messenger.topic         # MQTT topic to listen to.

        # Set the callback functions of the messenger and the worker.
        self._messenger.downlink = self.retrieve    # Call on new messages.
        self._worker.uplink = self.publish          # Call to publish message.

        # Subscribe to topic of worker's name.
        self._messenger.subscribe(self._topic + '/' + worker.name)

    def publish(self, target: str, message: str) -> None:
        """Sends an `Observation` object to the next receiver by using the
        messenger.

        Args:
            target: Name of the topic.
            message: Message in JSON format.
        """
        target_path = '{}/{}'.format(self._topic, target)
        self._messenger.publish(target_path, message)

    def retrieve(self, message: List[Dict]) -> None:
        """Callback function for the messenger. New data from the message broker
        lands here.

        Args:
            message: Header and payload of the message, both Dict.
        """
        self._inbox.put(message)

    def run(self) -> None:
        """Checks the inbox for new messages and calls the `handle()` method of
        the worker for further processing. Runs within a thread."""
        self.logger.verbose('Connecting modules "{}" to {}:{}'
                            .format(self._worker.name,
                                    self._messenger.host,
                                    self._messenger.port))
        self._messenger.connect()

        while True:
            message = self._inbox.get()   # Blocking I/O.
            self._worker.handle(message)  # Fire and forget.

        self._messenger.disconnect()

    def start_worker(self) -> None:
        self._worker.start()

    def stop_worker(self) -> None:
        self._worker.stop()

    @property
    def messenger(self) -> MQTTMessenger:
        return self._messenger

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def worker(self) -> Prototype:
        return self._worker

    @messenger.setter
    def messenger(self, messenger: MQTTMessenger) -> None:
        self._messenger = messenger

    @worker.setter
    def worker(self, worker: Prototype) -> None:
        self._worker = worker

