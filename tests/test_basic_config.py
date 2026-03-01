import sys
import os
sys.path.append(os.getcwd())
from typing import Annotated
from argparse import ArgumentError
from argparse_dantic import ArgumentParser, BaseModel, ArgumentField, set_basic_config, reset_basic_config

def test_basic_config():
    try:
        set_basic_config(dest_prefix="-", aliases_prefix="-", exit_on_error=False)

        class MainModel(BaseModel):
            name: Annotated[str, ArgumentField("n", description="name of the program")]
            verbose: Annotated[bool, ArgumentField("v", description="verbose mode")]

        parser = ArgumentParser(model_class=MainModel)
        parser.parse_typed_args([
            "-n", "name",
            "-v"
        ])
        try:
            parser.parse_typed_args([
                "--name", "name",
                "--verbose"
            ])
            assert False, "should raise ArgumentError"
        except ArgumentError:
            pass
        try:
            parser.parse_typed_args([
                "--n", "name",
                "--v"
            ])
            assert False, "Should raise ArgumentError"
        except ArgumentError:
            pass
    finally:
        reset_basic_config() # !! Reset the config to default, othewise other tests will fail

if __name__ == "__main__":
    test_basic_config()