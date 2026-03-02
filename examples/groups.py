import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated
from argparse_dantic import (
    ArgumentParser, BaseModel, ArgumentField,
    create_group
)

Group = create_group("Group", "This is a group")
MutuallyExclusiveGroup =    create_group("MutuallyExclusiveGroup", "This is a mutually exclusive group"). \
                            create_mutually_exclusive_group()

class GroupModel(BaseModel, group=Group):
    group_option_a: Annotated[str, ArgumentField("--group-option-a", help="This is a group option a")]
    group_option_b: Annotated[str, ArgumentField("--group-option-b", help="This is a group option b")]

class MutuallyExclusiveModel(BaseModel, group=MutuallyExclusiveGroup):
    verbose: Annotated[bool, ArgumentField("-v", "--verbose", help="Enable verbose mode")]
    quiet: Annotated[bool, ArgumentField("-q", "--quiet", help="Enable quiet mode")]

class MainModel(GroupModel, MutuallyExclusiveModel):
    option_a: Annotated[str, ArgumentField("-a", "--option-a", help="This is an option a")]
    option_b: Annotated[str, ArgumentField("-b", "--option-b", help="This is an option b")]

if __name__ == "__main__":
    parser = ArgumentParser(
        model_class=MainModel,
        prog="example_groups",
        description="Example of using groups in argparse-dantic"
    )
    args = ["-h"]
    arguments = parser.parse_typed_args(args)
    print(arguments)