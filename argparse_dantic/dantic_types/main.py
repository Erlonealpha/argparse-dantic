import typing
try:
    from typing import Self # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Python < 3.11
    from typing_extensions import Self
from pydantic import BaseModel as PydanticBaseModel
from pydantic._internal import _utils

from ._construct import BaseModelMetaRewrite
from .fields import Field, FieldInfo
from ..utils import types

_T = typing.TypeVar('_T')

def __dataclass_transform__(
    *,
    eq_default: bool = True,       
    order_default: bool = False,   
    kw_only_default: bool = False, 
    field_descriptors: tuple[typing.Union[type, typing.Callable[..., typing.Any]], ...] = (()),
) -> typing.Callable[[_T], _T]:
    return lambda a: a

if typing.TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 13):
        from warnings import deprecated
    else:
        from warnings import _deprecated as deprecated  # type: ignore[attr-defined]

    class CommandNameBind(str):
        """
        CommandNameBind is a marker class for command bind types.

        Example:

        ```python
        from argparse_dantic import ArgumentParser, BaseModel, Field, CommandField, CommandNameBind

        class MyBaseModel(BaseModel):
            command_name: CommandNameBind

        class CommandA(MyBaseModel):
            option_a: bool = Field(default=False, aliases=['--a'])
        
        class CommandB(MyBaseModel):
            option_b: bool = Field(default=False, aliases=['--b'])

        class CommandModel(MyBaseModel):
            command_a: CommandA = CommandField(...)
            command_b: CommandB = CommandField(...)

        if __name__ == '__main__':
            args = ['command_a', '--a']
            parser = ArgumentParser(
                model_class=CommandModel,
            )
            arguments = parser.parse_typed_args(args)
            print(arguments)
            print(getattr(arguments, arguments.command_name))

        ```
        >>> 'CommandModel(command_name="command_a")'
        >>> 'CommandA(option_a=True)'
        """
        ...
    @deprecated("ActionNameBind is deprecated, use CommandNameBind instead.")
    class ActionNameBind:
        ...
else:
    class CommandNameBind:
        __argparse_dantic_command_name_bind__ = True
    ActionNameBind = CommandNameBind

@__dataclass_transform__(kw_only_default=True, field_descriptors=(Field, FieldInfo))
class BaseModelMeta(BaseModelMetaRewrite):
    @classmethod
    def __set_command_name_binds_names__(mcs, bases: tuple[type], namespace: dict[str, typing.Any], annotations: dict[str, typing.Any]):
        if '__command_name_binds_names__' in namespace:
            command_name_binds_names = namespace['__command_name_binds_names__']
        else:
            command_name_binds_names = set()
            if bases:
                for base in bases:
                    if hasattr(base, '__command_name_binds_names__'):
                        command_name_binds_names.update(getattr(base, '__command_name_binds_names__'))
            for k, v in annotations.items():
                v = typing.get_origin(v) or v
                if hasattr(v, '__argparse_dantic_command_name_bind__'):
                    command_name_binds_names.add(k)
            namespace['__command_name_binds_names__'] = command_name_binds_names

        # remove command name binds from namespace and annotations
        return command_name_binds_names

class BaseModel(PydanticBaseModel, metaclass=BaseModelMeta):
    """A set of global field names for this model."""
    __argparse_dantic_global_fields_names__: typing.ClassVar[set[str]] = set()

    """A set of command name binds names for this model."""
    __command_name_binds_names__: typing.ClassVar[set[str]]

    if typing.TYPE_CHECKING:
        __pydantic_fields__: typing.ClassVar[dict[str, FieldInfo]] # type: ignore[override]

        @_utils.deprecated_instance_property
        @classmethod
        def model_fields(cls) -> dict[str, FieldInfo]: # type: ignore[override]
            """A mapping of field names to their respective [`FieldInfo`][pydantic.fields.FieldInfo] instances.

            !!! warning
                Accessing this attribute from a model instance is deprecated, and will not work in Pydantic V3.
                Instead, you should access this attribute from the model class.
            """
            return getattr(cls, '__pydantic_fields__', {})

    @classmethod
    def model_validate( # type: ignore[override]
        cls, 
        obj: typing.Any, *, 
        strict: bool | None = None, 
        extra: None | typing.Literal['allow', 'ignore', 'forbid'] = None, 
        from_attributes: bool | None = None, 
        context: typing.Any | None = None, 
        by_alias: bool | None = None, 
        by_name: bool | None = None
    ) -> Self:
        envs = lookup_env_fields(cls.__pydantic_fields__)
        if envs:
            envs.update(obj)
            obj = envs
        return super().model_validate(
            obj, strict=strict, extra=extra, from_attributes=from_attributes, context=context, by_alias=by_alias, by_name=by_name
        )

def lookup_env_fields(fields: dict[str, FieldInfo]):
    import os
    
    def _lookup(fields: dict[str, FieldInfo], obj: dict[str, typing.Any]):
        for name, field in fields.items():
            if field.argument_fields is not None and \
                field.argument_fields.env is not None and \
                field.argument_fields.env in os.environ:
                obj[name] = os.environ[field.argument_fields.env]
            elif field.command_fields is not None or field.model_fields is not None:
                ann = types.get_field_type(field)
                assert ann is not None
                assert issubclass(ann, BaseModel), "AssertionError: field.annotation must be a BaseModel when it has command_fields or model_fields"
                if name not in obj:
                    _obj = {}
                else:
                    _obj = obj[name]
                _lookup(ann.__pydantic_fields__, _obj)
                if _obj and name not in obj:
                    obj[name] = _obj

    obj = {}
    _lookup(fields, obj)
    return obj
