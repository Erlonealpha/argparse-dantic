import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated, Any, TypedDict, Literal
from argparse_dantic import (
    BaseModel, ArgumentParser, CommandNameBind, 
    ArgumentField, CommandField, ModelField,
    create_group
)

type LogLevels = Literal["debug", "info", "warning", "error", "critical"]

class GlobalData(TypedDict):
    verbose: bool
    quiet: bool
    logging: "LoggingModel"

MGroup =    create_group("Mutually Exclusive Group", "Mutually Exclusive Group Description").\
            create_mutually_exclusive_group(required=False)
class MutuallyGroup(BaseModel, group=MGroup):
    verbose: Annotated[bool, ArgumentField(default=False, description="Verbose Mode")]
    quiet: Annotated[bool, ArgumentField(default=False, description="Quiet Mode")]

class LoggingModel(BaseModel):
    level: Annotated[LogLevels, ArgumentField("l", default="info", description="Logging Level", env="ARGPARSE_DANTIC_TEST_LOG_LEVEL")]
    file: Annotated[str, ArgumentField("f", default="app.log", metavar="FILE", description="Log File", env="ARGPARSE_DANTIC_TEST_LOG_FILE")]

class GlobalModel(MutuallyGroup):
    global_data: GlobalData
    logging: Annotated[LoggingModel, ModelField(connect_char=".")]

class BaseCommandModel(GlobalModel):
    command_name: CommandNameBind

class BuildCommand(GlobalModel):
    name: Annotated[str, ArgumentField(description="Project Name")]
    version: Annotated[str, ArgumentField(description="Project Version")]

class ListToolsCommand(GlobalModel):
    ...
class ListInstallCommand(GlobalModel):
    ...
class ListCommand(BaseCommandModel):
    tools: Annotated[ListToolsCommand, CommandField(description="List Tools Command")]
    install: Annotated[ListInstallCommand, CommandField(description="List Install Command")]

class MainModel(BaseCommandModel):
    build: Annotated[BuildCommand, CommandField(aliases=["bd"], description="Build Command")]
    list: Annotated[ListCommand, CommandField(aliases=["ls"], description="Check Command")]

class Commands:
    def __init__(self):
        self.commands = {}
    def register(self, name = None, parent = None):
        def decorator(func):
            nonlocal name
            if name is None:
                name = func.__name__
            if parent is not None:
                name = f"{parent}.{name}"
            self.commands[name] = func
            return func
        return decorator
    def __call__(self, name, parent = None) -> Any:
        if parent:
            name = f"{parent}.{name}"
        return self.commands[name]

commands = Commands()

@commands.register()
def build(arguments: BuildCommand):
    print(f"Building {arguments.name} version {arguments.version}")
@commands.register(name="list")
def list_(arguments: ListCommand):
    commands(arguments.command_name, "list")(getattr(arguments, arguments.command_name))
@commands.register(parent="list")
def tools(arguments: ListToolsCommand):
    print("List of tools")
@commands.register(parent="list")
def install(arguments: ListInstallCommand):
    print("List of installed binaries")

if __name__ == "__main__":
    parser = ArgumentParser(
        model_class=MainModel,
        prog="Advanced Example",
        description="Advanced Example Description",
        version="1.0.0"
    )
    args = ["build", "--name", "MyProject", "--logging.level", "error", "--quiet"]
    # args = ["list", "tools"]
    args = ["-h"]
    arguments = parser.parse_typed_args(args)
    parser.console.print("Global Data:")
    parser.console.print("\tverbose:", arguments.global_data["verbose"])
    parser.console.print("\tquiet:", arguments.global_data["quiet"])
    parser.console.print("Logging Config:")
    parser.console.print("\tlevel:", arguments.global_data["logging"].level)
    parser.console.print("\tfile:", arguments.global_data["logging"].file)
    try:
        commands(arguments.command_name)(getattr(arguments, arguments.command_name))
    except KeyError:
        if arguments.command_name is None:
            parser.console.print("No command specified")
        else:
            parser.console.print(f"Command {arguments.command_name} not found")