import os
import sys
from typing import Annotated

sys.path.append(os.getcwd())

from argparse_dantic import (
    ArgumentParser,
    BaseModel,
    CommandNameBind,
    ArgumentField,
    CommandField,
)


def test_global_data_collects_default_and_runtime_values():
    class GlobalModel(BaseModel):
        command_name: CommandNameBind
        global_arg_1: Annotated[str, ArgumentField("-g1", default="global_default", global_=True)]
        global_arg_2: Annotated[bool, ArgumentField("--g2", default=False, global_=True)]

    class SubA(GlobalModel):
        option_a: Annotated[str, ArgumentField("-oa", required=True)]

    class MainModel(GlobalModel):
        sub_a: Annotated[SubA, CommandField(aliases=["sa"])]

    old_global_data = dict(MainModel.global_data)
    try:
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
    finally:
        MainModel.global_data.clear()
        MainModel.global_data.update(old_global_data)
