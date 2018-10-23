#!/usr/bin/env python3.6

"""Methods for getting system information."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2018 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import platform
import socket

from pathlib import Path

import arrow
import uptime
#import psutil

from core.version import OPENADMS_VERSION, OPENADMS_VERSION_NAME


class System():
    """
    System is a helper class to retrieve information about the used platform and
    system resources.
    """

    start_time = arrow.now()

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
        """Returns a string with OpenADMS Node version and version name:

        Returns:
            Complete OpenADMS Node version string.
        """
        return f'OpenADMS Node {OPENADMS_VERSION} ({OPENADMS_VERSION_NAME})'

    @staticmethod
    def get_openadms_version() -> float:
        """Returns the current version of OpenADMS:

        Returns:
            Version number.
        """
        return OPENADMS_VERSION

    @staticmethod
    def get_openadms_version_name() -> str:
        """Returns the code name of the current OpenADMS Node version.

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
        return f'{platform.python_implementation()} {platform.python_version()}'

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
        return (f'{System.get_os_name()} {System.get_os_version()} '
                f'({System.get_machine()})')

    @staticmethod
    def get_system_uptime_string() -> str:
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

    @staticmethod
    def get_software_uptime_string() -> str:
        """Returns the software uptime as a formatted string (days, hours,
        minutes, seconds).

        Returns:
            String with the software uptime.
        """
        u = '{:d}d {:d}h {:d}m {:d}s'

        t = int((arrow.now() - System.start_time).total_seconds())
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        return u.format(d, h, m, s)

    @staticmethod
    def get_uptime() -> float:
        """Returns the system uptime in seconds.

        Returns:
            Uptime in seconds.
        """
        return uptime.uptime()

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
