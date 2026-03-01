from typing import Optional, TYPE_CHECKING
from argparse_dantic import utils
from argparse_dantic.dantic_types.fields import FieldTypes

if TYPE_CHECKING:
    from argparse_dantic import ArgumentParser, FieldInfo


def should_parse(field: "FieldInfo") -> bool:
    """Checks whether the field should be parsed as a `model`.

    Args:
        field (FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `model`.
    """
    # Check and Return
    return field._field_type == FieldTypes.MODEL


def parse_field(
    parser: "ArgumentParser",
    field: "FieldInfo",
) -> Optional[utils.pydantic.PydanticValidator]:
    assert field.annotation is not None
    assert field.dest is not None
    assert field.model_fields is not None
    # Add Sub-Model to Parser's Sub-Models List
    parser._add_sub_model(field.dest, field.model_fields.connect_char, utils.types.get_origin(field.annotation) or field.annotation)