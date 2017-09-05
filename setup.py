#!/usr/bin/env python3

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
    Executable('openadmsw.pyw', base=base)
]

setup(name='OpenADMS',
      version='0.5',
      description='OpenADMS',
      options={
          'build_exe': build_exe_options
      },
      executables=executables)
