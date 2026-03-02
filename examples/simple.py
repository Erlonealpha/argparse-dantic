import sys
import os
sys.path.append(os.getcwd())
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
