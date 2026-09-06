"""Fail-closed Product Binding errors.

The same shape Reflow, Difference, Change and Evidence use: a declared Project Binding
either validates and adopts cleanly, or it is refused before anything is persisted. There is
no partial, best-effort, or silently-narrowed Binding.
"""


class BindingError(ValueError):
    """Base error for a Project Binding declaration that cannot be read, or may not adopt."""


class BindingValidationError(BindingError):
    """A declared Project Binding, or one of its embedded structures, failed schema or
    cross-field validation -- before any Store write."""


class BindingIdentityError(BindingError):
    """The claimed ``project_binding_id`` does not reproduce from the declared body's own
    semantic fields, or the Binding and its genesis State disagree on ``project_id``."""
