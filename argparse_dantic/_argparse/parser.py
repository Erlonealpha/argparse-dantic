"""Declarative and Typed Argument Parser.

The `parser` module contains the `ArgumentParser` class, which provides a
declarative method of defining command-line interfaces.

The procedure to declaratively define a typed command-line interface is:

1. Define `pydantic` arguments model
2. Create typed `ArgumentParser`
3. Parse typed arguments

The resultant arguments object returned is an instance of the defined
`pydantic` model. This means that the arguments object and its attributes will
be compatible with an IDE, linter or type checker.
"""

import os
import sys
import re
import pydantic
import argparse
import inspect

from rich import get_console
from rich.console import Console
from typing import Any, Union, Generic, NoReturn, Optional, Type, TypeVar, Callable, TYPE_CHECKING
from gettext import gettext as _, ngettext

from . import actions, container
from .. import parsers, utils
from .help import HelpFormatter, HelpColors
from ..dantic_types import BaseModel, FieldInfo
from ..dantic_types.basic_config import _DefaultConfig
from ..dantic_types.groups import _Group as Group, _MutuallyExclusiveGroup as MutuallyExclusiveGroup
from ..dantic_types.fields import ArgumentFieldInfo


# Constants
PydanticModelT = TypeVar("PydanticModelT", bound=BaseModel)


class ArgumentParser(argparse._AttributeHolder, container._ActionsContainer, Generic[PydanticModelT]):
    """Declarative and Typed Argument Parser.

    The `ArgumentParser` declaratively generates a command-line interface using
    the `pydantic` model specified upon instantiation.

    The `ArgumentParser` provides the following `argparse` functionality:

    * Required Arguments
    * Optional Arguments
    * Subcommands

    All arguments are *named*, and positional arguments are not supported.

    The `ArgumentParser` provides the method `parse_typed_args()` to parse
    command line arguments and return an instance of its bound `pydantic`
    model, populated with the parsed and validated user supplied command-line
    arguments.
    """

    # Argument Group Names
    COMMANDS = "Commands"
    REQUIRED = "Required Arguments"
    OPTIONAL = "Optional Arguments"
    HELP = "Help"

    # Keyword Arguments
    KWARG_REQUIRED = "Required"

    # Exit Codes
    EXIT_ERROR = 2

    def __init__(
        self,
        model_class: Type[PydanticModelT],
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        epilog: Optional[str] = None,
        prefix_chars: str =     None,     # type: ignore
        add_help: bool =        None,         # type: ignore
        exit_on_error: bool =   None,    # type: ignore
        console: Optional[Console] = None,
        formatter_class: Type[argparse.HelpFormatter] = HelpFormatter,
    ) -> None:
        """Instantiates the Typed Argument Parser with its `pydantic` model.

        Args:
            model_class (Type[PydanticModelT]): Pydantic argument model class.
            prog (Optional[str]): Program name for CLI.
            description (Optional[str]): Program description for CLI.
            version (Optional[str]): Program version string for CLI.
            epilog (Optional[str]): Optional text following help message.
            add_help (bool): Whether to add a `-h`/`--help` flag.
            exit_on_error (bool): Whether to exit on error.
        """

        if prefix_chars is None:
            prefix_chars = _DefaultConfig.get("prefix_chars") # type: ignore
        if add_help is None:
            add_help = _DefaultConfig.get("add_help") # type: ignore
        if exit_on_error is None:
            exit_on_error = _DefaultConfig.get("exit_on_error") # type: ignore
        superinit = super(ArgumentParser, self).__init__
        superinit(
            description=description,
            prefix_chars=prefix_chars,
            argument_default=argparse.SUPPRESS,
            conflict_handler='error'
        )
        if prog is None:
            prog = os.path.basename(sys.argv[0])
        
        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = None
        self.add_help = add_help
        self.allow_abbrev = True
        self.exit_on_error = exit_on_error

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('options'))
        self._subparsers = None
        self._m_groups: dict[int, tuple[Callable, list[container._ArgumentGroup | container._MutuallyExclusiveGroup]]] = {}

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)
        
        # Set Console
        self.console = console or get_console()

        # Set Version, Add Help and Exit on Error Flag
        self.version = version
        self.add_help = add_help
        self.exit_on_error = exit_on_error

        # Add Arguments Groups
        self._subcommands: Optional[actions._SubParsersAction] = None
        self._sub_models: Optional[list["SubModel"]] = None
        self._remap_names: dict[str, tuple[str,...]] = {}
        self._required_group = self.add_argument_group(ArgumentParser.REQUIRED)
        self._optional_group = self.add_argument_group(ArgumentParser.OPTIONAL)
        self._help_group = self.add_argument_group(ArgumentParser.HELP)

        # Add Help and Version Flags
        if self.add_help:
            self._add_help_flag()
        if self.version:
            self._add_version_flag()

        # Add Arguments from Model
        self.model = self._add_model(model_class)
        self.dest = None

    def _set_dest(self, dest):
        if self.dest is not None:
            raise ValueError('dest is already set')
        self.dest = dest

    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]
    
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            raise argparse.ArgumentError(None, _('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = kwargs.pop('title', _('subcommands'))
            description = kwargs.pop('description', None)
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '') # type: ignore
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action
    
    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action
    
    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]
    
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s') % ' '.join(argv)
            if self.exit_on_error:
                self.error(msg)
            else:
                raise argparse.ArgumentError(None, msg)
        return args

    def parse_known_args(self, args=None, namespace=None):
        return self._parse_known_args2(args, namespace, intermixed=False)

    def _parse_known_args2(self, args, namespace, intermixed):
        if args is None:
            # args default to the system args
            args = sys.argv[1:]
        else:
            # make sure that args are mutable
            args = list(args)

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = argparse.Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not argparse.SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not argparse.SUPPRESS:
                        setattr(namespace, action.dest, action.default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        if self.exit_on_error:
            try:
                namespace, args = self._parse_known_args(args, namespace, intermixed)
            except argparse.ArgumentError as err:
                self.error(str(err))
        else:
            namespace, args = self._parse_known_args(args, namespace, intermixed)

        if hasattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR):
            args.extend(getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR))
            delattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR)
        return namespace, args

    def _parse_known_args(self, arg_strings, namespace, intermixed):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuples = self._parse_optional(arg_string)
                if option_tuples is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuples
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = set()
        seen_non_default_actions = set()
        warned = set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments
            if action.option_strings or argument_strings:
                seen_non_default_actions.add(action)
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = argparse._get_action_name(conflict_action)
                        raise argparse.ArgumentError(action, msg % action_name)

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not argparse.SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):

            # get the optional identified at this index
            option_tuples = option_string_indices[start_index]
            # if multiple actions match, the option string was ambiguous
            if len(option_tuples) > 1:
                options = ', '.join([option_string
                    for action, option_string, sep, explicit_arg in option_tuples])
                args = {'option': arg_strings[start_index], 'matches': options}
                msg = _('ambiguous option: %(option)s could match %(matches)s')
                raise argparse.ArgumentError(None, msg % args)

            action, option_string, sep, explicit_arg = option_tuples[0]

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    extras_pattern.append('O')
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if (
                        arg_count == 0
                        and option_string[1] not in chars
                        and explicit_arg != ''
                    ):
                        if sep or explicit_arg[0] in chars:
                            msg = _('ignored explicit argument %r')
                            raise argparse.ArgumentError(action, msg % explicit_arg)
                        action_tuples.append((action, [], option_string))
                        char = option_string[0]
                        option_string = char + explicit_arg[0]
                        optionals_map = self._option_string_actions
                        if option_string in optionals_map:
                            action = optionals_map[option_string]
                            explicit_arg = explicit_arg[1:]
                            if not explicit_arg:
                                sep = explicit_arg = None
                            elif explicit_arg[0] == '=':
                                sep = '='
                                explicit_arg = explicit_arg[1:]
                            else:
                                sep = ''
                        else:
                            extras.append(char + explicit_arg)
                            extras_pattern.append('O')
                            stop = start_index + 1
                            break
                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise argparse.ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            assert action_tuples
            for action, args, option_string in action_tuples:
                if action.deprecated and option_string not in warned:
                    self._warning(_("option '%(option)s' is deprecated") %
                                  {'option': option_string})
                    warned.add(option_string)
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                # Strip out the first '--' if it is not in REMAINDER arg.
                if action.nargs == argparse.PARSER:
                    if arg_strings_pattern[start_index] == '-':
                        assert args[0] == '--'
                        args.remove('--')
                elif action.nargs != argparse.REMAINDER:
                    if (arg_strings_pattern.find('-', start_index,
                                                 start_index + arg_count) >= 0):
                        args.remove('--')
                start_index += arg_count
                if args and action.deprecated and action.dest not in warned:
                    self._warning(_("argument '%(argument_name)s' is deprecated") %
                                  {'argument_name': action.dest})
                    warned.add(action.dest)
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        extras = []
        extras_pattern = []
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = start_index
            while next_option_string_index <= max_option_string_index:
                if next_option_string_index in option_string_indices:
                    break
                next_option_string_index += 1
            if not intermixed and start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were extra arguments
            if start_index not in option_string_indices:
                strings = arg_strings[start_index:next_option_string_index]
                extras.extend(strings)
                extras_pattern.extend(arg_strings_pattern[start_index:next_option_string_index])
                start_index = next_option_string_index

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        if not intermixed:
            # consume any positionals following the last Optional
            stop_index = consume_positionals(start_index)

            # if we didn't consume all the argument strings, there were extras
            extras.extend(arg_strings[stop_index:])
        else:
            extras.extend(arg_strings[start_index:])
            extras_pattern.extend(arg_strings_pattern[start_index:])
            extras_pattern_str = ''.join(extras_pattern)
            assert len(extras_pattern_str) == len(extras)
            # consume all positionals
            arg_strings = [s for s, c in zip(extras, extras_pattern_str) if c != 'O']
            arg_strings_pattern = extras_pattern_str.replace('O', '')
            stop_index = consume_positionals(0)
            # leave unknown optionals and non-consumed positionals in extras
            for i, c in enumerate(extras_pattern_str):
                if not stop_index:
                    break
                if c != 'O':
                    stop_index -= 1
                    extras[i] = None
            extras = [s for s in extras if s is not None]

        # make sure all required actions were present and also convert
        # action defaults which were not given as arguments
        required_actions = []
        for action in self._actions:
            if action not in seen_actions:
                if action.required:
                    required_actions.append(argparse._get_action_name(action))
                else:
                    # Convert action default now instead of doing it before
                    # parsing arguments to avoid calling convert functions
                    # twice (which may fail) if the argument was given, but
                    # only if it was defined already in the namespace
                    if (action.default is not None and
                        isinstance(action.default, str) and
                        hasattr(namespace, action.dest) and
                        action.default is getattr(namespace, action.dest)):
                        setattr(namespace, action.dest,
                                self._get_value(action, action.default))

        if required_actions:
            raise argparse.ArgumentError(None, _('the following arguments are required: %s') %
                       ', '.join(required_actions))

        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [argparse._get_action_name(action) or ''
                             for action in group._group_actions
                             if action.help is not argparse.SUPPRESS]
                    msg = _('one of the arguments %s is required')
                    raise argparse.ArgumentError(None, msg % ' '.join(names))

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if not arg_string or arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    with open(arg_string[1:],
                              encoding=sys.getfilesystemencoding(),
                              errors=sys.getfilesystemencodeerrors()) as args_file:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                except OSError as err:
                    raise argparse.ArgumentError(None, str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                argparse.OPTIONAL: _('expected at most one argument'),
                argparse.ONE_OR_MORE: _('expected at least one argument'),
            }
            msg = nargs_errors.get(action.nargs)
            if msg is None:
                msg = ngettext('expected %s argument',
                               'expected %s arguments',
                               action.nargs) % action.nargs
            raise argparse.ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([self._get_nargs_pattern(action)
                               for action in actions_slice])
            match = re.match(pattern, arg_strings_pattern)
            if match is not None:
                result = [len(string) for string in match.groups()]
                if (match.end() < len(arg_strings_pattern)
                    and arg_strings_pattern[match.end()] == 'O'):
                    while result and not result[-1]:
                        del result[-1]
                return result
        return []

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if arg_string[0] not in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return [(action, arg_string, None, None)]

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        option_string, sep, explicit_arg = arg_string.partition('=')
        if sep and option_string in self._option_string_actions:
            action = self._option_string_actions[option_string]
            return [(action, option_string, sep, explicit_arg)]

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        if option_tuples:
            return option_tuples

        # if it was not found as an option, but it looks like a negative
        # number, it was meant to be positional
        # unless there are negative-number-like options
        if self._negative_number_matcher.match(arg_string):
            if not self._has_negative_number_optionals:
                return None

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return [(None, arg_string, None, None)]

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if self.allow_abbrev:
                option_prefix, sep, explicit_arg = option_string.partition('=')
                if not sep:
                    sep = explicit_arg = None
                for option_string in self._option_string_actions:
                    if option_string.startswith(option_prefix):
                        action = self._option_string_actions[option_string]
                        tup = action, option_string, sep, explicit_arg
                        result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix, sep, explicit_arg = option_string.partition('=')
            if not sep:
                sep = explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, '', short_explicit_arg
                    result.append(tup)
                elif self.allow_abbrev and option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, sep, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            raise argparse.ArgumentError(None, _('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs
        # if this is an optional action, -- is not allowed
        option = action.option_strings

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '([A])' if option else '(-*A-*)'

        # allow zero or one arguments
        elif nargs == argparse.OPTIONAL:
            nargs_pattern = '(A?)' if option else '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == argparse.ZERO_OR_MORE:
            nargs_pattern = '(A*)' if option else '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == argparse.ONE_OR_MORE:
            nargs_pattern = '(A+)' if option else '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == argparse.REMAINDER:
            nargs_pattern = '([AO]*)' if option else '(.*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == argparse.PARSER:
            nargs_pattern = '(A[AO]*)' if option else '(-*A[-AO]*)'

        # suppress action, like nargs=0
        elif nargs == argparse.SUPPRESS:
            nargs_pattern = '()' if option else '(-*)'

        # all others should be integers
        else:
            nargs_pattern = '([AO]{%d})' % nargs if option else '((?:-*A){%d}-*)' % nargs

        # return the pattern
        return nargs_pattern

    # ========================
    # Alt command line argument parsing, allowing free intermix
    # ========================

    def parse_intermixed_args(self, args=None, namespace=None):
        args, argv = self.parse_known_intermixed_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s') % ' '.join(argv)
            if self.exit_on_error:
                self.error(msg)
            else:
                raise argparse.ArgumentError(None, msg)
        return args

    def parse_known_intermixed_args(self, args=None, namespace=None):
        # returns a namespace and list of extras
        #
        # positional can be freely intermixed with optionals.  optionals are
        # first parsed with all positional arguments deactivated.  The 'extras'
        # are then parsed.  If the parser definition is incompatible with the
        # intermixed assumptions (e.g. use of REMAINDER, subparsers) a
        # TypeError is raised.

        positionals = self._get_positional_actions()
        a = [action for action in positionals
             if action.nargs in [argparse.PARSER, argparse.REMAINDER]]
        if a:
            raise TypeError('parse_intermixed_args: positional arg'
                            ' with nargs=%s'%a[0].nargs)

        return self._parse_known_args2(args, namespace, intermixed=True)

    # ========================
    # Value conversion methods
    # ========================
    def _get_values(self, action, arg_strings):
        # optional argument produces a default when not present
        if not arg_strings and action.nargs == argparse.OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, str) and value is not argparse.SUPPRESS:
                value = self._get_value(action, value)
                self._check_value(action, value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == argparse.ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
                self._check_value(action, value)
            else:
                # since arg_strings is always [] at this point
                # there is no need to use self._check_value(action, value)
                value = arg_strings

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, argparse.OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == argparse.REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == argparse.PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            self._check_value(action, value[0])

        # SUPPRESS argument does not put anything in the namespace
        elif action.nargs == argparse.SUPPRESS:
            value = argparse.SUPPRESS

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not callable(type_func):
            msg = _('%r is not callable')
            raise argparse.ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except argparse.ArgumentTypeError as err:
            msg = str(err)
            raise argparse.ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            args = {'type': name, 'value': arg_string}
            msg = _('invalid %(type)s value: %(value)r')
            raise argparse.ArgumentError(action, msg % args)

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        choices = action.choices
        if choices is not None:
            if isinstance(choices, str):
                choices = iter(choices)
            if value not in choices:
                args = {'value': str(value),
                        'choices': ', '.join(map(str, action.choices))}
                msg = _('invalid choice: %(value)r (choose from %(choices)s)')
                raise argparse.ArgumentError(action, msg % args)

    def parse_typed_args(
        self,
        args: Optional[list[str]] = None,
    ) -> PydanticModelT:
        """Parses command line arguments.

        If `args` are not supplied by the user, then they are automatically
        retrieved from the `sys.argv` command-line arguments.

        Args:
            args (Optional[list[str]]): Optional list of arguments to parse.

        Returns:
            PydanticModelT: Populated instance of typed arguments model.

        Raises:
            argparse.ArgumentError: Raised upon error, if not exiting on error.
            SystemExit: Raised upon error, if exiting on error.
        """
        # Call Super Class Method
        namespace = self.parse_args(args)

        # Convert Namespace to Dictionary
        arguments = utils.namespaces.to_dict(namespace)

        self._remap_sub_model_fields(arguments)

        # Apply Global Data
        self._apply_global_data(self.model, arguments)

        # Handle Possible Validation Errors
        try:
            # Convert Namespace to Pydantic Model
            model = self.model.model_validate(arguments)

            # Apply Action Bind Names
            self._apply_command_bind_names(model, arguments)

        except (pydantic.ValidationError) as exc:
            # , pydantic.env_settings.SettingsError
            # Catch exceptions, and use the ArgumentParser.error() method
            # to report it to the user
            self.error(utils.errors.format(exc))

        # Return
        return model

    def _remap_sub_model_fields(self, argumens: dict[str, Any]):

        def _iter(dic: dict[str, Any]):
            dels = []
            remap = {}
            for k, v in dic.items():
                if k in self._remap_names:
                    dels.append(k)
                    names = self._remap_names[k]
                    d = remap
                    for name in names[:-1]:
                        if name not in d:
                            d[name] = {}
                        d = d[name]
                    d[names[-1]] = v
                elif isinstance(v, dict):
                    _iter(v)
            dic.update(remap)
            for _k in dels:
                del dic[_k]

        _iter(argumens)
    
    @staticmethod
    def _apply_global_data(model: Type[PydanticModelT], arguments: dict[str, Any]):
        
        def _global_check(k, v, model: Type[PydanticModelT]):
            field = model.__pydantic_fields__[k]
            if field.global_:
                if field.model_fields is not None:
                    getattr(model, "global_data")[k] = field.annotation.model_validate(v) # type: ignore
                else:
                    getattr(model, "global_data")[k] = v

            if isinstance(v, dict):
                _iter(v, utils.types.get_field_type(field))
        
        def _iter(dic: dict[str, Any], model: Type[PydanticModelT]):
            for k, v in dic.items():
                _global_check(k, v, model)
        
        _iter(arguments, model)
    
    @staticmethod
    def _apply_command_bind_names(model: PydanticModelT, arguments: dict[str, Any]) -> None:
        """Applies command bind names to the namespace."""
        def _get_binds(model) -> Optional[list[str]]:
            return getattr(model, "__command_name_binds_names__")
        
        def _apply(k: str, v: Union[str, dict[str, Any]], model: PydanticModelT, field: Optional[FieldInfo] = None):
            if field is None:
                field = model.__pydantic_fields__[k]
            # Only apply command bind names to fields that are commands
            if parsers.command.should_parse(field):
                binds = _get_binds(model)
            else:
                binds = None
            
            if isinstance(v, dict):
                _model = getattr(model, k, None)
                if _model is not None:
                    _iter(v, _model)
            
            return binds
        
        def _iter(dic: dict[str, Any], model: PydanticModelT, field = None):
            binds = None
            bind_k = None
            for k, v in dic.items():
                binds = _apply(k, v, model, field)
                if binds:
                    if bind_k is not None:
                        raise ValueError(f"Multiple commands found for {k}")
                    bind_k = k

            if bind_k and binds:
                for bind in binds:
                    # Apply action bind name to the model
                    setattr(model, bind, bind_k)

        _iter(arguments, model)

    def add_argument(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> argparse.Action:
        """Adds an argument to the ArgumentParser.

        Args:
            *args (Any): Positional args to be passed to super class method.
            **kwargs (Any): Keyword args to be passed to super class method.

        Returns:
            argparse.Action: Action generated by the argument.
        """
        # Check whether the argument is required or optional
        # We intercept the keyword arguments and "pop" here so that the
        # `required` kwarg can never be passed through to the parent
        # `ArgumentParser`, allowing Pydantic to perform all of the validation
        # and error handling itself.
        if kwargs.pop(ArgumentParser.KWARG_REQUIRED.lower()):
            # Required
            group = self._required_group
        else:
            # Optional
            group = self._optional_group

        # Return Action
        return group.add_argument(*args, **kwargs) # type: ignore
    
    def _commands(self, field=None) -> argparse._SubParsersAction:
        """Creates and Retrieves Subcommands Action for the ArgumentParser.

        Returns:
            argparse._SubParsersAction: SubParsersAction for the subcommands.
        """
        # Check for Existing Sub-Commands Group
        if not self._subcommands:
            # Add Sub-Commands Group
            self._subcommands = self.add_subparsers(
                title=ArgumentParser.COMMANDS,
                action=actions.SubParsersAction,
                required=True,
                field=field
            )

            # Shuffle Group to the Top for Help Message
            self._action_groups.insert(0, self._action_groups.pop())

        # Return
        return self._subcommands # type: ignore

    def _add_sub_model(self, prefix: str, connect_char: str, model: Type[PydanticModelT]):
        if not self._sub_models:
            self._sub_models = []
        sub_model = SubModel(self, prefix, connect_char)
        self._sub_models.append(sub_model)
        sub_model._add_model(model)

    @staticmethod
    def __add_group(con: container._ActionsContainer, group: Group | MutuallyExclusiveGroup):
        groups = []
        if isinstance(group, MutuallyExclusiveGroup):
            _group = con.add_mutually_exclusive_group(required = group.required)
        elif isinstance(group, Group):
            _group = con.add_argument_group(group.title, group.description)
        else:
            raise ValueError(f"Invalid group type: {type(group)}")
        groups.append(_group)

        for _g in group._groups:
            groups.extend(ArgumentParser.__add_group(_group, _g))
        for _g in group._mutually_exclusive_groups:
            groups.extend(ArgumentParser.__add_group(_group, _g))

        return groups

    def _add_group(self, group: Group | MutuallyExclusiveGroup):
        p = self._m_groups.get(hash(group))
        if p is None:
            groups = self.__add_group(self, group)
            g = groups[-1]
            _g = GroupWrapper(self, g)
            def wrapper(func):
                def fn(*args, **kwargs):
                    return func.__func__(_g, *args, **kwargs)
                return fn
            add_field = wrapper(self._add_field)
            self._m_groups[hash(group)] = (add_field, groups)
        else:
            add_field, groups = p
        return add_field

    def _register_remap_names(self, name: str, names: tuple[str,...]):
        self._remap_names[name] = names

    def _add_help_flag(self) -> None:
        """Adds help flag to argparser."""
        # Add help flag
        self._help_group.add_argument(
            "-h",
            "--help",
            action=actions._HelpAction,
            help="show this help message and exit",
        )

    def _add_version_flag(self) -> None:
        """Adds version flag to argparser."""
        # Add version flag
        self._help_group.add_argument(
            "-v",
            "--version",
            action=actions._VersionAction,
            help="show program's version number and exit",
        )

    def _add_model(self, model: Type[PydanticModelT]) -> Type[PydanticModelT]:
        """Adds the `pydantic` model to the argument parser.

        This method also generates "validators" for the arguments derived from
        the `pydantic` model, and generates a new subclass from the model
        containing these validators.

        Args:
            model (Type[PydanticModelT]): Pydantic model class to add to the
                argument parser.

        Returns:
            Type[PydanticModelT]: Pydantic model possibly with new validators.
        """
        # Initialise validators dictionary
        validators: dict[str, utils.pydantic.PydanticValidator] = {}

        # Loop through fields in model
        for field in model.__pydantic_fields__.values():
            if field.dest in model.__command_name_binds_names__:
                # Skip command name binds field
                continue

            if field.group is not None:
                add_field = self._add_group(field.group)
            else:
                add_field = self._add_field

            # Add field
            validator = add_field(field)

            if field.global_ and field.dest not in (_global_data := getattr(model, "global_data")):
                # Set default value for global data
                _global_data[field.dest] = field.get_default()

            # Update validators
            utils.pydantic.update_validators(validators, validator)

        # Construct and return model with validators
        return utils.pydantic.model_with_validators(model, validators)

    def _add_field(self, field: FieldInfo) -> Optional[utils.pydantic.PydanticValidator]:
        """Adds `pydantic` field to argument parser.

        Args:
            field (FieldInfo): Field to be added to parser.

        Returns:
            Optional[utils.pydantic.PydanticValidator]: Possible validator.
        """
        if parsers.command.should_parse(field):
            if hasattr(self, "_group"):
                raise ValueError("Cannot add sub-commands to a group")
            # Add Command
            validator = parsers.command.parse_field(self._commands(field), field, self.console) # type: ignore

        elif parsers.boolean.should_parse(field):
            # Add Boolean Field
            validator = parsers.boolean.parse_field(self, field)

        elif parsers.container.should_parse(field):
            # Add Container Field
            validator = parsers.container.parse_field(self, field)

        elif parsers.mapping.should_parse(field):
            # Add Mapping Field
            validator = parsers.mapping.parse_field(self, field)

        elif parsers.literal.should_parse(field):
            # Add Literal Field
            validator = parsers.literal.parse_field(self, field)

        elif parsers.enum.should_parse(field):
            # Add Enum Field
            validator = parsers.enum.parse_field(self, field)

        elif parsers.model.should_parse(field):
            # Add Sub-Model Field
            validator = parsers.model.parse_field(self, field)

        else:
            # Add Standard Field
            validator = parsers.standard.parse_field(self, field)

        if getattr(field, "_prefix", None) is not None:
            assert field.dest is not None
            self._register_remap_names(field.dest, tuple(field.dest.split(field._connect_char))) # type: ignore

        # Return Validator
        return validator

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups) # type: ignore
        return formatter.format_help()

    def format_help(self) -> str:
        formatter = self._get_formatter()

        # description
        formatter.add_text(self.description)

        # usage
        formatter.add_usage(
            self.usage, self._actions,
            self._mutually_exclusive_groups # type: ignore
        )

        global_actions = []
        
        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            group_actions = action_group._group_actions.copy()
            for i in range(len(group_actions) - 1, -1, -1):
                field = group_actions[i].field
                if field is not None and field.global_:
                    global_actions.append(group_actions.pop(i))
            if not group_actions:
                continue
            formatter.start_section(f"[{HelpColors.HEADER}]{action_group.title}[/]")
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        
        # global options
        formatter.start_section(f"[{HelpColors.HEADER}]Global Options[/]")
        formatter.add_arguments(global_actions)
        formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_help(self, file=None):
        self._print_message(self.format_help())
    
    def print_usage(self, file = None):
        self._print_message(self.format_usage())

    def _print_message(self, message: str):
        self.console.print(message, markup=True)
    
    def exit(self, status = 0, message = None):
        if message:
            self._print_message(message)
        sys.exit(status)

    def error(self, message: str) -> NoReturn:
        """Prints a usage message to `stderr` and exits if required.

        Args:
            message (str): Message to print to the user.

        Raises:
            argparse.ArgumentError: Raised if not exiting on error.
            SystemExit: Raised if exiting on error.
        """
        # Print usage message
        self.print_usage(sys.stderr)

        # Check whether parser should exit
        if self.exit_on_error:
            self.exit(ArgumentParser.EXIT_ERROR, f"{self.prog}: error: {message}\n")

        # Raise Error
        raise argparse.ArgumentError(None, f"{self.prog}: error: {message}")

    def _warning(self, message):
        args = {'prog': self.prog, 'message': message}
        self._print_message(_('%(prog)s: warning: %(message)s\n') % args)

if TYPE_CHECKING:
    ArgumentFieldWrapper: Type[ArgumentFieldInfo]
else:
    class ArgumentFieldWrapper:
        def __init__(self, args: tuple[str, FieldInfo]):
            prefix, field = args
            self._field = field
            self.aliases = [prefix + alias for alias in field.aliases]

        def __getattr__(self, name):
            if name in self.__dict__:
                return self.__dict__[name]
            return getattr(self._field, name)

if TYPE_CHECKING:
    FieldInfoWrapper: Type[FieldInfo]
else:
    class FieldInfoWrapper:
        def __init__(self, args: tuple[str, FieldInfo]):
            prefix, connect_char, field = args
            assert field.dest is not None
            self._field = field
            self._prefix = prefix
            self._connect_char = connect_char
            self.dest = prefix + field.dest
            self.aliases = [prefix + alias for alias in field.aliases]
            if field.argument_fields is not None:
                self.argument_fields = ArgumentFieldWrapper((prefix, field.argument_fields))
            else:
                self.argument_fields = None

        def __getattr__(self, name):
            if name in self.__dict__:
                return self.__dict__[name]
            return getattr(self._field, name)

if TYPE_CHECKING:
    class SubModel(ArgumentParser):
        def __init__(self, parser: ArgumentParser, prefix: str, connect_char: str):
            ...
else:
    class SubModel:
        def __init__(self, parser: ArgumentParser, prefix: str, connect_char: str):
            self._parser = parser
            self._prefix = prefix
            self._connect_char = connect_char

        def _commands(self, *args, **kwargs):
            raise ValueError("Sub-Models cannot have sub-commands")

        def _add_field(self, field: FieldInfo):
            return self._parser._add_field(FieldInfoWrapper((self._prefix + self._connect_char, self._connect_char, field)))

        def _func_wrap(self, func):
            def wrapper(*args, **kwargs):
                if hasattr(func, "__self__"):
                    if func.__self__ is self._parser:
                        return func.__func__(self, *args, **kwargs)
                return func(*args, **kwargs)
            return wrapper

        def __getattr__(self, name):
            if name in self.__dict__:
                return self.__dict__[name]
            if name in ("_commands", "_add_field"):
                return getattr(self._parser, name)
            val = getattr(self._parser, name)
            if inspect.ismethod(val):
                return self._func_wrap(val)
            return val

class GroupWrapper:
    def __init__(self, parser: ArgumentParser, group: container._ArgumentGroup):
        self._parser = parser
        self._group = group

    def _func_wrap(self, func):
            def wrapper(*args, **kwargs):
                if hasattr(func, "__self__"):
                    if func.__self__ is self._parser:
                        return func.__func__(self, *args, **kwargs)
                return func(*args, **kwargs)
            return wrapper

    def __getattr__(self, name):
        if name == "add_argument":
            return self._group.add_argument
        val = getattr(self._parser, name)
        if inspect.ismethod(val):
            return self._func_wrap(val)
        return val