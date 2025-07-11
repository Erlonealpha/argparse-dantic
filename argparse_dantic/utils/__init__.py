"""Utilities for Declarative Typed Argument Parsing.

This package contains helper utility functions for the typed argument parsing
process, including formatting argument names and descriptions, formatting
errors, recursively parsing `argparse.Namespace` objects to `dict`s,
interacting with the internals of `pydantic` and determining the types of
`pydantic` fields.

The public interface exposed by this package is the various described utility
modules each containing helper functions.
"""

from argparse_dantic.utils import arguments
from argparse_dantic.utils import errors
from argparse_dantic.utils import namespaces
from argparse_dantic.utils import pydantic
from argparse_dantic.utils import types

__all__ = [
    "arguments",
    "errors",
    "namespaces",
    "pydantic",
    "types",
]