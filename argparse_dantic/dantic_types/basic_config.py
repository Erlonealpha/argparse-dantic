from typing import TypedDict

try:
    from typing import Unpack
except ImportError:  # pragma: no cover - Python < 3.11
    from typing_extensions import Unpack

__DefaultConfig = {
    "hyphenate_dest": True,
    "metavar_default": "empty",
    "connect_char": ".",
    "dest_prefix": "--",
    "aliases_prefix": "--",
    "prefix_chars": "-",
    "add_help": True,
    "exit_on_error": True,
}

_DefaultConfig = __DefaultConfig.copy()

class ConfigDict(TypedDict, total=False):
    hyphenate_dest: bool
    metavar_default: str
    connect_char: str
    dest_prefix: str
    aliases_prefix: str
    prefix_chars: str
    add_help: bool
    exit_on_error: bool

def set_basic_config(**kwargs: Unpack[ConfigDict]):
    conf = ConfigDict(**kwargs)
    _DefaultConfig.update(conf)

def reset_basic_config():
    _DefaultConfig.update(__DefaultConfig)
