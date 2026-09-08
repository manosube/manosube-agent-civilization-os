"""Product Binding (Phase 9, Issue #43): ``KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER``.

Binds a real Human-declared project -- its Objective Revision, Boundary, Authority policy
reference, Source Registrations, Command Policy, and secret-exclusion policy -- into one
immutable, content-addressed Project Binding, atomically adopted alongside genesis State
through the existing State/Store owners. This is not a ninth Kernel element (the same
``KERNEL_ELEMENT=none`` convention Development Binding already uses, per ``00_KERNEL/
KERNEL_INDEX.md`` §4.8's identical precedent for Lineage), and it is not Development
Binding (``03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md``), which governs this
repository's own human/agent development process, never a bound product.

See ``03_BINDING/BINDING_INDEX.md`` for the full contract set.
"""

from .engine import (
    assemble_github_projection_grant_declaration,
    assemble_human_grant_declaration,
    assemble_project_binding,
)
from .errors import BindingError, BindingIdentityError, BindingValidationError
from .identity import (
    github_projection_grant_declaration_id,
    github_projection_grant_declaration_signing_payload,
    human_grant_declaration_id,
    human_grant_declaration_signing_payload,
    project_binding_id,
    verify_github_projection_grant_declaration_identity,
    verify_human_grant_declaration_identity,
    verify_project_binding_identity,
)
from .reference_classification import reject_wrong_kind_reference, resolve_binding_references
from .route import bind_project, declare_github_projection_grant, declare_human_grant
from .signature import (
    SUPPORTED_SIGNATURE_ALGORITHM,
    verify_declaration_signature,
    verify_ed25519_signature,
    verify_github_projection_grant_declaration_signature,
)

__all__ = [
    "SUPPORTED_SIGNATURE_ALGORITHM",
    "BindingError",
    "BindingIdentityError",
    "BindingValidationError",
    "assemble_github_projection_grant_declaration",
    "assemble_human_grant_declaration",
    "assemble_project_binding",
    "bind_project",
    "declare_github_projection_grant",
    "declare_human_grant",
    "github_projection_grant_declaration_id",
    "github_projection_grant_declaration_signing_payload",
    "human_grant_declaration_id",
    "human_grant_declaration_signing_payload",
    "project_binding_id",
    "reject_wrong_kind_reference",
    "resolve_binding_references",
    "verify_declaration_signature",
    "verify_ed25519_signature",
    "verify_github_projection_grant_declaration_identity",
    "verify_github_projection_grant_declaration_signature",
    "verify_human_grant_declaration_identity",
    "verify_project_binding_identity",
]
