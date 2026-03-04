import os
import re
import argparse
from typing import Optional, TYPE_CHECKING
try:
    from typing import Self
except ImportError:  # pragma: no cover - Python < 3.11
    from typing_extensions import Self
from .actions import Action

class HelpColors:
    HEADER      = "bold spring_green3"
    OPTION      = "sky_blue3"
    OPTION_BOLD = "bold sky_blue3"
    ALIAS       = "cadet_blue"

class HelpFormatter(argparse.HelpFormatter):
    if TYPE_CHECKING:
        _root_section: "_Section"
        _current_section: "_Section"

    def __init__(
        self,
        prog,
        indent_increment=2,
        max_help_position=24,
        width=None
    ):

        # default setting for width
        if width is None:
            import shutil
            width = shutil.get_terminal_size().columns
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = min(max_help_position,
                                      max(width - 20, indent_increment * 2))
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None) # type: ignore
        self._current_section = self._root_section

        self._whitespace_matcher = re.compile(r'\s+', re.ASCII)
        self._long_break_matcher = re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object): # type: ignore

        def __init__(self, formatter: 'HelpFormatter', parent: Optional[Self], heading: Optional[str]=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not argparse.SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading_text = '%(heading)s:' % dict(heading=self.heading)
                heading = '%*s%s\n' % (current_indent, '', heading_text)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not argparse.SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not argparse.SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not argparse.SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocation_lengths = [len(get_invocation(action)) + self._current_indent]
            for subaction in self._iter_indented_subactions(action):
                invocation_lengths.append(len(get_invocation(subaction)) + self._current_indent)

            # update the maximum item length
            action_length = max(invocation_lengths)
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not argparse.SUPPRESS])
    
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = f"[{HelpColors.HEADER}]Usage[/]: "

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            usage = ' '.join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                opt_parts = self._get_actions_usage_parts(optionals, groups)
                # pos_parts = self._get_actions_usage_parts(positionals, groups)
                pos_parts = []

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    indent_length = len(indent)
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = indent_length - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width and line:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = indent_length - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][indent_length:]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, f"[{HelpColors.OPTION}]{usage}[/]")
    
    def _format_actions_usage(self, actions, groups):
        return ' '.join(self._get_actions_usage_parts(actions, groups))

    def _get_actions_usage_parts(self, actions: list[argparse.Action], groups: list[argparse._ArgumentGroup]):
        # find group indices and identify actions in groups
        group_actions = set()
        inserts: dict[tuple[int, int], argparse.Action] = {}
        for group in groups:
            if not group._group_actions:
                raise ValueError(f'empty group {group}')

            if all(action.help is argparse.SUPPRESS for action in group._group_actions):
                continue

            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    group_actions.update(group._group_actions)
                    inserts[start, end] = group

        # collect all actions format strings
        parts = []
        for action in actions:

            # suppressed arguments are marked with None
            if action.help is argparse.SUPPRESS:
                part = None

            # produce all arg strings
            elif not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                part = self._format_args(action, default)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == '[' and part[-1] == ']':
                        part = part[1:-1]

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = action.format_usage()

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = '[%s]' % part

            # add the action string to the list
            parts.append(part)

        # group mutually exclusive actions
        inserted_separators_indices = set()
        for start, end in sorted(inserts, reverse=True):
            group = inserts[start, end]
            group_parts = [item for item in parts[start:end] if item is not None]
            group_size = len(group_parts)
            if group.required:
                open, close = "()" if group_size > 1 else ("", "")
            else:
                open, close = "[]"
            group_parts[0] = open + group_parts[0]
            group_parts[-1] = group_parts[-1] + close
            for i, part in enumerate(group_parts[:-1], start=start):
                # insert a separator if not already done in a nested group
                if i not in inserted_separators_indices:
                    parts[i] = part + ' |'
                    inserted_separators_indices.add(i)
            parts[start + group_size - 1] = group_parts[-1]
            for i in range(start + group_size, end):
                parts[i] = None

        # return the usage parts
        return [item for item in parts if item is not None]

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = max(self._width - self._current_indent, 11)
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2

        if action.choices is not None:
            _action_header = ""
        else:
            _action_header = self._format_action_invocation(action)

        def _color_size(*color: str):
            # Extra style markup size
            return sum(len(c) for c in color) + 5*len(color)
        
        def get_action_header(action_header: str):
            # collect the pieces of the action help
            if action_header:
                if action_header.startswith('-'):
                    return _color_size(HelpColors.OPTION), f"[{HelpColors.OPTION}]{action_header}[/]"
                else:
                    _splits = action_header.split()
                    if len(_splits) > 1:
                        return _color_size(HelpColors.OPTION_BOLD, HelpColors.ALIAS), f"[{HelpColors.OPTION_BOLD}]{_splits[0]}[/] [{HelpColors.ALIAS}]{' '.join(_splits[1:])}[/]"
                    else:
                        return _color_size(HelpColors.OPTION_BOLD), f"[{HelpColors.OPTION_BOLD}]{action_header}[/]"
            else:
                return 0, ""
        
        # no help; start on same line and add a final newline
        if not action.help:
            _, _action_header = get_action_header(_action_header)
            tup = self._current_indent, '', _action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(_action_header) <= action_width:
            extra_indent, _action_header = get_action_header(_action_header)
            tup = self._current_indent, '', action_width + extra_indent, _action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            _, _action_header = get_action_header(_action_header)
            tup = self._current_indent, '', _action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position
        
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help and action.help.strip():
            help_text = self._expand_help(action)
            if help_text:
                help_lines = self._split_lines(help_text, help_width)
                parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
                for line in help_lines[1:]:
                    parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            return ' '.join(self._metavar_formatter(action, default)(1))

        else:

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                return ', '.join(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s, --long ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                return ', '.join(action.option_strings) + ' ' + args_string

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            result = '{%s}' % ','.join(map(str, action.choices))
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == argparse.OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == argparse.ZERO_OR_MORE:
            metavar = get_metavar(1)
            if len(metavar) == 2:
                result = '[%s [%s ...]]' % metavar
            else:
                result = '[%s ...]' % metavar
        elif action.nargs == argparse.ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif action.nargs == argparse.REMAINDER:
            result = '...'
        elif action.nargs == argparse.PARSER:
            result = '%s ...' % get_metavar(1)
        elif action.nargs == argparse.SUPPRESS:
            result = ''
        else:
            try:
                formats = ['%s' for _ in range(action.nargs)]
            except TypeError:
                raise ValueError("invalid nargs value") from None
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is argparse.SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            params['choices'] = ', '.join(map(str, params['choices']))
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            yield from get_subactions()
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        # The textwrap module is used only for formatting help.
        # Delay its import for speeding up the common usage of argparse.
        import textwrap
        return textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        import textwrap
        return textwrap.fill(
            text, width,
            initial_indent=indent,
            subsequent_indent=indent
        )

    def _get_help_string(self, action: Action): # type: ignore
        if action.field is not None and \
            action.field.argument_fields is not None and \
            action.field.argument_fields.env is not None:
            env_var = os.environ.get(action.field.argument_fields.env)
            if env_var is not None:
                env = f"\\[env: {action.field.argument_fields.env}={env_var}]" # type: ignore
            else:
                env = f"\\[env: {action.field.argument_fields.env}=]" # type: ignore
            if action.help is not None:
                return f"{action.help} {env}"
            else:
                return env

        return action.help

    def _get_default_metavar_for_optional(self, action: Action): # type: ignore
        return action.dest.upper()

    def _get_default_metavar_for_positional(self, action: Action): # type: ignore
        return action.dest
