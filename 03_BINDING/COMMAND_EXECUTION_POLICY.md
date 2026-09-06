# Command Execution Policy (Phase 9, Issue #43)

```text
DOC_TYPE=COMMAND_EXECUTION_POLICY_CONTRACT
DOCUMENT_ID=BINDING-COMMAND-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

## 1. Position

Command Policy is a ceiling, never an authority grant. It may narrow which command
*classes* a later (not-yet-implemented) Phase 10 Boot may consider; it can never grant
Authority, execute a command, invoke a shell, or authorize an external operation.

```text
COMMAND_POLICY_GRANTS_AUTHORITY=false
COMMAND_EXECUTION_PERFORMED=false
```

## 2. Shape

Schema: `01_SCHEMA/binding/command_policy.schema.json`.

```text
schema_version              const "0.1"
allowed_command_classes      array, unique, items from a closed enum:
                              READ_ONLY_QUERY, BUILD, TEST, LINT, FORMAT_CHECK
max_commands_per_change      integer >= 0
```

## 3. Why this shape forecloses the required negative controls structurally

No field ever accepts a raw command string, a shell fragment, or a wildcard. Every entry
in `allowed_command_classes` must be one of five named classes -- there is no field a
caller could populate with `"*"`, `"rm -rf /"`, or any other command text, because the
schema never has a slot for command text at all. `additionalProperties: false` closes the
remaining route: any attempt to add an `authority_grant`, `execute_now`, or similarly
named field fails schema validation before it ever reaches engine logic.

```text
UNCONSTRAINED_WILDCARD_ACCEPTED=false
SHELL_TEXT_EMBEDDING_ACCEPTED=false
COMMAND_POLICY_AUTHORITY_GRANT_FIELD_ACCEPTED=false
```
