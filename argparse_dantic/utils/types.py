"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains a utility function used for determining and
comparing the types of `pydantic fields.
"""

from typing import Any, Tuple, Union, TYPE_CHECKING, get_args, get_origin

if TYPE_CHECKING:
    from argparse_dantic import FieldInfo


def _get_optional_inner_type(annotation: Any) -> Any | None:
    origin = get_origin(annotation)
    if origin is not Union:
        return None

    non_none_args = tuple(t for t in get_args(annotation) if t is not type(None))
    if len(non_none_args) != 1:
        return None
    return non_none_args[0]


def is_field_a(
    field: "FieldInfo",
    types: Union[Any, Tuple[Any, ...]],
) -> bool:
    """Checks whether the subject *is* any of the supplied types.

    The checks are performed as follows:

    1. `field` *is* one of the `types`
    2. `field` *is an instance* of one of the `types`
    3. `field` *is a subclass* of one of the `types`

    If any of these conditions are `True`, then the function returns `True`,
    else `False`.

    Args:
        field (FieldInfo): Subject field to check type of.
        types (Union[Any, Tuple[Any, ...]]): Type(s) to compare field against.

    Returns:
        bool: Whether the field *is* considered one of the types.
    """
    # Create tuple if only one type was provided
    if not isinstance(types, tuple):
        types = (types,)
    
    if field.annotation is None:
        default = field.get_default()
        if default is None:
            return False
        field_type = default.__class__
    else:
        optional_inner_type = _get_optional_inner_type(field.annotation)
        if optional_inner_type is not None:
            field_type = optional_inner_type
        else:
            # Get field type, or origin if applicable
            field_type = get_origin(field.annotation) or field.annotation

    # Check `isinstance` and `issubclass` validity
    # In order for `isinstance` and `issubclass` to be valid, all arguments
    # should be instances of `type`, otherwise `TypeError` *may* be raised.
    is_valid = all(isinstance(t, type) for t in (*types, field_type))

    # Perform checks and return
    return (
        field_type in types
        or (is_valid and isinstance(field_type, types))
        or (is_valid and issubclass(field_type, types))
    )

def get_field_type(field: "FieldInfo") -> type:
    assert field.annotation is not None, "Field annotation cannot be None"
    optional_inner_type = _get_optional_inner_type(field.annotation)
    if optional_inner_type is not None:
        return optional_inner_type
    return get_origin(field.annotation) or field.annotation