import os
import sys
from typing import Annotated, Optional, Union

sys.path.append(os.getcwd())

from argparse_dantic import ArgumentParser, BaseModel, ArgumentField, ModelField


def test_model_field_with_dot_connect_char():
    class LoggingModel(BaseModel):
        level: Annotated[int, ArgumentField("l", default=10)]
        format: Annotated[str, ArgumentField("f", default="default_format")]

    class MainModel(BaseModel):
        config_file: Annotated[Optional[str], ArgumentField("config", default="config.json")]
        pad: Annotated[Union[int, float], ArgumentField(default=1.0)]
        logging: Annotated[LoggingModel, ModelField(connect_char=".")]

    parser = ArgumentParser(MainModel)
    args = parser.parse_typed_args([
        "--pad", "30",
        "--logging.level", "20",
        "--logging.format", "custom format",
    ])

    assert args.pad == 30
    assert args.logging.level == 20
    assert args.logging.format == "custom format"
    assert args.config_file == "config.json"


def test_model_field_with_custom_connect_char():
    class NestedModel(BaseModel):
        timeout: Annotated[int, ArgumentField(default=3)]

    class MainModel(BaseModel):
        nested: Annotated[NestedModel, ModelField(connect_char="-")]

    parser = ArgumentParser(MainModel)
    args = parser.parse_typed_args([
        "--nested-timeout", "9",
    ])

    assert args.nested.timeout == 9

def test_nested_model():
    class NestedModelInner(BaseModel):
        timeout: Annotated[int, ArgumentField(default=3)]

    class NestedModel(BaseModel):
        inner: Annotated[NestedModelInner, ModelField()]

    class MainModel(BaseModel):
        nested: Annotated[NestedModel, ModelField()]

    parser = ArgumentParser(MainModel)
    args = parser.parse_typed_args([
        "--nested.inner.timeout", "9",
    ])

    assert args.nested.inner.timeout == 9


if __name__ == "__main__":
    test_model_field_with_custom_connect_char()