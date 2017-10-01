#!/usr/bin/env python3.6

"""Setup for cx_Freeze

This script creates executables for Microsoft Windows by using cx_Freeze.
Just run

    $ python setup.py build

or start the batch file `win_make_cx_freeze.bat`. All files are stored in the
sub-folder `dist`. For more information, please see https://www.dabamos.de/.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import sys

from cx_Freeze import setup, Executable

from core import version


build_exe_options = {
    'build_exe': 'dist',
    'packages': ['asyncio',
                 'appdirs',
                 'packaging',
                 'module.database',
                 'module.export',
                 'module.notification',
                 'module.port',
                 'module.processing',
                 'module.prototype',
                 'module.schedule',
                 'module.server',
                 'module.testing',
                 'module.totalstation',
                 'module.virtual'],
    'excludes': ['tkinter'],
    'include_files': [
        'config',
        'data',
        'extra',
        'module',
        'schema',
        'sensor',
        'res'
    ],
    'silent': True
}

base = None

if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('openadms.py', base=base),
    Executable('openadms-launcher.pyw', base=base)
]

setup(name='OpenADMS Node',
      version=OPENADMS_VERSION,
      description='OpenADMS Node',
      options={
          'build_exe': build_exe_options
      },
      executables=executables)

