#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg.

Licenced under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    https://joinup.ec.europa.eu/community/eupl/og_page/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import logging

from collections import deque
from queue import Queue
from threading import Thread
from typing import *


class RootFilter(logging.Filter):

    def filter(self, record: Type[logging.LogRecord]) -> bool:
        """Returns whether a logging.LogRecord should be logged."""
        if record.name.startswith(('asyncio', 'hbmqtt', 'passlib')):
            return False
        else:
            return True


class RingBuffer(object):
    """
    RingBuffer stores elements in a deque. It is used to cache a number of
    elements, while older ones get overwritten automatically.
    """

    def __init__(self, max_length: int):
        """
        Args:
            max_length: The maximum size of the deque.
        """
        self._deque = deque(maxlen=max_length)

    def append(self, x: Any) -> None:
        """Appends an element to the deque.

        Args:
            x: Element to append.
        """
        self._deque.append(x)

    def pop(self) -> Any:
        """Pops an element.

        Returns:
            String on the left side of the deque.
        """
        return self._deque.popleft()

    def get(self) -> List[Any]:
        """Returns a list with all elements.

        Returns:
            List with all elements in the deque.
        """
        return list(self._deque)

    def to_string(self) -> str:
        """Returns the whole deque as a string.

        Returns:
            String containing all string elements in the deque.
        """
        return '\n'.join(self.get())


class RingBufferLogHandler(object):
    """
    RingBufferLogHandler stores log messages in a `RingBuffer` with a fixed
    length.
    """

    def __init__(self, size: int, log_level: int):
        self._size = size
        self._buffer = RingBuffer(self._size)
        self._queue = Queue(self._size)

        self._handler = logging.handlers.QueueHandler(self._queue)

        # Add logging filter.
        self._handler.addFilter(RootFilter())

        level = {
            1: logging.CRITICAL,
            2: logging.ERROR,
            3: logging.WARNING,
            4: logging.INFO,
            5: logging.DEBUG
        }.get(log_level, 4)

        self._handler.setLevel(level)

        fmt = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        formatter = logging.Formatter(fmt)
        self._handler.setFormatter(formatter)

        root = logging.getLogger()
        root.addHandler(self._handler)

        self._is_running = True
        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

    def __del__(self):
        self._is_running = False

    def run(self) -> None:
        while self._is_running:
            log_record = self._queue.get()  # Blocking I/O.
            s = '{} - {:>8} - {:>26} - {}'.format(log_record.asctime,
                                                  log_record.levelname,
                                                  log_record.name,
                                                  log_record.message)
            self._buffer.append(s)

    def get_logs(self) -> str:
        return self._buffer.to_string()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def size(self) -> int:
        return self._size
