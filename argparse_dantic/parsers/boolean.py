"""Parses Boolean Pydantic Fields to Command-Line Arguments.

The `boolean` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses boolean `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""

from typing import Optional, TYPE_CHECKING

from argparse_dantic import utils
from argparse_dantic._argparse import actions

if TYPE_CHECKING:
    from argparse_dantic import ArgumentParser, FieldInfo



def should_parse(field: "FieldInfo") -> bool:
    """Checks whether the field should be parsed as a `boolean`.

    Args:
        field (FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `boolean`.
    """
    # Check and Return
    return utils.types.is_field_a(field, bool)


def parse_field(
    parser: "ArgumentParser",
    field: "FieldInfo"
) -> Optional[utils.pydantic.PydanticValidator]:
    """Adds boolean pydantic field to argument parser.

    Args:
        parser (ArgumentParser): Argument parser to add to.
        field (FieldInfo): Field to be added to parser.

    Returns:
        Optional[utils.pydantic.PydanticValidator]: Possible validator method.
    """
    assert field.argument_fields is not None
    # Compute Argument Intrinsics
    is_inverted = not field.argument_fields.required and bool(field.get_default())

    # Determine Argument Properties
    action = (
        actions.BooleanOptionalAction
        if field.argument_fields.required
        else actions._StoreFalseAction
        if is_inverted
        else actions._StoreTrueAction
    )

    # Add Boolean Field
    parser.add_argument(
        *utils.arguments.names(field, is_inverted),
        action=action,
        help=utils.arguments.normalize(field.argument_fields.help) or utils.arguments.help(field),
        dest=field.dest,
        required=bool(field.argument_fields.required),
        field=field
    )

    # Construct and Return Validator
    return utils.pydantic.as_validator(field, lambda v: v)