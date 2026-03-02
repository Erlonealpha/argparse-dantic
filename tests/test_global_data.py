import os
import sys
from typing import Annotated, TypedDict

sys.path.append(os.getcwd())

from argparse_dantic import (
    ArgumentParser,
    BaseModel,
    CommandNameBind,
    ArgumentField,
    CommandField,
)

class GlobalData(TypedDict):
    global_arg_1: str
    global_arg_2: bool

def test_global_data_collects_default_and_runtime_values():
    class GlobalModel(BaseModel):
        global_data: GlobalData
        command_name: CommandNameBind
        global_arg_1: Annotated[str, ArgumentField("-g1", default="global_default")]
        global_arg_2: Annotated[bool, ArgumentField("--g2", default=False)]

    class SubA(GlobalModel):
        option_a: Annotated[str, ArgumentField("-oa", required=True)]

    class MainModel(GlobalModel):
        sub_a: Annotated[SubA, CommandField(aliases=["sa"])]

    parser = ArgumentParser(MainModel)

    assert MainModel.global_data.get("global_arg_1") == "global_default"
    assert MainModel.global_data.get("global_arg_2") is False

    args = parser.parse_typed_args([
        "--g2",
        "sa",
        "-oa", "value_a",
        "-g1", "global_runtime",
    ])

    assert args.command_name == "sub_a"
    assert args.sub_a.option_a == "value_a"

    # Runtime value from sub command should be reflected in global data
    assert MainModel.global_data.get("global_arg_1") == "global_runtime"
    assert MainModel.global_data.get("global_arg_2") is True

if __name__ == "__main__":
    test_global_data_collects_default_and_runtime_values()