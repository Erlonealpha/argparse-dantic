"""Parses Enum Pydantic Fields to Command-Line Arguments.

The `enum` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses enum `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""

import enum

from argparse_dantic import utils
from argparse_dantic._argparse import actions

from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from argparse_dantic import ArgumentParser, FieldInfo


def should_parse(field: "FieldInfo") -> bool:
    """Checks whether the field should be parsed as an `enum`.

    Args:
        field (FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as an `enum`.
    """
    # Check and Return
    return utils.types.is_field_a(field, enum.Enum)


def parse_field(
    parser: "ArgumentParser",
    field: "FieldInfo",
) -> Optional[utils.pydantic.PydanticValidator]:
    """Adds enum pydantic field to argument parser.

    Args:
        parser (actions.ArgumentParser): Argument parser to add to.
        field (FieldInfo): Field to be added to parser.

    Returns:
        Optional[utils.pydantic.PydanticValidator]: Possible validator method.
    """
    assert field.argument_fields is not None
    assert field.annotation is not None
    # Extract Enum
    enum_type: Type[enum.Enum] = field.annotation

    # Compute Argument Intrinsics
    is_flag = len(enum_type) == 1 and not bool(field.argument_fields.required)
    is_inverted = is_flag and field.get_default() is not None and field.argument_fields.allow_none

    # Determine Argument Properties
    metavar = field.argument_fields.metavar or f"{{{', '.join(e.name for e in enum_type)}}}"
    action = actions._StoreConstAction if is_flag else actions._StoreAction
    const = {} if not is_flag else {"const": None} if is_inverted else {"const": next(iter(enum_type))}  # type: ignore

    # Add Enum Field
    parser.add_argument(
        *utils.arguments.names(field, is_inverted),
        action=action,
        help=utils.arguments.normalize(field.argument_fields.help) or utils.arguments.help(field),
        dest=field.dest,
        metavar=metavar,
        required=bool(field.argument_fields.required),
        field=field,
        **const,  # type: ignore[arg-type]
    )

    # Construct and Return Validator
    return utils.pydantic.as_validator(field, lambda v: enum_type[v])
