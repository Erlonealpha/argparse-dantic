import re
import sys
import typing
import annotated_types
import dataclasses

from warnings import warn
from typing_extensions import TypeAlias, Unpack, deprecated, TypedDict
from typing_inspection import typing_objects
from pydantic_core import PydanticUndefined
from pydantic.fields import FieldInfo as PydanticFieldInfo, _EmptyKwargs, _FIELD_ARG_NAMES, _Unset
from typing_inspection.introspection import UNKNOWN, AnnotationSource, ForbiddenQualifier, inspect_annotation
from types import EllipsisType

from pydantic import types
from pydantic.aliases import AliasChoices, AliasPath
from pydantic.config import JsonDict
from pydantic.errors import PydanticForbiddenQualifier, PydanticUserError
from pydantic.warnings import PydanticDeprecatedSince20
from pydantic.json_schema import PydanticJsonSchemaWarning

from .basic_config import _DefaultConfig
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
    include_dest_in_names: bool

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

_DefaultValues = {
    "dest": None,
    "group": None,
    "aliases": [],
    "help": None,
    "description": None,
    "required": False,
    "allow_none": False,
    "metavar": None,
    "env": None,
    "prog": None,
    "usage": None,
    "epilog": None,
    "version": None,
}

def get_default_value(key: str):
    if key in _DefaultValues:
        return _DefaultValues[key]
    return _DefaultConfig.get(key)

class ArgumentFieldInfo(typing.NamedTuple):
    aliases: list[str]
    help: str | None
    required: bool
    allow_none: bool
    metavar: str | None
    metavar_default: str
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
        'include_dest_in_names',
        'group',
        'argument_fields',
        'command_fields',
        'model_fields',
        '_attributes_set',
        '_qualifiers',
        '_complete',
        '_original_assignment',
        '_original_annotation',
        '_final',
        '_field_type'
        '_global',
    )

    def __init__(self, default: typing.Any = _Unset, **kwargs):
        _attributes_set = {k: v for k, v in kwargs.items() if v is not _Unset}
        kwargs = {k: get_default_value(k) if v is _Unset else v for k, v in kwargs.items()}

        _argument_fields = None
        _command_fields = None
        _model_fields = None
        _field_type =       typing.cast(_FIELD_TYPE,        kwargs.pop('_field_type',    None))
        if _field_type is None:
            if (ann := kwargs.get("annotation")) is not None:
                from ._import_utils import import_cached_base_model
                if isinstance(typing.get_origin(ann) or ann, import_cached_base_model()):
                    # If the annotation is a BaseModel and `_field_type` is not set,
                    # Default to subcommand type.
                    _field_type = FieldTypes.SUBCOMMAND
            if _field_type is None:
                # Default to argument type.
                _field_type: _FIELD_TYPE = FieldTypes.ARGUMENT
        g = get_default_value
        dest =                  typing.cast(str | None,            kwargs.pop('dest',            g('dest')))
        group =                 typing.cast(_GROUP_TYPE | None,    kwargs.pop('group',           g('group')))
        aliases =               typing.cast(list[str],             kwargs.pop('aliases',         g('aliases')))
        dest_prefix =           typing.cast(str | None,            kwargs.pop('dest_prefix',     g('dest_prefix')))
        aliases_prefix =        typing.cast(str | None,            kwargs.pop('aliases_prefix',  g('aliases_prefix')))
        hyphenate_dest =        typing.cast(bool,                  kwargs.pop('hyphenate_dest',  g('hyphenate_dest')))
        include_dest_in_names = typing.cast(bool,                  kwargs.pop('include_dest_in_names', g('include_dest_in_names')))
        if _field_type == FieldTypes.ARGUMENT:
            help =              typing.cast(str | None,            kwargs.pop('help',            g('help')))
            required =          typing.cast(bool,                  kwargs.pop('required',        g('required')))
            allow_none =        typing.cast(bool,                  kwargs.pop('allow_none',      g('allow_none')))
            metavar =           typing.cast(str | None,            kwargs.pop('metavar',         g('metavar')))
            metavar_default =   typing.cast(_METAVAR_DEFAULT_TYPE, kwargs.pop('metavar_default', g('metavar_default')))
            env =               typing.cast(str | None,            kwargs.pop('env',             g('env')))
            if not required and default is _Unset:
                # If the required is False, we want to set default to None, not _Unset.
                # That new pydantic will not raise missing value error.
                default = None
            _argument_fields = ArgumentFieldInfo(
                aliases=aliases,
                help=help,
                required=required,
                allow_none=allow_none,
                metavar=metavar,
                metavar_default=metavar_default,
                env=env,
            )
        elif _field_type == FieldTypes.SUBCOMMAND:
            default = None
            prog =              typing.cast(str | None,            kwargs.pop('prog',          g("prog")))
            usage =             typing.cast(str | None,            kwargs.pop('usage',         g("usage")))
            help =              typing.cast(str | None,            kwargs.pop('help',          g("help")))
            description =       typing.cast(str | None,            kwargs.get('description',   g("description")))
            epilog =            typing.cast(str | None,            kwargs.pop('epilog',        g("epilog")))
            prefix_chars =      typing.cast(str,                   kwargs.pop('prefix_chars',  g("prefix_chars")))
            add_help =          typing.cast(bool,                  kwargs.pop('add_help',      g("add_help")))
            exit_on_error =     typing.cast(bool,                  kwargs.pop('exit_on_error', g("exit_on_error")))
            version =           typing.cast(str | None,            kwargs.pop('version',       g("version")))
            _command_fields = CommandFieldInfo(
                aliases=aliases,
                prog=prog,
                usage=usage,
                help=help,
                description=description,
                version=version,
                epilog=epilog,
                prefix_chars=prefix_chars,
                add_help=add_help,
                exit_on_error=exit_on_error,
            )
        elif _field_type == FieldTypes.MODEL:
            connect_char =      typing.cast(str,                   kwargs.pop('connect_char',  g("connect_char")))
            _model_fields = ModelFieldInfo(
                aliases=aliases,
                connect_char=connect_char,
            )
        else:
            raise ValueError(f"Invalid field type {_field_type}")

        if not include_dest_in_names and not aliases:
            raise TypeError('Aliases must be provided if include_dest_in_names is False.')

        super().__init__(default=default, **kwargs) # type: ignore
        self._attributes_set.update(_attributes_set)

        self._field_type: _FIELD_TYPE = _field_type
        self.dest = dest
        self.group = group
        self.aliases = aliases
        self.dest_prefix = dest_prefix
        self.aliases_prefix = aliases_prefix
        self.hyphenate_dest = hyphenate_dest
        self.include_dest_in_names = include_dest_in_names
        self.argument_fields: "ArgumentFieldInfo | None" = _argument_fields
        self.command_fields: "CommandFieldInfo | None" = _command_fields
        self.model_fields: "ModelFieldInfo | None" = _model_fields
        self._global = False

    @staticmethod
    def from_field(default: typing.Any = PydanticUndefined, **kwargs: Unpack[_FromFieldInfoInputs]) -> "FieldInfo": # type: ignore
        if 'annotation' in kwargs:
            raise TypeError('"annotation" is not permitted as a Field keyword argument')
        return FieldInfo(default=default, **kwargs)

    @staticmethod
    def from_annotation(
        annotation: typing.Any, 
        *, _source: AnnotationSource = AnnotationSource.ANY,
        **kwargs,
    ) -> "FieldInfo":
        try:
            inspected_ann = inspect_annotation(
                annotation,
                annotation_source=_source,
                unpack_type_aliases='skip',
            )
        except ForbiddenQualifier as e:
            raise PydanticForbiddenQualifier(e.qualifier, annotation)

        # TODO check for classvar and error?

        # No assigned value, this happens when using a bare `Final` qualifier (also for other
        # qualifiers, but they shouldn't appear here). In this case we infer the type as `typing.Any`
        # because we don't have any assigned value.
        type_expr: typing.Any = typing.Any if inspected_ann.type is UNKNOWN else inspected_ann.type
        final = 'final' in inspected_ann.qualifiers
        metadata = inspected_ann.metadata

        if not metadata:
            # No metadata, e.g. `field: int`, or `field: Final[str]`:
            field_info = FieldInfo(annotation=type_expr, frozen=final or None, **kwargs)
            field_info._qualifiers = inspected_ann.qualifiers
            return field_info

        # With metadata, e.g. `field: Annotated[int, Field(...), Gt(1)]`:
        field_info_annotations = [a for a in metadata if isinstance(a, FieldInfo)]
        field_info = FieldInfo.merge_field_infos(*field_info_annotations, annotation=type_expr, **kwargs)

        new_field_info = field_info._copy()
        new_field_info.annotation = type_expr
        new_field_info.frozen = final or field_info.frozen
        field_metadata: list[typing.Any] = []
        for a in metadata:
            if typing_objects.is_deprecated(a):
                new_field_info.deprecated = a.message
            elif not isinstance(a, FieldInfo):
                field_metadata.append(a)
            else:
                field_metadata.extend(a.metadata)
            new_field_info.metadata = field_metadata
        new_field_info._qualifiers = inspected_ann.qualifiers
        if new_field_info._field_type == FieldTypes.MODEL and new_field_info.default_factory is None:
            # Set default_factory to the model class if it's not set already.
            new_field_info.default_factory = new_field_info.annotation
        return new_field_info
    
    @staticmethod
    def from_annotated_attribute(
        annotation: type[typing.Any], 
        default: typing.Any, *, 
        _source: AnnotationSource = AnnotationSource.ANY,
        **kwargs,
    ) -> "FieldInfo":
        if annotation is default:
            raise PydanticUserError(
                'Error when building FieldInfo from annotated attribute. '
                "Make sure you don't have any field name clashing with a type annotation.",
                code='unevaluable-type-annotation',
            )

        try:
            inspected_ann = inspect_annotation(
                annotation,
                annotation_source=_source,
                unpack_type_aliases='skip',
            )
        except ForbiddenQualifier as e:
            raise PydanticForbiddenQualifier(e.qualifier, annotation)

        # TODO check for classvar and error?

        # TODO infer from the default, this can be done in v3 once we treat final fields with
        # a default as proper fields and not class variables:
        type_expr: typing.Any = typing.Any if inspected_ann.type is UNKNOWN else inspected_ann.type
        final = 'final' in inspected_ann.qualifiers
        metadata = inspected_ann.metadata

        if isinstance(default, FieldInfo):
            # e.g. `field: int = Field(...)`
            default.annotation = type_expr
            default.metadata += metadata
            merged_default = FieldInfo.merge_field_infos(
                *[x for x in metadata if isinstance(x, FieldInfo)],
                default,
                annotation=default.annotation,
                **kwargs
            )
            merged_default.frozen = final or merged_default.frozen
            merged_default._qualifiers = inspected_ann.qualifiers
            return merged_default

        if isinstance(default, dataclasses.Field):
            # `collect_dataclass_fields()` passes the dataclass Field as a default.
            pydantic_field = FieldInfo._from_dataclass_field(default, **kwargs)
            pydantic_field.annotation = type_expr
            pydantic_field.metadata += metadata
            pydantic_field = FieldInfo.merge_field_infos(
                *[x for x in metadata if isinstance(x, FieldInfo)],
                pydantic_field,
                annotation=pydantic_field.annotation,
                **kwargs
            )
            pydantic_field.frozen = final or pydantic_field.frozen
            pydantic_field.init_var = 'init_var' in inspected_ann.qualifiers
            pydantic_field.init = getattr(default, 'init', None)
            pydantic_field.kw_only = getattr(default, 'kw_only', None)
            pydantic_field._qualifiers = inspected_ann.qualifiers
            return pydantic_field

        if not metadata:
            # No metadata, e.g. `field: int = ...`, or `field: Final[str] = ...`:
            field_info = FieldInfo(annotation=type_expr, default=default, frozen=final or None, **kwargs)
            field_info._qualifiers = inspected_ann.qualifiers
            return field_info

        # With metadata, e.g. `field: Annotated[int, Field(...), Gt(1)] = ...`:
        field_infos = [a for a in metadata if isinstance(a, FieldInfo)]
        field_info = FieldInfo.merge_field_infos(*field_infos, annotation=type_expr, default=default, **kwargs)
        field_metadata: list[typing.Any] = []
        for a in metadata:
            if typing_objects.is_deprecated(a):
                field_info.deprecated = a.message
            elif not isinstance(a, FieldInfo):
                field_metadata.append(a)
            else:
                field_metadata.extend(a.metadata)
        field_info.metadata = field_metadata
        field_info._qualifiers = inspected_ann.qualifiers
        if field_info._field_type == FieldTypes.MODEL and field_info.default_factory is None:
            # Set default_factory to the model class if it's not set already.
            field_info.default_factory = field_info.annotation
        return field_info
    
    @staticmethod
    def merge_field_infos(*field_infos: "FieldInfo", **overrides: typing.Any) -> "FieldInfo": # type: ignore
        if len(field_infos) == 1:
            # No merging necessary, but we still need to make a copy and apply the overrides
            field_info = field_infos[0]._copy()
            field_info._attributes_set.update(overrides)

            default_override = overrides.pop('default', PydanticUndefined)
            if default_override is Ellipsis:
                default_override = PydanticUndefined
            if default_override is not PydanticUndefined:
                field_info.default = default_override

            for k, v in overrides.items():
                setattr(field_info, k, v)
            return field_info  # type: ignore

        merged_field_info_kwargs: dict[str, typing.Any] = {}
        metadata = {}
        for field_info in field_infos:
            attributes_set = field_info._attributes_set.copy()

            try:
                json_schema_extra = attributes_set.pop('json_schema_extra')
                existing_json_schema_extra = merged_field_info_kwargs.get('json_schema_extra')

                if existing_json_schema_extra is None:
                    merged_field_info_kwargs['json_schema_extra'] = json_schema_extra
                if isinstance(existing_json_schema_extra, dict):
                    if isinstance(json_schema_extra, dict):
                        merged_field_info_kwargs['json_schema_extra'] = {
                            **existing_json_schema_extra,
                            **json_schema_extra,
                        }
                    if callable(json_schema_extra):
                        warn(
                            'Composing `dict` and `callable` type `json_schema_extra` is not supported.'
                            'The `callable` type is being ignored.'
                            "If you'd like support for this behavior, please open an issue on pydantic.",
                            PydanticJsonSchemaWarning,
                        )
                elif callable(json_schema_extra):
                    # if ever there's a case of a callable, we'll just keep the last json schema extra spec
                    merged_field_info_kwargs['json_schema_extra'] = json_schema_extra
            except KeyError:
                pass

            # later FieldInfo instances override everything except json_schema_extra from earlier FieldInfo instances
            merged_field_info_kwargs.update(attributes_set)

            for x in field_info.metadata:
                if not isinstance(x, FieldInfo):
                    metadata[type(x)] = x

        merged_field_info_kwargs.update(overrides)
        field_info = FieldInfo(**merged_field_info_kwargs)
        field_info.metadata = list(metadata.values())
        return field_info
    
    @staticmethod
    def _from_dataclass_field(dc_field: dataclasses.Field[typing.Any], **kwargs) -> "FieldInfo":
        default = dc_field.default
        if default is dataclasses.MISSING:
            default = _Unset

        if dc_field.default_factory is dataclasses.MISSING:
            default_factory = _Unset
        else:
            default_factory = dc_field.default_factory

        # use the `Field` function so in correct kwargs raise the correct `TypeError`
        dc_field_metadata = {k: v for k, v in dc_field.metadata.items() if k in _FIELD_ARG_NAMES}
        return Field(default=default, default_factory=default_factory, repr=dc_field.repr, **dc_field_metadata, **kwargs)  # pyright: ignore[reportCallIssue]


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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
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
    # Check deprecated and removed params from V1. This logic should eventually be removed.
    const = extra.pop('const', None)  # type: ignore
    if const is not None:
        raise PydanticUserError('`const` is removed, use `Literal` instead', code='removed-kwargs')

    min_items = extra.pop('min_items', None)  # type: ignore
    if min_items is not None:
        warn(
            '`min_items` is deprecated and will be removed, use `min_length` instead',
            PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if min_length in (None, _Unset):
            min_length = min_items  # type: ignore

    max_items = extra.pop('max_items', None)  # type: ignore
    if max_items is not None:
        warn(
            '`max_items` is deprecated and will be removed, use `max_length` instead',
            PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if max_length in (None, _Unset):
            max_length = max_items  # type: ignore

    unique_items = extra.pop('unique_items', None)  # type: ignore
    if unique_items is not None:
        raise PydanticUserError(
            (
                '`unique_items` is removed, use `Set` instead'
                '(this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296)'
            ),
            code='removed-kwargs',
        )

    allow_mutation = extra.pop('allow_mutation', None)  # type: ignore
    if allow_mutation is not None:
        warn(
            '`allow_mutation` is deprecated and will be removed. use `frozen` instead',
            PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if allow_mutation is False:
            frozen = True

    regex = extra.pop('regex', None)  # type: ignore
    if regex is not None:
        raise PydanticUserError('`regex` is removed. use `pattern` instead', code='removed-kwargs')

    if (_field_type := extra.pop('_field_type', None)) is None:
        def is_defined(v: typing.Any) -> bool:
            return v is not _Unset
        # try to infer field type from inputs
        if all(is_defined(v) for v in (allow_none, help, env, required, metavar)):
            _field_type = FieldTypes.ARGUMENT
        elif all(is_defined(v) for v in (usage, epilog, prefix_chars, add_help, exit_on_error, version)):
            _field_type = FieldTypes.SUBCOMMAND
        elif connect_char is not _Unset:
            _field_type = FieldTypes.MODEL
    _field_type = typing.cast(_FIELD_TYPE | None, _field_type)

    if extra:
        warn(
            'Using extra keyword arguments on `Field` is deprecated and will be removed.'
            ' Use `json_schema_extra` instead.'
            f' (Extra keys: {", ".join(k.__repr__() for k in extra.keys())})',
            PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if not json_schema_extra or json_schema_extra is _Unset:
            json_schema_extra = extra  # type: ignore

    if (
        validation_alias
        and validation_alias is not _Unset
        and not isinstance(validation_alias, (str, AliasChoices, AliasPath))
    ):
        raise TypeError('Invalid `validation_alias` type. it should be `str`, `AliasChoices`, or `AliasPath`')

    if serialization_alias in (_Unset, None) and isinstance(alias, str):
        serialization_alias = alias

    if validation_alias in (_Unset, None):
        validation_alias = alias

    include = extra.pop('include', None)  # type: ignore
    if include is not None:
        warn(
            '`include` is deprecated and does nothing. It will be removed, use `exclude` instead',
            PydanticDeprecatedSince20,
            stacklevel=2,
        )

    return FieldInfo.from_field(
        default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        field_title_generator=field_title_generator,
        description=description,
        examples=examples,
        exclude=exclude,
        exclude_if=exclude_if,
        discriminator=discriminator,
        deprecated=deprecated,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        pattern=pattern,
        validate_default=validate_default,
        repr=repr,
        init=init,
        init_var=init_var,
        kw_only=kw_only,
        coerce_numbers_to_str=coerce_numbers_to_str,
        strict=strict,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_length=min_length,
        max_length=max_length,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        union_mode=union_mode,
        fail_fast=fail_fast,
        aliases=aliases,
        allow_none=allow_none,
        help=help,
        env=env,
        required=required,
        metavar=metavar,
        metavar_default=metavar_default,
        prog=prog,
        usage=usage,
        epilog=epilog,
        prefix_chars=prefix_chars,
        add_help=add_help,
        exit_on_error=exit_on_error,
        version=version,
        connect_char=connect_char,
        hyphenate_dest=hyphenate_dest,
        include_dest_in_names=include_dest_in_names,
        _field_type=_field_type,
    )

def ArgumentField(
    *names: typing.Any,
    default: typing.Any = PydanticUndefined,
    default_factory: typing.Callable[[], typing.Any] | typing.Callable[[dict[str, typing.Any]], typing.Any] | None = _Unset,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[typing.Any] | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
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
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    if names:
        if aliases is not _Unset:
            raise TypeError("only one of 'aliases' or '*' args can be specified")
        aliases = list(names)
    return Field( # type: ignore
        default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        field_title_generator=field_title_generator,
        description=description,
        examples=examples,
        discriminator=discriminator,
        deprecated=deprecated,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        validate_default=validate_default,
        pattern=pattern,
        strict=strict,
        coerce_numbers_to_str=coerce_numbers_to_str,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_length=min_length,
        max_length=max_length,
        union_mode=union_mode,
        fail_fast=fail_fast,
        help=help,
        env=env,
        required=required,
        metavar=metavar,
        metavar_default=metavar_default,
        allow_none=allow_none,
        aliases=aliases,
        _field_type=FieldTypes.ARGUMENT,
        hyphenate_dest=hyphenate_dest,
        include_dest_in_names=include_dest_in_names,
        **extra
    )

def CommandField(
    title: str | None = _Unset,
    field_title_generator: typing.Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    prog: str | None = _Unset,
    usage: str | None = _Unset,
    epilog: str | None = _Unset,
    prefix_chars: str | None = _Unset,
    add_help: bool | None = _Unset,
    exit_on_error: bool | None = _Unset,
    version: str | None = _Unset,
    help: str | None = _Unset,
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    return Field( # type: ignore
        title=title,
        field_title_generator=field_title_generator,
        description=description,
        deprecated=deprecated,
        frozen=True,
        fail_fast=fail_fast,
        help=help,
        aliases=aliases,
        prog=prog,
        usage=usage,
        epilog=epilog,
        prefix_chars=prefix_chars,
        add_help=add_help,
        exit_on_error=exit_on_error,
        version=version,
        _field_type=FieldTypes.SUBCOMMAND,
        hyphenate_dest=hyphenate_dest,
        include_dest_in_names=include_dest_in_names,
        **extra
    )

def ModelField(
    fail_fast: bool | None = _Unset,
    aliases: list[str] | None = _Unset,
    connect_char: str | None = _Unset,
    hyphenate_dest: bool = _Unset,
    include_dest_in_names: bool = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> typing.Any:
    return Field( # type: ignore
        frozen=True,
        fail_fast=fail_fast,
        aliases=aliases,
        connect_char=connect_char,
        _field_type=FieldTypes.MODEL,
        hyphenate_dest=hyphenate_dest,
        include_dest_in_names=include_dest_in_names,
        **extra
    )