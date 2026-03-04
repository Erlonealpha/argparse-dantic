"""Recursively Nesting Sub-Parsers Action for Typed Argument Parsing.

The `actions` module contains the `SubParsersAction` class, which is an action
that provides recursive namespace nesting when parsing sub-commands. It also
contains the `BooleanOptionalAction` class, which is a direct backport of the
Python standard library `argparse` class of the same name.
"""
import sys
import argparse
from gettext import gettext as _
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple, TypeAlias, Union, cast, TYPE_CHECKING

_ActionType: TypeAlias = Callable[[str], Any] | argparse.FileType | str

if TYPE_CHECKING:
    from argparse_dantic import FieldInfo
    from argparse_dantic import ArgumentParser

def _copy_items(items):
    if items is None:
        return []
    # The copy module is used only in the 'append' and 'append_const'
    # actions, and it is needed only when the default value isn't a list.
    # Delay its import for speeding up the common case.
    if type(items) is list:
        return items[:]
    import copy
    return copy.copy(items)

class Action(argparse.Action):
    if TYPE_CHECKING:
        option_strings: Sequence[str]
        dest: str
        nargs: Optional[Union[int, str]]
        const: Any
        default: Any
        type: Optional[_ActionType]
        choices: Optional[Iterable]
        required: bool
        help: Optional[str]
        metavar: Optional[Union[str, Tuple[str, ...]]]
        deprecated: bool
        field: Optional[FieldInfo]
    if sys.version_info >= (3, 13):
        def __init__(
            self,
            option_strings,
            dest,
            nargs=None,
            const=None,
            default=None,
            type=None,
            choices=None,
            required=False,
            help=None,
            metavar=None,
            deprecated=False,
            field=None
        ):
            super().__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=nargs,
                const=const,
                default=default,
                type=type,
                choices=choices,
                required=required,
                help=help,
                metavar=metavar,
                deprecated=deprecated
            )
            self.field = field
    else:
        def __init__(
            self,
            option_strings,
            dest,
            nargs=None,
            const=None,
            default=None,
            type=None,
            choices=None,
            required=False,
            help=None,
            metavar=None,
            deprecated=False,
            field=None
        ):
            super().__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=nargs,
                const=const,
                default=default,
                type=type,
                choices=choices,
                required=required,
                help=help,
                metavar=metavar,
            )
            self.field = field
            self.deprecated = deprecated
    
    def __call__( # type: ignore[override]
        self,
        parser: 'ArgumentParser',
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None
    ):
        super().__call__(parser, namespace, values, option_string) # type: ignore[misc]

_deprecated_default = object()

class _BooleanOptionalAction(Action):
    def __init__(
        self,
        option_strings,
        dest,
        default=None,
        type=_deprecated_default,
        choices=_deprecated_default,
        required=False,
        help=None,
        metavar=_deprecated_default,
        deprecated=False,
        field=None
    ):

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith('--'):
                option_string = '--no-' + option_string[2:]
                _option_strings.append(option_string)

        # We need `_deprecated` special value to ban explicit arguments that
        # match default value. Like:
        #   parser.add_argument('-f', action=BooleanOptionalAction, type=int)
        for field_name in ('type', 'choices', 'metavar'):
            if locals()[field_name] is not _deprecated_default:
                import warnings
                if sys.version_info >= (3, 13):
                    warn = warnings.warn
                else:
                    warn = warnings._deprecated  # type: ignore[attr-defined]
                warn(
                    f"{field_name} is deprecated as of Python 3.12 and will be "
                    "removed in Python 3.14.")

        if type is _deprecated_default:
            type = None
        if choices is _deprecated_default:
            choices = None
        if metavar is _deprecated_default:
            metavar = None

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
            deprecated=deprecated,
            field=field
        )


    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(namespace, self.dest, not option_string.startswith('--no-'))  # type: ignore[union-attr]

    def format_usage(self):
        return ' | '.join(self.option_strings)

class BooleanOptionalAction(_BooleanOptionalAction):  # pragma: no cover
    """Action for parsing paired GNU-style boolean arguments.

    This backported action provides the functionality for parsing paired
    GNU-style boolean arguments, such as "--foo/--no-foo". This style of
    argument allows us to easily provide *required* boolean arguments.

    This action was added into the Python standard library `argparse` module
    in [`BPO-8538`](https://bugs.python.org/issue8538) and is available in
    Python 3.9 and above. In order to support Python 3.8 we directly backport
    the class and make it available here.

    Source:
    <https://github.com/python/cpython/blob/v3.11.0/Lib/argparse.py#L878-L914>
    """

    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        default: Optional[bool] = None,
        type = None,  # noqa: A002
        choices = None,
        required: bool = False,
        help: Optional[str] = None,  # noqa: A002
        metavar: Optional[Union[str, Tuple[str, ...]]] = None,
        field=None
    ) -> None:
        """Instantiates the Boolean Optional Action.

        This creates the default provided "--<OPT>" option strings which set
        the argument to `True`. It also creates alternative pair "--no-<OPT>"
        option strings which set the argument to `False`.

        Args:
            option_strings (Sequence[str]): Option strings.
            dest (str): Destination variable to save the value to.
            default (Optional[Union[T, str]]): Default value of the option.
            type (Optional[Union[Callable[[str], T], argparse.FileType]]): Type
                to cast the option to.
            choices (Optional[Iterable[T]]): Allowed values for the option.
            required (bool): Whether the option is required.
            help (Optional[str]): Help string for the option.
            metavar (Optional[Union[str, Tuple[str, ...]]]): Meta variable name
                for the option.
        """
        # Initialise intermediary option strings list
        _option_strings = []

        # Loop through passed in option strings
        for option_string in option_strings:
            # Append the option string to the new list
            _option_strings.append(option_string)

            # Check if this option string is a "--<OPT>" option string
            if option_string.startswith("--"):
                # Create a "--no-<OPT>" negated option string
                option_string = "--no-" + option_string[2:]

                # Append the negated option string to the new list as well
                _option_strings.append(option_string)

        # Initialise Super Class
        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
            field=field
        )

    def __call__( # type: ignore[override]
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Optional[Union[str, Sequence[Any]]],
        option_string: Optional[str] = None,
    ) -> None:
        """Parses the provided boolean arguments into a namespace.

        This custom method parses arguments as booleans, negating the values of
        any arguments prepended with "--no-".

        Args:
            parser (argparse.ArgumentParser): Parent argument parser object.
            namespace (argparse.Namespace): Parent namespace being parsed to.
            values (Optional[Union[str, Sequence[Any]]]): Arguments to parse.
            option_string (Optional[str]): Optional option string.
        """
        # Check if the passed in option string matches our option strings
        if option_string in self.option_strings:
            # Set a boolean value on the namespace
            # If the option string starts with "--no-", then negate the value
            setattr(namespace, self.dest, not option_string.startswith("--no-"))  # type: ignore[union-attr]

    def format_usage(self) -> str:
        """Formats the usage string.

        Returns:
            str: Usage string for the option.
        """
        # Format and return usage string
        return " | ".join(self.option_strings)


class _StoreAction(Action):

    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
        deprecated=False,
        field=None
    ):
        if nargs == 0:
            raise ValueError(
                'nargs for store actions must be != 0; if you '
                'have nothing to store, actions such as store '
                'true or store const may be more appropriate'
            )
        if const is not None and nargs != argparse.OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % argparse.OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
            deprecated=deprecated,
            field=field
        )

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(
        self,
        option_strings,
        dest,
        const=None,
        default=None,
        required=False,
        help=None,
        metavar=None,
        deprecated=False,
        field=None
    ):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar,
            deprecated=deprecated,
            field=field)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(
        self,
        option_strings,
        dest,
        default=False,
        required=False,
        help=None,
        deprecated=False,
        field=None
    ):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            deprecated=deprecated,
            required=required,
            help=help,
            default=default,
            field=field
        )


class _StoreFalseAction(_StoreConstAction):

    def __init__(
        self,
        option_strings,
        dest,
        default=True,
        required=False,
        help=None,
        deprecated=False,
        field=None
    ):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help,
            deprecated=deprecated,
            field=field
        )


class _AppendAction(Action):

    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
        deprecated=False,
        field=None,
    ):
        if nargs == 0:
            raise ValueError('nargs for append actions must be != 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != argparse.OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % argparse.OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
            deprecated=deprecated,
            field=field
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = _copy_items(items)
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(
        self,
        option_strings,
        dest,
        const=None,
        default=None,
        required=False,
        help=None,
        metavar=None,
        deprecated=False,
        field=None
    ):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar,
            deprecated=deprecated,
            field=field
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = _copy_items(items)
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(
        self,
        option_strings,
        dest,
        default=None,
        required=False,
        help=None,
        deprecated=False,
        field=None
    ):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help,
            deprecated=deprecated,
            field=field
        )

    def __call__(self, parser, namespace, values, option_string=None):
        count = getattr(namespace, self.dest, None)
        if count is None:
            count = 0
        setattr(namespace, self.dest, count + 1)


class _HelpAction(Action):

    def __init__(
        self,
        option_strings,
        dest=argparse.SUPPRESS,
        default=argparse.SUPPRESS,
        help=None,
        deprecated=False,
        field=None,
    ):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
            deprecated=deprecated,
            field=field
        )

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(
        self,
        option_strings,
        version=None,
        dest=argparse.SUPPRESS,
        default=argparse.SUPPRESS,
        help=None,
        deprecated=False,
        field=None
    ):
        if help is None:
            help = _("show program's version number and exit")
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
            field=field
        )
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser._print_message(formatter.format_help())
        parser.exit()


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, aliases, help, field):
            metavar = dest = name
            if aliases:
                metavar += ' (%s)' % ', '.join(aliases)
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=dest, help=help,
                         metavar=metavar, field=field)

    def __init__(
        self,
        option_strings,
        prog,
        parser_class,
        dest=argparse.SUPPRESS,
        required=False,
        help=None,
        metavar=None,
        field=None
    ):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        self._choices_actions = []
        self._deprecated = set()

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=argparse.PARSER,
            choices=self._name_parser_map,
            required=required,
            help=help,
            metavar=metavar,
            field=field
        )

    def add_parser(self, name, *, deprecated=False, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        aliases = kwargs.pop('aliases', ())

        if name in self._name_parser_map:
            raise argparse.ArgumentError(self, _('conflicting subparser: %s') % name)
        for alias in aliases:
            if alias in self._name_parser_map:
                raise argparse.ArgumentError(
                    self, _('conflicting subparser alias: %s') % alias)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, aliases, help, kwargs.pop('field'))
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser

        # make parser available under aliases also
        for alias in aliases:
            self._name_parser_map[alias] = parser

        if deprecated:
            self._deprecated.add(name)
            self._deprecated.update(aliases)

        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        assert values is not None
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not argparse.SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            subparser = self._name_parser_map[parser_name]
        except KeyError:
            args = {'parser_name': parser_name,
                    'choices': ', '.join(self._name_parser_map)}
            msg = _('unknown parser %(parser_name)r (choices: %(choices)s)') % args
            raise argparse.ArgumentError(self, msg)

        if parser_name in self._deprecated:
            parser._warning(_("command '%(parser_name)s' is deprecated") %
                            {'parser_name': parser_name})

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them

        # In case this subparser defines new defaults, we parse them
        # in a new namespace object and then update the original
        # namespace for the relevant parts.
        subnamespace, arg_strings = subparser.parse_known_args(arg_strings, None)
        for key, value in vars(subnamespace).items():
            setattr(namespace, key, value)

        if arg_strings:
            if not hasattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR):
                setattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)

class _ExtendAction(_AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = _copy_items(items)
        items.extend(values)
        setattr(namespace, self.dest, items)

class SubParsersAction(_SubParsersAction):
    """Recursively Nesting Sub-Parsers Action for Typed Argument Parsing.

    This custom action differs in functionality from the existing standard
    argparse SubParsersAction because it nests the resultant sub-namespace
    directly into the supplied parent namespace, rather than iterating through
    and updating the parent namespace object with each argument individually.

    Example:
        Construct `ArgumentParser`:
        ```python
        # Create Argument Parser
        parser = argparse.ArgumentParser()

        # Add Example Global Argument
        parser.add_argument("--time")

        # Add SubParsersAction
        subparsers = parser.add_subparsers()

        # Add Example 'walk' Command with Arguments
        walk = subparsers.add_parser("walk")
        walk.add_argument("--speed")
        walk.add_argument("--distance")

        # Add Example 'talk' Command with Arguments
        talk = subparsers.add_parser("talk")
        talk.add_argument("--volume")
        talk.add_argument("--topic")
        ```

        Parse the Arguments:
        ```console
        --time 3 walk --speed 7 --distance 42
        ```

        Check Resultant Namespaces:
        ```python
        Original: Namespace(time=3, speed=7, distance=42)
        Custom:   Namespace(time=3, walk=Namespace(speed=7, distance=42))
        ```

    This behaviour results in a final namespace structure which is much easier
    to parse, where subcommands are easily identified and nested into their own
    namespace recursively.
    """

    def __call__(
        self,
        parser: "ArgumentParser",
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        """Parses arguments into a namespace with the specified subparser.

        This custom method parses arguments with the specified subparser, then
        embeds the resultant sub-namespace into the supplied parent namespace.

        Args:
            parser (argparse.ArgumentParser): Parent argument parser object.
            namespace (argparse.Namespace): Parent namespace being parsed to.
            values (Union[str, Sequence[Any], None]): Arguments to parse.
            option_string (Optional[str]): Optional option string (not used).

        Raises:
            argparse.ArgumentError: Raised if subparser name does not exist.
        """
        # Check values object is a sequence
        # In order to not violate the Liskov Substitution Principle (LSP), the
        # function signature for __call__ must match the base Action class. As
        # such, this function signature also accepts 'str' and 'None' types for
        # the values argument. However, in reality, this should only ever be a
        # list of strings here, so we just do a type cast.
        values = cast(list[str], values)

        # Get Parser Name and Remaining Argument Strings
        parser_name, *arg_strings = values

        # Try select the parser
        try:
            # Select the parser
            parser = self._name_parser_map[parser_name]

        except KeyError as exc:
            # Parser doesn't exist, raise an exception
            raise argparse.ArgumentError(
                self,
                f"unknown parser {parser_name} (choices: {', '.join(self._name_parser_map)})",
            ) from exc

        # Parse all the remaining options into a sub-namespace, then embed this
        # sub-namespace into the parent namespace
        subnamespace, arg_strings = parser.parse_known_args(arg_strings)
        assert parser.dest is not None
        setattr(namespace, parser.dest, subnamespace)

        # Store any unrecognized options on the parent namespace, so that the
        # top level parser can decide what to do with them
        if arg_strings:
            vars(namespace).setdefault(argparse._UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)



