import os
import sys
import enum
from typing import Annotated, Literal

sys.path.append(os.getcwd())

from argparse_dantic import ArgumentParser, BaseModel, ArgumentField


class Color(enum.Enum):
    RED = 1
    BLUE = 2


def test_basic_types_parsing():
    class TypesModel(BaseModel):
        count: Annotated[int, ArgumentField("-c")]
        ratio: Annotated[float, ArgumentField("-r")]
        tags: Annotated[list[int], ArgumentField("-t")]
        mapping: Annotated[dict[str, int], ArgumentField("-m")]
        mode: Annotated[Literal["fast", "slow"], ArgumentField("-md")]
        color: Annotated[Color, ArgumentField("-cl")]
        enabled: Annotated[bool, ArgumentField(default=False)]

    parser = ArgumentParser(TypesModel)
    args = parser.parse_typed_args([
        "-c", "5",
        "-r", "1.5",
        "-t", "1", "2", "3",
        "-m", "{'a': 1, 'b': 2}",
        "-md", "fast",
        "-cl", "RED",
        "--enabled",
    ])

    assert args.count == 5
    assert args.ratio == 1.5
    assert args.tags == [1, 2, 3]
    assert args.mapping == {"a": 1, "b": 2}
    assert args.mode == "fast"
    assert args.color == Color.RED
    assert args.enabled is True


def test_inverted_boolean_flag():
    class BoolModel(BaseModel):
        verbose: Annotated[bool, ArgumentField(default=True)]

    parser = ArgumentParser(BoolModel)

    default_args = parser.parse_typed_args([])
    no_verbose_args = parser.parse_typed_args(["--no-verbose"])

    assert default_args.verbose is True
    assert no_verbose_args.verbose is False

if __name__ == "__main__":
    test_basic_types_parsing()
    test_inverted_boolean_flag()