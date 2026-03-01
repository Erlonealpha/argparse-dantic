import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated
from argparse_dantic import ArgumentParser, BaseModel, ArgumentField, create_group
from argparse import ArgumentError

def test_group():
    A = create_group("A", "Group A")
    B = create_group("B", "Group B")
    class GroupA(BaseModel, group = A):
        group_a_arg: Annotated[str, ArgumentField("-aarg", help = "Group A argument")]
    class GroupB(BaseModel, group = B):
        group_b_arg: Annotated[str, ArgumentField("-barg", help = "Group B argument")]
    class MainModel(GroupA, GroupB):
        arg: Annotated[str, ArgumentField("-arg", help = "Main argument")]
    parser = ArgumentParser(model_class = MainModel)
    help = parser.format_help()
    assert "Group A" in help
    assert "Group B" in help

def test_mutually_exclusive_group():
    A = create_group("A", "Group A")
    B = create_group("M", "Mutually exclusive group B").create_mutually_exclusive_group()
    C = create_group("C", "Mutually exclusive group C").create_mutually_exclusive_group(True)
    class GroupA(BaseModel, group = A):
        group_a_arg: Annotated[str, ArgumentField("-aarg", help = "Group A argument")]
    class GroupB(BaseModel, group = B):
        b1: Annotated[bool, ArgumentField(default=False, description="Mutually exclusive B option 1")]
        b2: Annotated[bool, ArgumentField(default=False, description="Mutually exclusive B option 2")]
    class GroupC(BaseModel, group = C):
        c1: Annotated[bool, ArgumentField(default=False, description="Mutually exclusive C option 1")]
        c2: Annotated[bool, ArgumentField(default=False, description="Mutually exclusive C option 2")]
    class MainModel(GroupA, GroupB, GroupC):
        arg: Annotated[str, ArgumentField("-arg", help = "Main argument")]
    parser = ArgumentParser(model_class = MainModel, exit_on_error=False)
    try:
        parser.parse_typed_args([
            "-arg", "arg_value",
            "-aarg", "aarg_value",
            "--b1", "--b2", "--c1"
        ])
        assert False, "Should have raised an exception of type ArgumentError"
    except ArgumentError:
        pass
    try:
        parser.parse_typed_args([
            "-arg", "arg_value",
            "-aarg", "aarg_value",
            "--b1",
        ])
        assert False, "Should have raised an exception of type ArgumentError"
    except ArgumentError:
        pass
    args = parser.parse_typed_args([
        "-arg", "arg_value",
        "-aarg", "aarg_value",
        "--b1", "--c2"
    ])
    assert args.b1 is True
    assert args.b2 is False
    assert args.c1 is False
    assert args.c2 is True
    assert args.arg == "arg_value"
    assert args.group_a_arg == "aarg_value"

if __name__ == "__main__":
    test_group()
    test_mutually_exclusive_group()