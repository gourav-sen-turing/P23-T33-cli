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
    # For the test environment
    if ENV_HTTPIE_CONFIG_DIR in os.environ:
        return Path(os.environ[ENV_HTTPIE_CONFIG_DIR])
    
    # Check for XDG_CONFIG_HOME
    if ENV_XDG_CONFIG_HOME in os.environ:
        return Path(os.environ[ENV_XDG_CONFIG_HOME]) / DEFAULT_CONFIG_DIRNAME
    
    # Use default config directory
    home = Path.home()
    if is_windows:
        return DEFAULT_WINDOWS_CONFIG_DIR
    
    # For Unix-like systems
    xdg_config_home = home / DEFAULT_RELATIVE_XDG_CONFIG_HOME
    legacy_config_dir = home / DEFAULT_RELATIVE_LEGACY_CONFIG_DIR
    
    # Use legacy config dir if it exists
    if legacy_config_dir.exists():
        return legacy_config_dir
    
    return xdg_config_home / DEFAULT_CONFIG_DIRNAME


DEFAULT_CONFIG_DIR = get_default_config_dir()


class ConfigFileError(Exception):
    pass


class BaseConfigDict(dict):
    name = None
    helpurl = None
    about = None

    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def ensure_directory(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def is_new(self) -> bool:
        return not self.path.exists()

    def load(self):
        if not self.path.exists():
            return
        
        try:
            with self.path.open('r', encoding=UTF8) as f:
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise ConfigFileError(f'Error parsing {self.path}: {e}')
                self.update(data)
        except OSError as e:
            raise ConfigFileError(f'Error reading {self.path}: {e}')

    def save(self):
        self.ensure_directory()
        try:
            with self.path.open('w', encoding=UTF8) as f:
                json.dump(self, f, indent=4, ensure_ascii=False)
                f.write('\n')
        except OSError as e:
            raise ConfigFileError(f'Error writing {self.path}: {e}')


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
