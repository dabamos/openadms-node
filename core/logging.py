#!/usr/bin/env python3.6
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
from typing import *


class RootFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        """Returns whether a logging.LogRecord should be logged."""
        if record.name.startswith(('asyncio', 'hbmqtt', 'passlib', 'urllib3')):
            return False
        else:
            return True


class RingBuffer(object):
    """
    RingBuffer stores elements in a deque. It is a FIFO list with fixed size to
    cache a number of elements, like log messages. The oldest elements get
    removed when the number of elements is greater than the maximum length.
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


class StringFormatter(logging.Formatter):
    """
    StringFormatter simply returns a formatted string of a log record.
    """

    def __init__(self):
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Return formatted string of log record.

        Args:
            record: The log record.

        Returns:
            Formatted string of log record.
        """
        if record.args and 'asctime' not in record.args:
            record.asctime = self.formatTime(record, self.datefmt)

        if record.args and 'message' not in record.args:
            record.message = record.msg

        s = '{} - {:>8} - {:>26} - {}'.format(record.asctime,
                                              record.levelname,
                                              record.name,
                                              record.message)

        return s


class RingBufferLogHandler(logging.Handler):
    """
    RingBufferLogHandler stores a number of log messages in a `RingBuffer`.
    """

    def __init__(self,  level: int, size: int):
        """
        Args:
            level: The log level.
            size: The size of the `RingBuffer`.
        """
        super().__init__(level)

        self._size = size
        self._buffer = RingBuffer(self._size)

    def emit(self, record: logging.LogRecord) -> None:
        """Adds a log record to the internal ring buffer.

        Args:
            record: The log record.
        """
        log_entry = self.format(record)
        self._buffer.append(log_entry)

    def get_logs(self) -> str:
        return self._buffer.to_string()

    @property
    def size(self) -> int:
        return self._size
