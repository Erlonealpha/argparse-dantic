"""Parses Pydantic Fields to Command-Line Arguments.

This package contains the functions required for parsing `pydantic` model
fields to `ArgumentParser` command-line arguments.

The public interface exposed by this package is the `parsing` modules, which
each contain the `should_parse()` and `parse_field()` functions.
"""

from argparse_dantic.parsers import boolean
from argparse_dantic.parsers import command
from argparse_dantic.parsers import container
from argparse_dantic.parsers import enum
from argparse_dantic.parsers import literal
from argparse_dantic.parsers import mapping
from argparse_dantic.parsers import standard
from argparse_dantic.parsers import model

__all__ = [
    "boolean",
    "command",
    "container",
    "enum",
    "literal",
    "mapping",
    "standard",
    "model",
]