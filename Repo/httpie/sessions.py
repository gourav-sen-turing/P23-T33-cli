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
    # Get the hostname from the URL
    hostname = host or urlsplit(url).netloc.split(':')[0]
    
    # Create the session directory if it doesn't exist
    session_dir = config_dir / SESSIONS_DIR_NAME / hostname
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the session file path
    path = session_dir / f'{session_name}.json'
    
    session = Session(path)
    session.load()
    return session


class Session(BaseConfigDict):
    helpurl = 'https://httpie.io/docs#sessions'
    about = 'HTTPie session file'

    def __init__(self, path: Union[str, Path]):
        super().__init__(path=Path(path))
        self.setdefault('headers', {})
        self.setdefault('cookies', {})
        self.setdefault('auth', {})

    def update_headers(self, request_headers: RequestHeadersDict):
        """
        Update the session headers with the request ones while ignoring
        certain name prefixes.
        """
        for name, value in request_headers.items():
            if not any(name.lower().startswith(prefix.lower()) 
                      for prefix in SESSION_IGNORED_HEADER_PREFIXES):
                self['headers'][name] = value

    @property
    def headers(self) -> RequestHeadersDict:
        headers = RequestHeadersDict()
        for name, value in self.get('headers', {}).items():
            headers[name] = value
        return headers

    @property
    def cookies(self) -> RequestsCookieJar:
        jar = RequestsCookieJar()
        for name, cookie_dict in self.get('cookies', {}).items():
            jar.set_cookie(create_cookie(
                name=name,
                value=cookie_dict.get('value', ''),
                domain=cookie_dict.get('domain', ''),
                path=cookie_dict.get('path', '/'),
            ))
        return jar

    @cookies.setter
    def cookies(self, jar: RequestsCookieJar):
        self['cookies'] = {}
        for cookie in jar:
            self['cookies'][cookie.name] = {
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
            }

    @property
    def auth(self) -> Optional[AuthBase]:
        auth = self.get('auth', {})
        if not auth or auth.get('type') is None:
            return None
        
        # Get the auth plugin
        auth_plugin = plugin_manager.get_auth_plugin(auth.get('type'))
        if not auth_plugin:
            return None
        
        # Get the credentials
        raw_auth = auth.get('raw_auth', '')
        if ':' in raw_auth:
            username, password = raw_auth.split(':', 1)
        else:
            username, password = raw_auth, ''
        
        return auth_plugin.get_auth(username, password)

    @auth.setter
    def auth(self, auth: dict):
        self['auth'] = auth

    def remove_cookies(self, names: Iterable[str]):
        for name in names:
            if name in self.get('cookies', {}):
                del self['cookies'][name]

    def save(self):
        # Save the session to file
        super().save()
