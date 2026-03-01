import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated
from argparse_dantic import ArgumentParser, BaseModel, CommandNameBind, ArgumentField, CommandField

def test_command():
    class CommandA(BaseModel):
        a_option: Annotated[str, ArgumentField(aliases=["-aopt"])]
    class CommandB(BaseModel):
        b_option: Annotated[str, ArgumentField(aliases=["-bopt"])]
    class MainModel(BaseModel):
        command_name: CommandNameBind
        commanda: Annotated[CommandA, CommandField(aliases=["a"])]
        commandb: Annotated[CommandB, CommandField(aliases=["b"])]
    
    parser = ArgumentParser(MainModel)
    a_args = parser.parse_typed_args([
        "commanda",
        "--a-option", "a_value"
    ])
    b_args = parser.parse_typed_args([
        "b",
        "-bopt", "b_value"
    ])
    assert a_args.command_name == "commanda"
    assert a_args.commanda.a_option == "a_value"
    assert a_args.commandb is None
    assert b_args.command_name == "commandb"
    assert b_args.commandb.b_option == "b_value"
    assert b_args.commanda is None

if __name__ == "__main__":
    test_command()