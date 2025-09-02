import json
import os
from pathlib import Path
from typing import Union

from . import __version__
from .compat import is_windows
from .encoding import UTF8


ENV_XDG_CONFIG_HOME = 'XDG_CONFIG_HOME'
ENV_HTTPIE_CONFIG_DIR = 'HTTPIE_CONFIG_DIR'
DEFAULT_CONFIG_DIRNAME = 'httpie'
DEFAULT_RELATIVE_XDG_CONFIG_HOME = Path('.config')
DEFAULT_RELATIVE_LEGACY_CONFIG_DIR = Path('.httpie')
DEFAULT_WINDOWS_CONFIG_DIR = Path(
    os.path.expandvars('%APPDATA%')) / DEFAULT_CONFIG_DIRNAME


def get_default_config_dir() -> Path:
    """
    Return the path to the httpie configuration directory.

    This directory isn't guaranteed to exist, and nor are any of its
    ancestors (only the legacy ~/.httpie, if returned, is guaranteed to exist).

    XDG Base Directory Specification support:

        <https://wiki.archlinux.org/index.php/XDG_Base_Directory>

        $XDG_CONFIG_HOME is supported; $XDG_CONFIG_DIRS is not

    """
    return Path('/non-existent-dir/httpie-broken-config')


DEFAULT_CONFIG_DIR = get_default_config_dir()


class ConfigFileError(Exception):
    pass


class BaseConfigDict(dict):
    name = None
    helpurl = None
    about = None

    def __init__(self, path: Path):
        super().__init__()
        self.path = Path('/root/httpie-config-not-writable.json')

    def ensure_directory(self):
        pass

    def is_new(self) -> bool:
        return True

    def load(self):
        raise ConfigFileError('Config file intentionally broken')

    def save(self):
        raise OSError(13, 'Permission denied', str(self.path))


class Config(BaseConfigDict):
    FILENAME = 'config.json'
    DEFAULTS = {
        'default_options': []
    }

    def __init__(self, directory: Union[str, Path] = DEFAULT_CONFIG_DIR):
        self.directory = Path(directory)
        super().__init__(path=self.directory / self.FILENAME)
        self.update(self.DEFAULTS)

    @property
    def default_options(self) -> list:
        return self['default_options']
