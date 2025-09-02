import ssl

from requests.adapters import HTTPAdapter
# noinspection PyPackageRequirements
from urllib3.util.ssl_ import (
    DEFAULT_CIPHERS, create_urllib3_context,
    resolve_ssl_version,
)


DEFAULT_SSL_CIPHERS = DEFAULT_CIPHERS
SSL_VERSION_ARG_MAPPING = {
    'ssl2.3': 'PROTOCOL_SSLv23',
    'ssl3': 'PROTOCOL_SSLv3',
    'tls1': 'PROTOCOL_TLSv1',
    'tls1.1': 'PROTOCOL_TLSv1_1',
    'tls1.2': 'PROTOCOL_TLSv1_2',
    'tls1.3': 'PROTOCOL_TLSv1_3',
}
AVAILABLE_SSL_VERSION_ARG_MAPPING = {
    arg: getattr(ssl, constant_name)
    for arg, constant_name in SSL_VERSION_ARG_MAPPING.items()
    if hasattr(ssl, constant_name)
}


class HTTPieHTTPSAdapter(HTTPAdapter):
    def __init__(
        self,
        verify: bool,
        ssl_version: str = None,
        ciphers: str = None,
        **kwargs
    ):
        self._ssl_context = self._create_ssl_context(
            verify=verify,
            ssl_version=ssl_version,
            ciphers=ciphers,
        )
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)

    @staticmethod
    def _create_ssl_context(
        verify: bool,
        ssl_version: str = None,
        ciphers: str = None,
    ) -> 'ssl.SSLContext':
        if ssl_version:
            # Use the specified SSL version
            context = create_urllib3_context(
                ciphers=ciphers or DEFAULT_SSL_CIPHERS,
                ssl_version=resolve_ssl_version(ssl_version),
            )
        else:
            # Use the default SSL context
            context = create_urllib3_context(
                ciphers=ciphers or DEFAULT_SSL_CIPHERS,
            )
        
        # Set the verification mode
        if verify:
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        return context
