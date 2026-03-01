from typing import Literal
from rich import print
from rich.pretty import pprint
import sys
import os
sys.path.append(os.getcwd())

from argparse_dantic import ArgumentParser, CommandNameBind, BaseModel, Field, CommandField

class GlobalModel(BaseModel):
    command_name: CommandNameBind
    global_arg_1: str = Field(aliases=["-g1"], default="global_arg_1", global_=True)
    global_2: bool = Field(aliases=["--g2"], default=False, global_=True)

class SomePubOptions(BaseModel):
    option_p1: str = Field(aliases=["-op1"], default="option_p1")
    option_p2: bool = Field(aliases=["--op2"], default=False)

class SubAModel(GlobalModel, SomePubOptions):
    option_1: str = Field(aliases=["-o1"], default="option_1", required=True)
    option_2: bool = Field(aliases=["--o2"], default=False)

class SubBModel(GlobalModel, SomePubOptions):
    option_a: str = Field(aliases=["-oa"], default="option_a")
    literal_option: Literal["a", "b", "c"] = Field(aliases=["-lo"], default="a")

class MainModel(GlobalModel):
    sub_a: SubAModel = CommandField(aliases=["sa"], description="Sub A Command")
    sub_b: SubBModel = CommandField(aliases=["sb"], description="Sub B Command")

class CommandException(Exception):
        pass
class Commands:
    def __init__(self):
        self.commands = {}
    
    def register(
        self, 
        name = None,
        parent = None,
        model_class= None
    ):
        def decorator(func):
            nonlocal name
            setattr(func, "__model_class__", model_class)
            if name is None:
                name = func.__name__
            if parent is not None:
                name = f"{parent}.{name}"
            self.commands[name] = func
            return func
        return decorator
    
    def __call__(self, reg_name: str, parent = None):
        if parent is not None:
            reg_name = f"{parent}.{reg_name}"
        fn = self.commands.get(reg_name)
        if fn is None:
            raise CommandException(f"Command {reg_name} not found")
        return fn

commands = Commands()

@commands.register(model_class=SubAModel)
def sub_a(arguments: SubAModel):
    print("Sub A Command")

@commands.register(model_class=SubBModel)
def sub_b(arguments: SubBModel):
    print("Sub B Command")

def main():
    parser = ArgumentParser(
        MainModel,
        prog="example_app",
        description="Example ArgParseDantic Application",
    )
    args = [
        "--g2",
        "sa",
        "-o1", "option_1_value",
        "-g1", "global_arg_1_value"
    ]
    args = ["-h"]
    arguments = parser.parse_typed_args(args)

    _ = arguments.global_data.get("global_arg_1") # Access global data from the arguments object
    _ = arguments.global_data.get("global_2")

    commands(arguments.command_name)(getattr(arguments, arguments.command_name))
    print()
    pprint(arguments)


if __name__ == "__main__":
    main()