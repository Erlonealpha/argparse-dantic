import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated, Optional, Union

from argparse_dantic import ArgumentParser, BaseModel, ArgumentField, ModelField

class LoggingModel(BaseModel):
    level: Annotated[int, ArgumentField(
        "l",
        default=10,
    )]
    format: Annotated[str, ArgumentField(
        "f",
        default="%(asctime)s %(levelname)s %(message)s",
    )]

class MainModel(BaseModel):
    config_file: Annotated[Optional[str], ArgumentField("config", default="config.json")]
    pad: Annotated[Union[int, float], ArgumentField(default=1.0)]
    logging: Annotated[LoggingModel, ModelField(connect_char=".")]

if __name__ == "__main__":
    parser = ArgumentParser(
        MainModel,
        prog="example_option_group",
        description="Example of option group"
    )

    args = ["--pad", "30", "--logging.level", "20", "--logging.format", "custom format"]
    # args = ["-h"]

    arguments = parser.parse_typed_args(args)
    print("Level: ", arguments.logging.level)
    print("Format: ", arguments.logging.format)
