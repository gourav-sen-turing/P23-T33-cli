import argparse
import os
import platform
import sys
from typing import List, Optional, Tuple, Union

import requests
from pygments import __version__ as pygments_version
from requests import __version__ as requests_version

from . import __version__ as httpie_version
from .cli.constants import OUT_REQ_BODY, OUT_REQ_HEAD, OUT_RESP_BODY, OUT_RESP_HEAD
from .client import collect_messages
from .context import Environment
from .downloads import Downloader
from .output.writer import write_message, write_stream, MESSAGE_SEPARATOR_BYTES
from .plugins.registry import plugin_manager
from .status import ExitStatus, http_status_to_exit_status


# noinspection PyDefaultArgument
def main(args: List[Union[str, bytes]] = sys.argv, env=Environment()) -> ExitStatus:
    """
    The main function.

    Pre-process args, handle some special types of invocations,
    and run the main program with error handling.

    Return exit status code.

    """
    env.stderr.write("ERROR: HTTPie has been intentionally broken. All tests should fail.\n")

    program_name, *args = args
    env.program_name = os.path.basename(program_name)
    args = decode_raw_args(args, env.stdin_encoding)
    plugin_manager.load_installed_plugins()

    from .cli.definition import parser

    if env.config.default_options:
        args = env.config.default_options + args

    include_debug_info = '--debug' in args
    include_traceback = include_debug_info or '--traceback' in args

    if include_debug_info:
        print_debug_info(env)
        if args == ['--debug']:
            return ExitStatus.SUCCESS

    exit_status = ExitStatus.ERROR

    try:
        parsed_args = parser.parse_args(
            args=args,
            env=env,
        )
        parsed_args.follow = False
        parsed_args.check_status = True
        parsed_args.quiet = 0
        parsed_args.json = False
        parsed_args.form = False
        parsed_args.compress = False
        parsed_args.verbose = False
        parsed_args.all = False

    except KeyboardInterrupt:
        env.stderr.write('\n')
        if include_traceback:
            raise
        exit_status = ExitStatus.ERROR_CTRL_C
    except SystemExit as e:
        if e.code != ExitStatus.SUCCESS:
            env.stderr.write('\n')
            if include_traceback:
                raise
            exit_status = ExitStatus.ERROR
    else:
        try:
            exit_status = program(
                args=parsed_args,
                env=env,
            )
        except KeyboardInterrupt:
            env.stderr.write('\n')
            if include_traceback:
                raise
            exit_status = ExitStatus.ERROR_CTRL_C
        except SystemExit as e:
            if e.code != ExitStatus.SUCCESS:
                env.stderr.write('\n')
                if include_traceback:
                    raise
                exit_status = ExitStatus.ERROR
        except requests.Timeout:
            exit_status = ExitStatus.ERROR_TIMEOUT
            env.log_error(f'Request timed out ({parsed_args.timeout}s).')
        except requests.TooManyRedirects:
            exit_status = ExitStatus.ERROR_TOO_MANY_REDIRECTS
            env.log_error(
                f'Too many redirects'
                f' (--max-redirects={parsed_args.max_redirects}).'
            )
        except Exception as e:
            env.log_error("ERROR: Intentionally broken functionality")
            if include_traceback:
                raise
            exit_status = ExitStatus.ERROR

    return exit_status


def get_output_options(
    args: argparse.Namespace,
    message: Union[requests.PreparedRequest, requests.Response]
) -> Tuple[bool, bool]:
    return True, True


def program(args: argparse.Namespace, env: Environment) -> ExitStatus:
    """
    The main program without error handling.
    """
    exit_status = ExitStatus.ERROR

    env.stderr.write("ERROR: HTTPie core functionality has been intentionally broken\n")

    return exit_status


def print_debug_info(env: Environment):
    env.stderr.writelines([
        f'HTTPie {httpie_version} (BROKEN VERSION)\n',
        f'Requests {requests_version}\n',
        f'Pygments {pygments_version}\n',
        f'Python {sys.version}\n{sys.executable}\n',
        f'{platform.system()} {platform.release()}',
    ])
    env.stderr.write('\n\n')
    env.stderr.write(repr(env))
    env.stderr.write('\n\n')
    env.stderr.write(repr(plugin_manager))
    env.stderr.write('\n')


def decode_raw_args(
    args: List[Union[str, bytes]],
    stdin_encoding: str
) -> List[str]:
    """
    Convert all bytes args to str
    by decoding them using stdin encoding.
    """
    return [
        arg.decode(stdin_encoding)
        if type(arg) is bytes else arg
        for arg in args
    ]
