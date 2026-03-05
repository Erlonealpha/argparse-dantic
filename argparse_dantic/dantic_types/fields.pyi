import re
import sys
import typing
import annotated_types
import dataclasses

from typing_extensions import TypeAlias, Unpack, deprecated, TypedDict
from pydantic_core import PydanticUndefined
from pydantic.fields import FieldInfo as PydanticFieldInfo, _EmptyKwargs, _Unset
from typing_inspection.introspection import AnnotationSource
from types import EllipsisType

from pydantic import types
from pydantic.aliases import AliasChoices, AliasPath
from pydantic.config import JsonDict
from .groups import _Group, _MutuallyExclusiveGroup


if sys.version_info >= (3, 13):
    import warnings

    Deprecated: TypeAlias = warnings.deprecated | deprecated
else:
    Deprecated: TypeAlias = deprecated

class FieldTypes:
    ARGUMENT = 'argument'
    MODEL = 'model'
    SUBCOMMAND = 'subcommand'

_FIELD_TYPE = typing.Literal['argument', 'model','subcommand']
_GROUP_TYPE = typing.Union[_Group, _MutuallyExclusiveGroup]
_METAVAR_DEFAULT_TYPE = typing.Literal['empty', 'upper', 'notset']

class _FromFieldInfoInputs(TypedDict, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.from_field`."""

    # TODO PEP 747: use TypeForm:
    annotation: type[typing.Any] | None
    default_factory: typing.Callable[[], typing.Any] | typing.Callable[[dict[str, typing.Any]], typing.Any] | None
    alias: str | None
    alias_priority: int | None
    validation_alias: str | AliasPath | AliasChoices | None
    serialization_alias: str | None
    title: str | None
    field_title_generator: typing.Callable[[str, "FieldInfo"], str] | None
    description: str | None
    examples: list[typing.Any] | None
    exclude: bool | None
    exclude_if: typing.Callable[[typing.Any], bool] | None
    gt: annotated_types.SupportsGt | None
    ge: annotated_types.SupportsGe | None
    lt: annotated_types.SupportsLt | None
    le: annotated_types.SupportsLe | None
    multiple_of: float | None
    strict: bool | None
    min_length: int | None
    max_length: int | None
    pattern: str | re.Pattern[str] | None
    allow_inf_nan: bool | None
    max_digits: int | None
    decimal_places: int | None
    union_mode: typing.Literal['smart', 'left_to_right'] | None
    discriminator: str | types.Discriminator | None
    deprecated: Deprecated | str | bool | None
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
    frozen: bool | None
    validate_default: bool | None
    repr: bool
    init: bool | None
    init_var: bool | None
    kw_only: bool | None
    coerce_numbers_to_str: bool | None
    fail_fast: bool | None

    dest: str | None
    group: _GROUP_TYPE | None
    dest_prefix: str
    aliases_prefix: str
    hyphenate_dest: bool

    aliases: list[str] | None
    allow_none: bool | None

    help: str | None
    env: str | None
    required: bool | None
    metavar: str | None
    metavar_default: _METAVAR_DEFAULT_TYPE

    prog: str | None
    usage: str | None
    description: str | None
    epilog: str | None
    prefix_chars: str | None
    add_help: bool | None
    exit_on_error: bool | None
    version: str | None

    connect_char: str | None

    _field_type: _FIELD_TYPE | None

class ArgumentFieldInfo(typing.NamedTuple):
    aliases: list[str]
    help: str | None
    required: bool
    allow_none: bool
    metavar: str | None
    metavar_default: _METAVAR_DEFAULT_TYPE
    env: str | None

class CommandFieldInfo(typing.NamedTuple):
    aliases: list[str]
    prog: str | None
    usage: str | None
    help: str | None
    description: str | None
    version: str | None
    epilog: str | None
    prefix_chars: str | None
    add_help: bool
    exit_on_error: bool

class ModelFieldInfo(typing.NamedTuple):
    aliases: list[str]
    connect_char: str

class FieldInfo(PydanticFieldInfo): # type: ignore

    dest: str | None
    aliases: list[str]
    dest_prefix: str
    aliases_prefix: str
    hyphenate_dest: bool
    group: _GROUP_TYPE | None
    argument_fields: ArgumentFieldInfo
    command_fields: CommandFieldInfo
    model_fields: ModelFieldInfo
    global_: bool

    __slots__ = (
        'annotation',
        'default',
        'default_factory',
        'alias',
        'alias_priority',
        'validation_alias',
        'serialization_alias',
        'title',
        'field_title_generator',
        'description',
        'examples',
        'exclude',
        'exclude_if',
        'discriminator',
        'deprecated',
        'json_schema_extra',
        'frozen',
        'validate_default',
        'repr',
        'init',
        'init_var',
        'kw_only',
        'metadata',
        'dest',
        'aliases',
        'dest_prefix',
        'aliases_prefix',
        'hyphenate_dest',
        'group',
        'argument_fields',
        'command_fields',
        'model_fields',
        'global_',
        '_attributes_set',
        '_qualifiers',
        '_complete',
        '_original_assignment',
        '_original_annotation',
        '_final',
        '_field_type'
    )

    def __init__(self, default: typing.Any = _Unset, **kwargs): ...

    @staticmethod
    def from_field(default: typing.Any = PydanticUndefined, **kwargs: Unpack[_FromFieldInfoInputs]) -> "FieldInfo": # type: ignore
        ...

    @staticmethod
    def from_annotation(
        annotation: typing.Any, 
        *, _source: AnnotationSource = AnnotationSource.ANY,
        **kwargs,
    ) -> "FieldInfo":
        ...
    
    @staticmethod
    def from_annotated_attribute(
        annotation: type[typing.Any], 
        default: typing.Any, *, 
        _source: AnnotationSource = AnnotationSource.ANY,
        **kwargs,
    ) -> "FieldInfo":
        ...
    
    @staticmethod
    def merge_field_infos(*field_infos: "FieldInfo", **overrides: typing.Any) -> "FieldInfo": # type: ignore
        ...
    
    @staticmethod
    def _from_dataclass_field(dc_field: dataclasses.Field[typing.Any], **kwargs) -> "FieldInfo":
        ...

_T = typing.TypeVar('_T')

# NOTE: Actual return type is 'FieldInfo', but we want to help type checkers
# to understand the magic that happens at runtime with the following overloads:
@typing.overload  # type hint the return value as `Any` to avoid type checking regressions when using `...`.
def Field(
    default: EllipsisType,
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any: ...
@typing.overload  # `default` argument set, validate_default=True (no type checking on the default value)
def Field(
    default: typing.Any,
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: typing.Literal[True],
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any: ...
@typing.overload  # `default` argument set, validate_default=False or unset
def Field(
    default: _T,
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    # NOTE: to get proper type checking on `exclude_if`'s argument, we could use `_T` instead of `Any`. However,
    # this requires (at least for pyright) adding an additional overload where `exclude_if` is required (otherwise
    # `a: int = Field(default_factory=str)` results in a false negative).
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: typing.Literal[False] = ...,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@typing.overload  # `default_factory` argument set, validate_default=True  (no type checking on the default value)
def Field(  # pyright: ignore[reportOverlappingOverload]
    *,
    default_factory: typing.Callable[[], typing.Any] | typing.Callable[[dict[str, typing.Any]], typing.Any],
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: typing.Literal[True],
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any: ...
@typing.overload  # `default_factory` argument set, validate_default=False or unset
def Field(
    *,
    default_factory: typing.Callable[[], _T] | typing.Callable[[dict[str, typing.Any]], _T],
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    # NOTE: to get proper type checking on `exclude_if`'s argument, we could use `_T` instead of `Any`. However,
    # this requires (at least for pyright) adding an additional overload where `exclude_if` is required (otherwise
    # `a: int = Field(default_factory=str)` results in a false negative).
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: typing.Literal[False] | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@typing.overload
def Field(  # No default set
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any: ...
def Field(  # noqa: C901
    default: typing.Any = PydanticUndefined,
    *,
    default_factory: typing.Callable[[], typing.Any] | typing.Callable[[dict[str, typing.Any]], typing.Any] | None = _Unset,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    exclude: bool | None = _Unset,
    exclude_if: typing.Callable[[typing.Any], bool] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | re.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: typing.Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    allow_none: bool | None = _Unset,
    help: str | None = _Unset,
    env: str | None = _Unset,
    required: bool | None = _Unset,
    metavar: str | None = _Unset,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    connect_char: str | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    """!!! abstract "Usage Documentation"
        [Fields](../concepts/fields.md)

    Create a field for objects that can be configured.

    Used to provide extra information about a field, either for the model schema or complex validation. Some arguments
    apply only to number fields (`int`, `float`, `Decimal`) and some apply only to `str`.

    Note:
        - Any `_Unset` objects will be replaced by the corresponding value defined in the `_DefaultValues` dictionary. If a key for the `_Unset` object is not found in the `_DefaultValues` dictionary, it will default to `None`

    Args:
        default: Default value if the field is not set.
        default_factory: A callable to generate the default value. The callable can either take 0 arguments
            (in which case it is called as is) or a single argument containing the already validated data.
        alias: The name to use for the attribute when validating or serializing by alias.
            This is often used for things like converting between snake and camel case.
        alias_priority: Priority of the alias. This affects whether an alias generator is used.
        validation_alias: Like `alias`, but only affects validation, not serialization.
        serialization_alias: Like `alias`, but only affects serialization, not validation.
        title: Human-readable title.
        field_title_generator: A callable that takes a field name and returns title for it.
        description: Human-readable description.
        examples: Example values for this field.
        exclude: Whether to exclude the field from the model serialization.
        exclude_if: A callable that determines whether to exclude a field during serialization based on its value.
        discriminator: Field name or Discriminator for discriminating the type in a tagged union.
        deprecated: A deprecation message, an instance of `warnings.deprecated` or the `typing_extensions.deprecated` backport,
            or a boolean. If `True`, a default deprecation message will be emitted when accessing the field.
        json_schema_extra: A dict or callable to provide extra JSON schema properties.
        frozen: Whether the field is frozen. If true, attempts to change the value on an instance will raise an error.
        validate_default: If `True`, apply validation to the default value every time you create an instance.
            Otherwise, for performance reasons, the default value of the field is trusted and not validated.
        repr: A boolean indicating whether to include the field in the `__repr__` output.
        init: Whether the field should be included in the constructor of the dataclass.
            (Only applies to dataclasses.)
        init_var: Whether the field should _only_ be included in the constructor of the dataclass.
            (Only applies to dataclasses.)
        kw_only: Whether the field should be a keyword-only argument in the constructor of the dataclass.
            (Only applies to dataclasses.)
        coerce_numbers_to_str: Whether to enable coercion of any `Number` type to `str` (not applicable in `strict` mode).
        strict: If `True`, strict validation is applied to the field.
            See [Strict Mode](../concepts/strict_mode.md) for details.
        gt: Greater than. If set, value must be greater than this. Only applicable to numbers.
        ge: Greater than or equal. If set, value must be greater than or equal to this. Only applicable to numbers.
        lt: Less than. If set, value must be less than this. Only applicable to numbers.
        le: Less than or equal. If set, value must be less than or equal to this. Only applicable to numbers.
        multiple_of: Value must be a multiple of this. Only applicable to numbers.
        min_length: Minimum length for iterables.
        max_length: Maximum length for iterables.
        pattern: Pattern for strings (a regular expression).
        allow_inf_nan: Allow `inf`, `-inf`, `nan`. Only applicable to float and [`Decimal`][decimal.Decimal] numbers.
        max_digits: Maximum number of allow digits for strings.
        decimal_places: Maximum number of decimal places allowed for numbers.
        union_mode: The strategy to apply when validating a union. Can be `smart` (the default), or `left_to_right`.
            See [Union Mode](../concepts/unions.md#union-modes) for details.
        fail_fast: If `True`, validation will stop on the first error. If `False`, all validation errors will be collected.
            This option can be applied only to iterable types (list, tuple, set, and frozenset).
        extra: (Deprecated) Extra fields that will be included in the JSON schema.

            !!! warning Deprecated
                The `extra` kwargs is deprecated. Use `json_schema_extra` instead.

    Returns:
        A new [`FieldInfo`][pydantic.fields.FieldInfo]. The return annotation is `Any` so `Field` can be used on
            type-annotated fields without causing a type error.
    """
    ...

def ArgumentField(
    *names: typing.Any,
    default: typing.Any = PydanticUndefined,
    aliases: list[str] | None = [],
    allow_none: bool | None = False,
    help: str | None = None,
    env: str | None = None,
    required: bool | None = False,
    metavar: str | None = None,
    metavar_default: typing.Literal['empty', 'notset', 'upper'] = "empty",
    default_factory: typing.Callable[[], typing.Any] | typing.Callable[[dict[str, typing.Any]], typing.Any] | None = None,
    alias: str | None = None,
    alias_priority: int | None = None,
    validation_alias: str | AliasPath | AliasChoices | None = None,
    serialization_alias: str | None = None,
    title: str | None = None,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = None,
    description: str | None = None,
    examples: list[typing.Any] | None = None,
    discriminator: str | types.Discriminator | None = None,
    deprecated: Deprecated | str | bool | None = None,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = None,
    frozen: bool | None = None,
    validate_default: bool | None = None,
    pattern: str | typing.Pattern[str] | None = None,
    strict: bool | None = None,
    coerce_numbers_to_str: bool | None = None,
    gt: annotated_types.SupportsGt | None = None,
    ge: annotated_types.SupportsGe | None = None,
    lt: annotated_types.SupportsLt | None = None,
    le: annotated_types.SupportsLe | None = None,
    multiple_of: float | None = None,
    allow_inf_nan: bool | None = None,
    max_digits: int | None = None,
    decimal_places: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    union_mode: typing.Literal['smart', 'left_to_right'] = "smart",
    fail_fast: bool | None = None,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    ...

def CommandField(
    aliases: list[str] | None = [],
    prog: str | None = None,
    usage: str | None = None,
    epilog: str | None = None,
    prefix_chars: str | None = "-",
    add_help: bool | None = True,
    exit_on_error: bool | None = True,
    version: str | None = None,
    help: str | None = None,
    title: str | None = None,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = None,
    description: str | None = None,
    deprecated: Deprecated | str | bool | None = None,
    fail_fast: bool | None = None,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    ...

def ModelField(
    aliases: list[str] | None = [],
    connect_char: str | None = ".",
    fail_fast: bool | None = None,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    ...