import logging


SETTINGS_TPL = """from os.path import abspath, dirname, join
from {basemodule} import *

basedir = abspath(dirname(__file__))
MEDIA_ROOT = join(basedir, "filestore")
DATABASES['default']['NAME'] = join(basedir, 'db.sqlite3')
DEVILRY_FSHIERDELIVERYSTORE_ROOT = join(basedir, 'deliverystorehier')
LOGGING = create_logging_conf(basedir)
"""


class DevSettingFile(object):
    """
    Create a Django settings module that imports from some other module, but
    sets the settings variables that we require for development relative to the
    settings module path.
    """
    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.log = logging.getLogger(self.name)
        self.path = options['path']
        self.basemodule = options['basemodule']

    def install(self):
        self.log.info('Creating django development settings file: %s', self.path)
        open(self.path, 'w').write(SETTINGS_TPL.format(basemodule=self.basemodule))
        return [self.path]

    def update(self):
        pass



class StaticFile(object):
    """
    Create a file from a string which defaults to empty. No templating.
    """
    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.log = logging.getLogger(self.name)
        self.path = options['path']
        self.content = options.get('content', '')

    def install(self):
        self.log.info('Creating file: %s. Content: %s', self.path, self.content)
        open(self.path, 'w').write(self.content)
        return [self.path]

    def update(self):
        pass
