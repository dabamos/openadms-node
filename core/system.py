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

import platform
import socket

import arrow
import uptime
#import psutil

from pathlib import Path

from core.version import *


class System(object):
    """
    System is a helper class to retrieve information about the used platform and
    system resources.
    """

#    @staticmethod
#    def get_cpu_load():
#        """Returns the current CPU load in percent. Please note, that calling
#        this method is blocking.
#
#        Returns:
#            Float with the CPU load (between 0.0 and 100.0).
#        """
#        return psutil.cpu_percent(interval=0.1)

    @staticmethod
    def get_current_year() -> int:
        """Returns the current year.

        Returns:
            Current year.
        """
        return arrow.now().year

    @staticmethod
    def get_date_time() -> str:
        """Returns local date and time.

        Returns:
            String containing date and time.
        """
        return arrow.now().format()

    @staticmethod
    def get_host_name() -> str:
        """Returns the host name of the system.

        Returns:
            String containing the host name.
        """
        return socket.gethostname()

    @staticmethod
    def get_machine() -> str:
        """Returns the hardware architecture.

        Returns:
            String with the hardware architecture.
        """
        return platform.machine()

    @staticmethod
    def get_openadms_string() -> str:
        """Returns a string with OpenADMS version and version name:

        Returns:
            Complete OpenADMS version string.
        """
        return 'OpenADMS {} ({})'.format(OPENADMS_VERSION,
                                         OPENADMS_VERSION_NAME)

    @staticmethod
    def get_openadms_version() -> float:
        """Returns the current version of OpenADMS:

        Returns:
            Version number.
        """
        return OPENADMS_VERSION

    @staticmethod
    def get_openadms_version_name() -> str:
        """Returns the code name of the current OpenADMS version.

        Returns:
            String with the version name.
        """
        return OPENADMS_VERSION_NAME

    @staticmethod
    def get_os_name() -> str:
        """Returns the name of the operating system.

        Returns:
            String with the OS name.
        """
        return platform.system()

    @staticmethod
    def get_os_version() -> str:
        """Returns the version of the operating system.

        Returns:
            Release number of the OS.
        """
        return platform.release()

    @staticmethod
    def get_python_version() -> str:
        """Returns Python implementation and version (e.g., 'CPython 3.5.1').

        Returns:
            String with name and version number.
        """
        return '{} {}'.format(platform.python_implementation(),
                              platform.python_version())

    @staticmethod
    def get_root_dir() -> Path:
        """Returns the root directory of OpenADMS.

        Returns:
            Path object.
        """
        return Path(__file__).parent.parent

    @staticmethod
    def get_system_string() -> str:
        """Returns a string containing operating system and hardware
        architecture (e.g., 'Windows 7 (AMD64)').

        Returns:
            String with OS name and architecture.
        """
        s = '{} {} ({})'.format(System.get_os_name(),
                                System.get_os_version(),
                                System.get_machine())
        return s

    @staticmethod
    def get_uptime() -> float:
        """Returns the system uptime in seconds.

        Returns:
            Uptime in seconds.
        """
        return uptime.uptime()

    @staticmethod
    def get_uptime_string() -> str:
        """Returns the system uptime as a formatted string (days, hours,
        minutes, seconds).

        Returns:
            String with the uptime.
        """
        u = '{:d}d {:d}h {:d}m {:d}s'

        if not System.get_uptime():
            # Doesn't work with PyPy3.5 v5.7.1 and below.
            return u.format(0, 0, 0, 0)

        t = int(System.get_uptime())
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        return u.format(d, h, m, s)

#    @staticmethod
#    def get_used_memory():
#        """Returns the currently used memory in percent.
#
#        Returns:
#            Memory currently in use (between 0.0 and 100.0).
#        """
#        return psutil.virtual_memory().percent

    @staticmethod
    def is_windows() -> bool:
        """Returns whether the current operating system is a version of
        Microsoft Windows or not.

        Returns:
            True if Windows, false if not.
        """
        if System.get_os_name() == 'Windows':
            return True
        else:
            return False
