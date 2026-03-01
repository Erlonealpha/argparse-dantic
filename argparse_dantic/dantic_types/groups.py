import sys

class _Container:
    def __init__(self, title: str | None = None, description: str | None = None):
        self.title = title
        self.description = description
        self._groups = []
        self._mutually_exclusive_groups = []

    def create_group(self, title: str | None = None, description: str | None = None):
        self._groups.append(_Group(title, description))
        return self

    def create_mutually_exclusive_group(self, required: bool = False):
        self._mutually_exclusive_groups.append(_MutuallyExclusiveGroup(required))
        return self

class _Group(_Container):
    def __init__(self, title: str | None = None, description: str | None = None):
        super().__init__(title, description)

    def create_group(self, title: str | None = None, description: str | None = None):
        if sys.version_info >= (3, 14):
            raise ValueError("create_group is not supported in Python 3.14 and above for Group")
        else:
            import warnings
            warnings.warn(
                "Nesting groups is deprecated.",
                category=DeprecationWarning,
                stacklevel=2)
            return super().create_group(title, description)

    def __hash__(self) -> int:
        return id(self)

class _MutuallyExclusiveGroup(_Group):
    def __init__(self, required: bool = False):
        self.required = required
        super(_Group, self).__init__()

    def create_mutually_exclusive_group(self, required: bool = False):
        if sys.version_info >= (3, 14):
            raise ValueError("create_mutually_exclusive_group is not supported in Python 3.14 and above for MutuallyExclusiveGroup")
        else:
            import warnings
            warnings.warn(
                "Nesting mutually exclusive groups is deprecated.",
                category=DeprecationWarning,
                stacklevel=2)
            return super().create_mutually_exclusive_group(required)

def create_group(title: str | None = None, description: str | None = None) -> _Group:
    group = _Group(title, description)
    return group

def create_mutually_exclusive_group(required: bool = False) -> _MutuallyExclusiveGroup:
    group = _MutuallyExclusiveGroup(required)
    return group