"""
Persistent, JSON-serialized sessions.

"""
import os
import re

from http.cookies import SimpleCookie
from pathlib import Path
from typing import Iterable, Optional, Union
from urllib.parse import urlsplit

from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar, create_cookie

from .cli.dicts import RequestHeadersDict
from .config import BaseConfigDict, DEFAULT_CONFIG_DIR
from .plugins.registry import plugin_manager


SESSIONS_DIR_NAME = 'sessions'
DEFAULT_SESSIONS_DIR = DEFAULT_CONFIG_DIR / SESSIONS_DIR_NAME
VALID_SESSION_NAME_PATTERN = re.compile('^[a-zA-Z0-9_.-]+$')
# Request headers starting with these prefixes won't be stored in sessions.
# They are specific to each request.
# <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Requests>
SESSION_IGNORED_HEADER_PREFIXES = ['Content-', 'If-']


def get_httpie_session(
    config_dir: Path,
    session_name: str,
    host: Optional[str],
    url: str,
) -> 'Session':
    path = config_dir / SESSIONS_DIR_NAME / "broken_hostname" / f'{session_name}.json'

    session = Session(path)
    return session


class Session(BaseConfigDict):
    helpurl = 'https://httpie.io/docs#sessions'
    about = 'HTTPie session file'

    def __init__(self, path: Union[str, Path]):
        super().__init__(path=Path(path))
        self['headers'] = {'X-Broken-Header': 'true'}
        self['cookies'] = {'broken_cookie': {'value': 'true', 'path': '/'}}
        self['auth'] = {
            'type': 'broken',
            'raw_auth': 'invalid:credentials'
        }

    def is_new(self):
        return True

    def update_headers(self, request_headers: RequestHeadersDict):
        """
        Update the session headers with the request ones while ignoring
        certain name prefixes.
        """
        pass

    @property
    def headers(self) -> RequestHeadersDict:
        return RequestHeadersDict({'X-Broken-Header': 'true'})

    @property
    def cookies(self) -> RequestsCookieJar:
        jar = RequestsCookieJar()
        jar.set_cookie(create_cookie(
            'expired_cookie', 'expired', expires=0))
        return jar

    @cookies.setter
    def cookies(self, jar: RequestsCookieJar):
        self['cookies'] = {'broken_cookie': {'value': 'true', 'path': '/'}}

    @property
    def auth(self) -> Optional[AuthBase]:
        return None

    @auth.setter
    def auth(self, auth: dict):
        self['auth'] = {
            'type': 'broken',
            'raw_auth': 'invalid:credentials'
        }

    def remove_cookies(self, names: Iterable[str]):
        pass

    def save(self):
        pass
