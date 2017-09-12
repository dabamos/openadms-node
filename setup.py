#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg an other contributors.

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

"""Setup for cx_Freeze

This script creates executables for OpenADMS by using cx_Freeze. Just run:

    $ python setup.py

All files are stored in the sub-folder `dist`. For more information, please see
https://www.dabamos.de/.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import sys
from cx_Freeze import setup, Executable


build_exe_options = {
    'build_exe': 'dist',
    'packages': ['asyncio',
                 'appdirs',
                 'packaging',
                 'module.database',
                 'module.export',
                 'module.linux',
                 'module.notification',
                 'module.port',
                 'module.processing',
                 'module.prototype',
                 'module.schedule',
                 'module.server',
                 'module.totalstation',
                 'module.virtual'],
    'excludes': ['tkinter'],
    'include_files': ['config', 'data', 'module', 'schema', 'sensor', 'res'],
    'silent': True
}

base = None

if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('openadms.py', base=base),
    Executable('openadms-gui.pyw', base=base)
]

setup(name='OpenADMS',
      version='0.6',
      description='OpenADMS',
      options={
          'build_exe': build_exe_options
      },
      executables=executables)

