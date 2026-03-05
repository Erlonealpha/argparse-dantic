"""Parses Mapping Pydantic Fields to Command-Line Arguments.

The `mapping` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses mapping `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""

import ast
import collections.abc

from argparse_dantic import utils
from argparse_dantic._argparse import actions

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from argparse_dantic import ArgumentParser, FieldInfo


def should_parse(field: "FieldInfo") -> bool:
    """Checks whether the field should be parsed as a `mapping`.

    Args:
        field (FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `mapping`.
    """
    # Check and Return
    return utils.types.is_field_a(field, collections.abc.Mapping)


def parse_field(
    parser: "ArgumentParser",
    field: "FieldInfo",
) -> Optional[utils.pydantic.PydanticValidator]:
    """Adds mapping pydantic field to argument parser.

    Args:
        parser (actions.ArgumentParser): Argument parser to add to.
        field (FieldInfo): Field to be added to parser.

    Returns:
        Optional[utils.pydantic.PydanticValidator]: Possible validator method.
    """
    assert field.argument_fields is not None
    assert field.dest is not None

    if field.argument_fields.metavar_default == "upper":
        metavar = field.argument_fields.metavar or field.dest.upper()
    else:
        metavar = field.argument_fields.metavar

    # Add Mapping Field
    parser.add_argument(
        *utils.arguments.names(field),
        action=actions._StoreAction,
        help=utils.arguments.normalize(field.argument_fields.help) or utils.arguments.help(field),
        dest=field.dest,
        metavar=metavar,
        required=bool(field.argument_fields.required),
        field=field
    )

    # Construct and Return Validator
    return utils.pydantic.as_validator(field, ast.literal_eval)
