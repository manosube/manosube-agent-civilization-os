# Boundary Contract (Phase 9, Issue #43)

```text
DOC_TYPE=BOUNDARY_CONTRACT
DOCUMENT_ID=BINDING-BOUNDARY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

## 1. Position

Boundary declares the project's operating structure -- where its own content lives, and
what is included or excluded within it. Boundary validation is structural and fails
closed. It never reads the filesystem, resolves a symlink, traverses a submodule, scans a
repository, or proves runtime containment.

```text
FILESYSTEM_READ_PERFORMED=false
SYMLINK_RESOLUTION_PERFORMED=false
SUBMODULE_TRAVERSAL_PERFORMED=false
REPOSITORY_SCAN_PERFORMED=false
RUNTIME_CONTAINMENT_PROVEN=false
```

## 2. Shape

Schema: `01_SCHEMA/binding/boundary.schema.json`.

```text
schema_version       const "0.1"
root_paths           array of relative path strings, minItems 1, unique
include_patterns     array of pattern strings, unique
exclude_patterns     array of pattern strings, unique
```

## 3. Escape rejection

`manosube_agent_civilization.binding.engine._reject_unsafe_relative_path` rejects, on
every `root_paths` entry:

```text
leading "/" or "~"          absolute or home-relative path
leading "\\\\"              UNC path
"<letter>:" prefix          drive-letter path
any ".." path segment       traversal
```

## 4. Conflicting declarations

`include_patterns` and `exclude_patterns` may not share a member -- a pattern declared
both included and excluded is a structural contradiction, rejected before any Source
Registration is checked against it (`_reject_conflicting_patterns`).

```text
BOUNDARY_ESCAPE_REJECTED=true
CONFLICTING_INCLUDE_EXCLUDE_REJECTED=true
```

## 5. Relationship to Source Registration

Every `source_registration.locator` must fall within one of `boundary.root_paths`, by real
path segment (never a bare string prefix -- `repo-other/src` does not match root `repo`).
See `SOURCE_REGISTRATION.md` §3.
