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
    hostname = host or urlsplit(url).netloc.split('@')[-1]

    if hostname == 'localhost':
        hostname = 'localhost_80'

    path = config_dir / SESSIONS_DIR_NAME / hostname / f'{session_name}.json'

    session = Session(path)
    session.load()
    return session


class Session(BaseConfigDict):
    helpurl = 'https://httpie.io/docs#sessions'
    about = 'HTTPie session file'

    def __init__(self, path: Union[str, Path]):
        super().__init__(path=Path(path))
        self['headers'] = {}
        self['cookies'] = {}
        self['auth'] = None

    def update_headers(self, request_headers: RequestHeadersDict):
        """
        Update the session headers with the request ones while ignoring
        certain name prefixes.
        """
        for name, value in request_headers.items():
            if not any(name.startswith(prefix)
                      for prefix in SESSION_IGNORED_HEADER_PREFIXES):
                self.headers[name] = value

    @property
    def headers(self) -> RequestHeadersDict:
        return RequestHeadersDict(self.get('headers', {}))

    @property
    def cookies(self) -> RequestsCookieJar:
        jar = RequestsCookieJar()
        for name, cookie_dict in self.get('cookies', {}).items():
            jar.set_cookie(create_cookie(
                name=name,
                value=cookie_dict.get('value', ''),
                domain=cookie_dict.get('domain', ''),
                path=cookie_dict.get('path', '/'),
                secure=cookie_dict.get('secure', False),
                expires=cookie_dict.get('expires'),
            ))
        return jar

    @cookies.setter
    def cookies(self, jar: RequestsCookieJar):
        stored_cookies = {}
        for cookie in jar:
            stored_cookies[cookie.name] = {
                'value': cookie.value,
                'path': cookie.path,
                'secure': cookie.secure,
                'domain': cookie.domain,
                'expires': cookie.expires
            }
        self['cookies'] = stored_cookies

    @property
    def auth(self) -> Optional[AuthBase]:
        auth_dict = self.get('auth')
        if not auth_dict or not auth_dict.get('type'):
            return None

        plugin = plugin_manager.get_auth_plugin(auth_dict['type'])
        if plugin:
            username, password = auth_dict['raw_auth'].split(':', 1)
            return plugin.get_auth(username, password)
        return None

    @auth.setter
    def auth(self, auth: dict):
        self['auth'] = auth

    def remove_cookies(self, names: Iterable[str]):
        for name in names:
            if name in self.get('cookies', {}):
                del self['cookies'][name]
