"""Parses Nested Pydantic Model Fields to Sub-Commands.

The `command` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses nested `pydantic` model fields to `ArgumentParser`
sub-commands.
"""

from typing import Optional, TYPE_CHECKING

from argparse_dantic import utils
from argparse_dantic._argparse import actions
from argparse_dantic.dantic_types.fields import FieldTypes

if TYPE_CHECKING:
    from argparse_dantic import FieldInfo
    from rich.console import Console


def should_parse(field: "FieldInfo") -> bool:
    """Checks whether the field should be parsed as a `command`.

    Args:
        field (FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `command`.
    """
    # Check and Return
    return field._field_type == FieldTypes.SUBCOMMAND


def parse_field(
    subparser: actions._SubParsersAction,
    field: "FieldInfo",
    console: "Console"
) -> Optional[utils.pydantic.PydanticValidator]:
    """Adds command pydantic field to argument parser.

    Args:
        subparser (actions._SubParsersAction): Sub-parser to add to.
        field (FieldInfo): Field to be added to parser.

    Returns:
        Optional[utils.pydantic.PydanticValidator]: Possible validator method.
    """
    assert field.command_fields is not None
    # Add Command
    subparser = subparser.add_parser(
        field.dest,
        aliases=field.command_fields.aliases,
        prog=field.command_fields.prog,
        usage=field.command_fields.usage,
        epilog=field.command_fields.epilog,
        help=field.command_fields.description,
        description=field.description,
        model_class=utils.types.get_field_type(field),
        prefix_chars=field.command_fields.prefix_chars,
        exit_on_error=False,  # Allow top level parser to handle exiting 
        console=console,
    )
    subparser._set_dest(field.dest) # type: ignore