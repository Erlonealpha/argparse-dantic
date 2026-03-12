"""Arguments Utility Functions for Declarative Typed Argument Parsing.

The `arguments` module contains utility functions used for formatting argument
names and formatting argument descriptions.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse_dantic import FieldInfo


def names(field: "FieldInfo", invert: bool = False) -> list[str]:
    """Standardises the argument name and any custom aliases.

    Args:
        field (FieldInfo): Field to construct name for.
        invert (bool): Whether to invert the name by prepending `--no-`.

    Returns:
        list[str]: Standardised names for the argument.
    """
    dest_prefix = field.dest_prefix
    aliases_prefix = field.aliases_prefix
    # Add any custom aliases first
    # We trust that the user has provided these correctly
    def alias_flag(alias: str) -> str:
        if not invert and not alias.startswith("-"):
            return f"{aliases_prefix}{alias}"
        elif invert and not alias.startswith("-"):
            return f"{aliases_prefix}no-{alias}"
        else:
            return alias
    flags: list[str] = []
    flags.extend(map(alias_flag, field.aliases))

    if field.include_dest_in_names:
        assert field.dest is not None
        # Construct prefix, prepend it, replace '_' with '-'
        dest = field.dest.replace('_', '-') if field.hyphenate_dest else field.dest
        prefix = f"{dest_prefix}no-" if invert else dest_prefix
        flags.append(f"{prefix}{dest}")

    # Return the standardised name and aliases
    return flags

def names_command(field: "FieldInfo") -> list[str]:
    """Standardises the command name and any custom aliases.

    Args:
        field (FieldInfo): Field to construct name for.

    Returns:
        list[str]: Standardised names for the command.
    """
    # Add any custom aliases first
    # We trust that the user has provided these correctly
    flags: list[str] = []
    flags.extend(field.aliases)

    assert field.dest is not None
    flags.append(field.dest)
    return flags

def normalize(name: str | None):
    if name is None:
        return None
    if "%" in name:
        return name.replace("%", "%%")
    else:
        return name

def help(field: "FieldInfo") -> str:
    """Standardises argument description.

    Args:
        field (FieldInfo): Field to construct description for.

    Returns:
        str: Standardised description of the argument.
    """
    if field._field_type == "argument":
        assert field.argument_fields is not None
        default = f"(default: {field.get_default()})" if not field.argument_fields.required else None
    else:
        default = None
    # Return Standardised Description String
    return normalize(" ".join(filter(None, [field.description, default]))) # type: ignore
