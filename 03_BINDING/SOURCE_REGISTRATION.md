# Source Registration (Phase 9, Issue #43)

```text
DOC_TYPE=SOURCE_REGISTRATION_CONTRACT
DOCUMENT_ID=BINDING-SOURCE-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

## 1. Position

A Source Registration declares that a specific location within the Boundary is trusted
material. It grants no Observation, Evidence, Difference, Authority, or permission to act
-- see `TRUST_MODEL.md` §3.

```text
SOURCE_REGISTRATION_GRANTS_OBSERVATION=false
SOURCE_REGISTRATION_GRANTS_EVIDENCE=false
SOURCE_REGISTRATION_GRANTS_AUTHORITY=false
```

## 2. Shape

Schema: `01_SCHEMA/binding/source_registration.schema.json`.

```text
schema_version       const "0.1"
source_id             common/identity.schema.json
source_type           closed enum: GIT_REPOSITORY, FILESYSTEM_DIRECTORY, PACKAGE_ARTIFACT
locator               relative path/locator string
include_patterns      array, unique
exclude_patterns      array, unique
```

An unrecognized `source_type` fails schema validation immediately (closed enum,
`additionalProperties: false`).

## 3. Cross-field checks

```text
locator escape                same rejection as Boundary root paths (BOUNDARY_CONTRACT.md
                               §3): absolute, home-relative, drive-letter, UNC, or
                               traversal locators are refused
locator outside the Boundary   locator must fall within one of the Binding's own
                               boundary.root_paths, by real path segment
duplicate source_id            two registrations may not share a source_id
duplicate (type, locator)      two registrations may not share a (source_type, locator)
                               pair under different ids either
own conflicting patterns       a registration's own include_patterns/exclude_patterns may
                               not share a member
```

All four checks run in `manosube_agent_civilization.binding.engine.
assemble_project_binding`, before any identity is minted or anything is persisted.
