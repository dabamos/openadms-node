#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg and other contributors.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
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

from distutils.core import setup
import py2exe

"""The setup file for py2exe. To create an executable, run:

    C:\Python34\python.exe setup.py py2exe

The distribution files are stored in the sub-folder "dist". You can run the
make file "make-py2exe.bat" to create a complete OpenADMS distribution for
Microsoft Windows."""
setup(console=['openadms.py'],
      options={'py2exe': {'includes': ['modules.database',
                                       'modules.export',
                                       'modules.gpio',
                                       'modules.notification',
                                       'modules.port',
                                       'modules.processing',
                                       'modules.processing',
                                       'modules.prototype',
                                       'modules.schedule',
                                       'modules.totalstation',
                                       'modules.virtual']}})
