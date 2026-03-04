<div align="center">
<!-- Logo -->
<a><img src="https://raw.githubusercontent.com/SupImDos/pydantic-argparse/master/docs/assets/images/logo.svg" width="50%"></a>
<!-- Headings -->
<h1>Argparse Dantic</h1>
<p><em>Typed Argument Parsing with Pydantic Enhanced</em></p>
<!-- Badges (Row 1) -->
<a href="https://pypi.python.org/pypi/argparse-dantic"><img src="https://img.shields.io/pypi/v/argparse-dantic"></a>
<a href="https://pepy.tech/project/argparse-dantic"><img src="https://img.shields.io/pepy/dt/argparse-dantic?color=blue"></a>
<a href="https://github.com/ErloneAlpha/argparse-dantic/blob/master/LICENSE"><img src="https://img.shields.io/github/license/ErloneAlpha/argparse-dantic"></a>
<br>
</div>

## Requirements
Requires Python 3.10+, and is compatible with the Pydantic library.
Use Rich for better console output.

## Installation
Installation with `pip` is simple:
```console
$ pip install argparse-dantic
```

## Example
```py
from argparse_dantic import ArgumentParser, BaseModel, ArgumentField

class Arguments(BaseModel):
    """Simple Command-Line Arguments."""

    # Required Args
    string: str = ArgumentField("-s", description="a required string")
    integer: int = ArgumentField("-i", description="a required integer")
    flag: bool = ArgumentField("-f", description="a required flag")

    # Optional Args
    second_flag: bool = ArgumentField("-sec", default=False, description="an optional flag")
    third_flag: bool = ArgumentField("-thi", default=True, description="an optional flag")

def main() -> None:
    """Simple Main Function."""
    # Create Parser and Parse Args
    parser = ArgumentParser(
        model_class=Arguments,
        prog="Example Program",
        description="Example Description",
        version="0.0.1",
        epilog="Example Epilog",
    )
    args = ["-h"]
    arguments = parser.parse_typed_args(args)

    # Print Args
    print(arguments)

if __name__ == "__main__":
    main()
```

```console
$ python3 example.py --help
Example Description

Usage: Example Program [-h] [-v] [--s STRING] [--i INTEGER] [--f] [--sec] [--no-thi]

Optional Arguments:
  -s, --string STRING   a required string (default: None)
  -i, --integer INTEGER
                        a required integer (default: None)
  -f, --flag            a required flag (default: None)
  -sec, --second-flag   an optional flag (default: False)
  -no-thi, --no-third-flag
                        an optional flag (default: True)

Help:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

Example Epilog
```

```console
$ python3 example.py --string hello -i 42 -f
string='hello' integer=42 flag=True second_flag=False third_flag=True
```

## Advanced Example
```py
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
    file: Annotated[str, ArgumentField("f", default="app.log", description="Log File", env="ARGPARSE_DANTIC_TEST_LOG_FILE")]

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
```

## License
This project is licensed under the terms of the MIT license.
