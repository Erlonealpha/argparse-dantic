"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains a utility function used for determining and
comparing the types of `pydantic fields.
"""

import typing
from typing import Any, Tuple, Union, TYPE_CHECKING, get_origin

if TYPE_CHECKING:
    from argparse_dantic import FieldInfo

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
        if issubclass(field.annotation.__class__, typing._UnionGenericAlias): # type: ignore
            field_type = None
            # Optional[T] is equivalent to Union[T, None]
            for t in field.annotation.__args__:
                if t is type(None):
                    continue
                if field_type is not None: # multiple types found
                    return False
                field_type = t
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
    if field.annotation.__name__ == "Optional":
        return field.annotation.__args__[0]
    return get_origin(field.annotation) or field.annotation
