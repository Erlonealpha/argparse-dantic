import typing
from warnings import deprecated
from pydantic import BaseModel as PydanticBaseModel
from pydantic._internal import _utils

from ._construct import BaseModelMetaRewrite, GlobalData, default_global_data
from .fields import Field, FieldInfo

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
    def __set_command_name_binds_names__(mcs, bases: tuple[type], namespace: dict[str, typing.Any], annotations: dict[str, typing.Any]) -> None:
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
        for command_name in command_name_binds_names:
            if command_name in namespace:
                del namespace[command_name]
            annotations[command_name] = typing.Annotated[str | None, Field(default=None)]

class BaseModel(PydanticBaseModel, metaclass=BaseModelMeta, global_data=default_global_data):
    global_data: typing.ClassVar[GlobalData]
    """A class-level attribute that holds the global data for the model."""

    __command_name_binds_names__: typing.ClassVar[set[str]]
    """A set of command name binds names for this model."""

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