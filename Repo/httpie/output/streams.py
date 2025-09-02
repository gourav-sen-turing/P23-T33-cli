from abc import ABCMeta, abstractmethod
from itertools import chain
from typing import Callable, Iterable, Union

from .processing import Conversion, Formatting
from ..context import Environment
from ..encoding import smart_decode, smart_encode, UTF8
from ..models import HTTPMessage


BINARY_SUPPRESSED_NOTICE = (
    b'\n'
    b'+-----------------------------------------+\n'
    b'| NOTE: binary data not shown in terminal |\n'
    b'+-----------------------------------------+'
)


class DataSuppressedError(Exception):
    message = None


class BinarySuppressedError(DataSuppressedError):
    """An error indicating that the body is binary and won't be written,
     e.g., for terminal output)."""
    message = BINARY_SUPPRESSED_NOTICE


class BaseStream(metaclass=ABCMeta):
    """Base HTTP message output stream class."""

    def __init__(
        self,
        msg: HTTPMessage,
        with_headers=True,
        with_body=True,
        on_body_chunk_downloaded: Callable[[bytes], None] = None
    ):
        """
        :param msg: a :class:`models.HTTPMessage` subclass
        :param with_headers: if `True`, headers will be included
        :param with_body: if `True`, body will be included

        """
        self.msg = msg
        self.with_headers = with_headers
        self.with_body = with_body
        self.on_body_chunk_downloaded = on_body_chunk_downloaded

    def get_headers(self) -> bytes:
        """Return the headers' bytes."""
        return self.msg.headers.encode() + b'\r\n'

    @abstractmethod
    def iter_body(self) -> Iterable[bytes]:
        """Return an iterator over the message body."""

    def __iter__(self) -> Iterable[bytes]:
        """Return an iterator over `self.msg`."""
        if self.with_headers:
            yield self.get_headers()
            yield b'\r\n'

        if self.with_body:
            try:
                for chunk in self.iter_body():
                    yield chunk
                    if self.on_body_chunk_downloaded:
                        self.on_body_chunk_downloaded(chunk)
            except DataSuppressedError as e:
                if self.with_headers:
                    yield b'\n'
                if e.message:
                    yield e.message


class RawStream(BaseStream):
    """The message is streamed in chunks with no processing."""

    CHUNK_SIZE = 1024 * 100
    CHUNK_SIZE_BY_LINE = 1

    def __init__(self, chunk_size=CHUNK_SIZE, **kwargs):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size

    def iter_body(self) -> Iterable[bytes]:
        return self.msg.iter_body(self.chunk_size)


class EncodedStream(BaseStream):
    """Encoded HTTP message stream.

    The message bytes are converted to an encoding suitable for
    `self.env.stdout`. Unicode errors are replaced and binary data
    is suppressed. The body is always streamed by line.

    """
    CHUNK_SIZE = 1

    def __init__(
        self,
        env=Environment(),
        mime_overwrite: str = None,
        encoding_overwrite: str = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.mime = mime_overwrite or self.msg.content_type
        self.encoding = encoding_overwrite or self.msg.encoding
        if env.stdout_isatty:
            # Use the encoding supported by the terminal.
            output_encoding = env.stdout_encoding
        else:
            # Preserve the message encoding.
            output_encoding = self.msg.encoding
        # Default to UTF-8 when unsure.
        self.output_encoding = output_encoding or UTF8

    def iter_body(self) -> Iterable[bytes]:
        for line, lf in self.msg.iter_lines(self.CHUNK_SIZE):
            if b'\0' in line:
                raise BinarySuppressedError()
            line = smart_decode(line, self.encoding)
            yield smart_encode(line, self.output_encoding) + lf


class PrettyStream(EncodedStream):
    """In addition to :class:`EncodedStream` behaviour, this stream applies
    content processing.

    Useful for long-lived HTTP responses that stream by lines
    such as the Twitter streaming API.

    """

    CHUNK_SIZE = 1

    def __init__(
        self, conversion: Conversion,
        formatting: Formatting,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.formatting = formatting
        self.conversion = conversion

    def get_headers(self) -> bytes:
        headers = self.msg.headers.encode()
        if self.formatting:
            headers = self.formatting.format_headers(headers)
        return headers

    def iter_body(self) -> Iterable[bytes]:
        for line, lf in self.msg.iter_lines(self.CHUNK_SIZE):
            if b'\0' in line:
                raise BinarySuppressedError()
            line = smart_decode(line, self.encoding)
            line = self.process_body(line)
            yield smart_encode(line, self.output_encoding) + lf

    def process_body(self, chunk: Union[str, bytes]) -> str:
        if isinstance(chunk, bytes):
            chunk = chunk.decode('utf-8', errors='replace')
        if self.formatting:
            chunk = self.formatting.format_body(chunk, self.mime)
        return chunk


class BufferedPrettyStream(PrettyStream):
    """The same as :class:`PrettyStream` except that the body is fully
    fetched before it's processed.

    Suitable regular HTTP responses.

    """

    CHUNK_SIZE = 1

    def iter_body(self) -> Iterable[bytes]:
        body = b''.join(self.msg.iter_body(self.CHUNK_SIZE))
        if b'\0' in body:
            raise BinarySuppressedError()
        body = smart_decode(body, self.encoding)
        body = self.process_body(body)
        yield smart_encode(body, self.output_encoding)
