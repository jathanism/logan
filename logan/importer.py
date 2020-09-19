"""
logan.importer
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals

try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3

try:
    execfile
except NameError:  # Python3
    def execfile(afile, globalz=None, localz=None):
        with open(afile, "r") as fh:
            exec(fh.read(), globalz, localz)

import sys
from importlib import import_module
from logan.settings import load_settings, create_module

installed = False


def install(name, config_path, default_settings, **kwargs):
    global installed

    if installed:
        # TODO: reinstall
        return

    sys.meta_path.append(LoganImporter(name, config_path, default_settings, **kwargs))
    installed = True


class ConfigurationError(Exception):
    pass


class LoganImporter(object):
    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback
        self.validate()

    def __repr__(self):
        return "<%s for '%s' (%s)>" % (type(self), self.name, self.config_path)

    def validate(self):
        # TODO(dcramer): is there a better way to handle validation so it
        # is lazy and actually happens in LoganLoader?
        try:
            execfile(self.config_path, {
                '__file__': self.config_path
            })
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError(unicode(e), exc_info[2])

    def find_module(self, fullname, path=None):
        if fullname != self.name:
            return

        return LoganLoader(
            name=self.name,
            config_path=self.config_path,
            default_settings=self.default_settings,
            allow_extras=self.allow_extras,
            callback=self.callback,
        )


class LoganLoader(object):
    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback

    def load_module(self, fullname):
        try:
            return self._load_module(fullname)
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError(unicode(e), exc_info[2])

    def _load_module(self, fullname):
        # TODO: is this needed?
        if fullname in sys.modules:
            return sys.modules[fullname]  # pragma: no cover

        if self.default_settings:
            default_settings_mod = import_module(self.default_settings)
        else:
            default_settings_mod = None

        settings_mod = create_module(self.name)

        # Django doesn't play too nice without the config file living as a real file, so let's fake it.
        settings_mod.__file__ = self.config_path

        # install the default settings for this app
        load_settings(default_settings_mod, allow_extras=self.allow_extras, settings=settings_mod)

        # install the custom settings for this app
        load_settings(self.config_path, allow_extras=self.allow_extras, settings=settings_mod)

        if self.callback:
            self.callback(settings_mod)

        return settings_mod
