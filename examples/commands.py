"""Commands Example."""
import sys
import os
sys.path.append(os.getcwd())
from argparse_dantic import (
    ArgumentParser, BaseModel, CommandNameBind, ArgumentField, CommandField,
    FilePath, IPvAnyAddress
)

from typing import Optional, Annotated

class MyBaseModel(BaseModel):
    action_name: CommandNameBind

class BuildCommand(MyBaseModel):
    """Build Command Arguments."""

    # Required Args
    location: Annotated[FilePath, ArgumentField("-loc", "--loc", description="build location")]


class ServeCommand(MyBaseModel):
    """Serve Command Arguments."""

    # Required Args
    address: IPvAnyAddress = ArgumentField(description="serve address")
    port: int = ArgumentField(description="serve port")


class Arguments(MyBaseModel):
    """Command-Line Arguments."""

    # Optional Args
    verbose: bool = ArgumentField("-verb", "--verb", default=False, description="verbose flag")

    # Commands
    build: Optional[BuildCommand] = CommandField(description="build command")
    serve: Optional[ServeCommand] = CommandField(description="serve command")

def test_build(args: BuildCommand):
    ...

def commands(args: Arguments):
    ...

def main() -> None:
    """Main Function."""
    # Create Parser and Parse Args
    parser = ArgumentParser(
        model_class=Arguments,
        prog="Example Program",
        description="Example Description",
        version="0.0.1",
        epilog="Example Epilog",
    )
    args = parser.parse_typed_args()

    # Print Args
    print(args)


if __name__ == "__main__":
    main()
