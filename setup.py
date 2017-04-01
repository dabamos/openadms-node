from distutils.core import setup
import py2exe

setup(console=['launcher.py'],
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
