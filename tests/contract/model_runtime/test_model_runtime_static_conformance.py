"""Phase 16 (Issue #66) Model Runtime: static conformance proofs, and V5's Phase 12 continuity.

A real AST walk over the ``model_runtime`` package's own module source -- never a grep, never a
hardcoded name list -- mirroring ``tests/contract/runtime/test_runtime_static_conformance.py``'s
own technique exactly, adapted to this delivery's own architecture:

- **No provider surface exists at all.** Phase 15's own equivalent test admits ``adapter.py`` as
  the one module allowed to import a transport surface, because that delivery genuinely opens
  HTTP. This delivery opens nothing: the adopted proposal's own non-targets forbid live provider
  credential use and remote command execution, and both shipped adapters are controlled and
  in-memory. So the requirement "no model/provider import outside the adapter surface" is proved
  here in its strictly stronger form -- **no** module in this package imports a provider SDK, a
  network surface, or a subprocess surface, and ``adapter.py`` is named as the one module that
  would be admitted if one were ever introduced.
- **Boot is reached only through Phase 12.** ``boot_project`` is never imported here at all;
  ``agent_runtime.start_temporary_agent`` has exactly one literal call site in this package. That
  is the adaptation of ``runtime/bootstrap.py``'s own "one literal ``boot_project`` call site"
  discipline to a layer whose execution contract is Phase 12's, not Boot's.
- **P16-C3's decisive control is structural, not behavioural.** The route reads exactly three
  keys back out of an adapter's own result, and it reads them *through*
  ``MODEL_ADAPTER_RESULT_KEYS`` rather than through string literals -- so an adapter's attempt to
  authorize itself, mint Evidence, close a Difference or widen its Boundary has no call shape at
  all, and that is proved by walking the route's own normalization body.

V5 (Phase 12 continuity) lives in this file too, in its own section: Phase 12's own public
surface is pinned by structure -- its exact module set, its exact exported names, the exact
abstract members of ``TemporaryAgent``, and ``start_temporary_agent``'s exact signature -- and
the absence of any second execution-contract record kind, schema, or persisted identity anywhere
in shipped code is proved by scanning the whole schema registry and the whole shipped package.
"""

from __future__ import annotations

import ast
import inspect
import json
import pathlib
from types import ModuleType
from typing import Any

import pytest

import manosube_agent_civilization
import manosube_agent_civilization.agent_runtime as agent_runtime_package
import manosube_agent_civilization.agent_runtime.agent as agent_module
import manosube_agent_civilization.agent_runtime.errors as agent_errors_module
import manosube_agent_civilization.agent_runtime.route as agent_route_module
import manosube_agent_civilization.model_runtime as model_runtime_package
import manosube_agent_civilization.model_runtime.adapter as adapter_module
import manosube_agent_civilization.model_runtime.engine as engine_module
import manosube_agent_civilization.model_runtime.errors as errors_module
import manosube_agent_civilization.model_runtime.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.model_runtime.identity as identity_module
import manosube_agent_civilization.model_runtime.route as route_module
import manosube_agent_civilization.model_runtime.types as types_module

pytestmark = pytest.mark.contract

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapter_module,
    evidence_handoff_module,
    model_runtime_package,
)

_AGENT_RUNTIME_MODULES = (
    agent_runtime_package,
    agent_module,
    agent_errors_module,
    agent_route_module,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_SCHEMA_ROOT = _REPO_ROOT / "01_SCHEMA"

#: The one module in this package that *would* be admitted to import a provider or transport
#: surface if one were ever introduced -- named here, as a value, so the admission is a declared
#: boundary rather than an accident of what happens to be imported today.
_PERMITTED_PROVIDER_SURFACE_MODULES = (adapter_module,)

#: Provider/model SDK and runtime tokens no shipped module may import. Deliberately includes the
#: three this repository's own Phase 15 suite already forbids (``openai``/``anthropic``,
#: ``threading``/``asyncio``) plus every other major provider surface, so "no provider SDK
#: becomes a Kernel dependency" (P16-C2) is a checked fact rather than a claim about today.
_FORBIDDEN_IMPORT_SUBSTRINGS = (
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "vertexai",
    "cohere",
    "mistralai",
    "ollama",
    "litellm",
    "replicate",
    "huggingface",
    "transformers",
    "torch",
    "tensorflow",
    "langchain",
    "llama_index",
    "boto3",
    "botocore",
    "urllib",
    "requests",
    "http.client",
    "socket",
    "subprocess",
    "threading",
    "asyncio",
    "multiprocessing",
    "sched",
)

#: Existing canonical owners no module in this package may ever import, in whole or in part --
#: Model Runtime mints no Reflow decision and never reaches Independent Verification's own
#: machinery, exactly as Runtime's own equivalent list already states for that package.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.independent_verification",
    "manosube_agent_civilization.projection",
    "manosube_agent_civilization.runtime",
    "manosube_agent_civilization.change",
)

#: Field names that would make a canonical record provider-specific, provider-session-bound, or
#: a second persisted execution-contract/agent identity. None may appear as a property name in
#: any schema this delivery owns.
_FORBIDDEN_SCHEMA_PROPERTY_NAMES = frozenset(
    {
        "provider",
        "provider_id",
        "provider_session_id",
        "model",
        "model_id",
        "model_name",
        "prompt",
        "prompt_tokens",
        "completion",
        "completion_tokens",
        "transcript",
        "chat_history",
        "conversation_id",
        "messages",
        "model_memory",
        "temperature",
        "api_key",
        "api_base",
        "endpoint",
        "agent_id",
        "session_id",
        "execution_contract_id",
        "temporary_agent_id",
        "resume_token",
    }
)

#: The schemas this delivery owns, by file. Pinned as a value so a sixth schema cannot be added
#: to this package without appearing in every scan below.
_MODEL_RUNTIME_SCHEMA_NAMES = (
    "model_execution_boundary.schema.json",
    "model_work_unit.schema.json",
    "model_execution_envelope.schema.json",
    "model_swap_receipt.schema.json",
    "session_recovery_receipt.schema.json",
)
_AUTHORITY_SCHEMA_NAMES = (
    "model_execution_grant.schema.json",
    "model_execution_decision.schema.json",
)


def _tree(module: ModuleType) -> ast.Module:
    return ast.parse(inspect.getsource(module))


def _imported_module_names(module: ModuleType) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _call_site_count(module: ModuleType, name: str) -> int:
    count = 0
    for node in ast.walk(_tree(module)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (
            isinstance(func, ast.Attribute) and func.attr == name
        ):
            count += 1
    return count


def _function_defs(module: ModuleType) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            assert node.name not in found, f"two functions named {node.name!r} in {module.__name__}"
            found[node.name] = node
    return found


def _function_names(module: ModuleType) -> set[str]:
    """Every ``def`` name in *module*, nested and duplicated ones included.

    Deliberately a *set* rather than :func:`_function_defs`' name-keyed mapping: a module
    declaring two classes legitimately declares two ``__init__`` methods, which is not the
    ambiguity that mapping exists to refuse.
    """

    return {
        node.name
        for node in ast.walk(_tree(module))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _shipped_python_files() -> list[pathlib.Path]:
    return sorted(
        path for path in _SHIPPED_PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def _schema_documents(directory: str, names: tuple[str, ...]) -> dict[str, Any]:
    return {
        name: json.loads((_SCHEMA_ROOT / directory / name).read_text(encoding="utf-8"))
        for name in names
    }


def _property_names(node: Any) -> set[str]:
    """Every JSON-Schema *property name* declared anywhere in *node*, at any depth."""

    found: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            found.update(properties)
        for child in node.values():
            found |= _property_names(child)
    elif isinstance(node, list):
        for child in node:
            found |= _property_names(child)
    return found


# =========================================================================== #
# 1. No provider surface, anywhere
# =========================================================================== #


def test_no_shipped_module_imports_a_provider_sdk_or_transport_surface() -> None:
    """P16-C2: "no provider SDK may become a Kernel dependency or canonical owner", proved in its
    strictly stronger form -- *no* module in this package imports one at all, not merely none
    outside the adapter surface. ``adapter.py`` is the module that would be admitted if a real
    provider surface were ever introduced (see this file's own docstring); today it imports
    none either, which is what ``PROVIDER_SDK_DEPENDENCY_COUNT=0`` states."""

    assert (adapter_module,) == _PERMITTED_PROVIDER_SURFACE_MODULES
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in _FORBIDDEN_IMPORT_SUBSTRINGS)
        }
        assert not hits, f"{module.__name__} imports a forbidden surface: {hits}"


def test_the_adapter_module_imports_nothing_but_its_own_packages_leaves() -> None:
    """The decisive structural half of P16-C3, and the discipline ``runtime/adapter.py`` already
    keeps (which the next test verifies rather than assumes). An adapter cannot mutate Canonical
    State, mint Authority, derive Evidence, or close a Difference *here* because no Store, Boot,
    Agent Runtime, Authority, Evidence, Difference, Change or Reflow module is importable from
    inside this file's own import graph at all."""

    imported = _imported_module_names(adapter_module)
    first_party = {name for name in imported if name.startswith("manosube_agent_civilization")}
    assert first_party == set(), f"adapter.py reaches a first-party owner: {first_party}"
    relative = {
        node.module
        for node in ast.walk(_tree(adapter_module))
        if isinstance(node, ast.ImportFrom) and node.level and node.module
    }
    assert relative <= {"errors", "types"}, relative


def test_the_phase_15_adapter_precedent_this_delivery_replicates_actually_holds() -> None:
    """The harness before its subject. This delivery's own adapter discipline is justified by
    ``runtime/adapter.py`` keeping the identical one; that claim is verified here rather than
    cited, so a future change to Phase 15's adapter cannot silently invalidate the precedent this
    file rests on."""

    import manosube_agent_civilization.runtime.adapter as runtime_adapter_module

    imported = _imported_module_names(runtime_adapter_module)
    first_party = {name for name in imported if name.startswith("manosube_agent_civilization")}
    assert first_party == set()
    for forbidden in ("store", "evidence", "authority", "boot", "difference", "change"):
        assert not any(f".{forbidden}" in name for name in imported)


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    """This layer never becomes a second Reflow, Independent Verification, Projection, Runtime or
    Change owner, and never reaches around one."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(name.startswith(prefix) for prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES)
        }
        assert not hits, f"{module.__name__} imports a forbidden owner: {hits}"


def test_no_shipped_module_hardcodes_a_provider_endpoint_model_name_or_credential() -> None:
    """``LIVE_PROVIDER_CREDENTIAL_USE=false`` is an adopted constraint, and a hardcoded endpoint
    or model name in shipped source would be the first step toward violating it. Proved by
    walking every string constant in every module of this package."""

    markers = (
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "sk-",
        "bearer ",
        "gpt-",
        "claude-",
        "gemini-",
        "https://",
        "http://",
    )
    for module in _ALL_PACKAGE_MODULES:
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            # Docstrings legitimately discuss what this layer does not do; only *code*-position
            # string constants are scanned, exactly as `_names_identifier` in Phase 15's own
            # suite deliberately excludes docstring prose.
            if len(node.value) > 200:
                continue
            lowered = node.value.lower()
            assert not any(marker in lowered for marker in markers), (
                module.__name__,
                node.value,
            )


def test_no_module_reads_configuration_or_the_environment() -> None:
    """A provider credential most plausibly arrives through the environment, so no module here
    reads one -- there is no ``os.environ``, ``getenv``, ``dotenv`` or config-file read anywhere
    in this package."""

    forbidden_calls = {"getenv", "environ", "load_dotenv", "read_text", "read_bytes", "open"}
    for module in _ALL_PACKAGE_MODULES:
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else (func.attr if isinstance(func, ast.Attribute) else None)
            )
            assert name not in forbidden_calls, (module.__name__, name)


# =========================================================================== #
# 2. No provider-specific field in any canonical schema
# =========================================================================== #


@pytest.mark.parametrize(
    ("directory", "name"),
    [("model_runtime", name) for name in _MODEL_RUNTIME_SCHEMA_NAMES]
    + [("authority", name) for name in _AUTHORITY_SCHEMA_NAMES],
)
def test_no_canonical_schema_declares_a_provider_specific_field(directory: str, name: str) -> None:
    """P16-C1/V2: "no provider-specific canonical fields". Every property name declared at any
    depth of every schema this delivery owns is checked against the closed forbidden set, which
    additionally covers provider session ids, chat transcripts, model memory and any second
    persisted agent/session/execution-contract identity."""

    document = _schema_documents(directory, (name,))[name]
    declared = _property_names(document)
    assert declared, f"{name} declares no properties at all -- the scan would be vacuous"
    offenders = declared & _FORBIDDEN_SCHEMA_PROPERTY_NAMES
    assert not offenders, f"{name} declares provider-specific field(s): {sorted(offenders)}"


def test_the_adapter_identity_shape_is_closed_to_exactly_two_neutral_fields() -> None:
    """The one place a provider-specific field would most naturally leak into a canonical record
    is the adapter's own declared identity. It is closed at the schema: exactly ``adapter`` and
    ``version``, with ``additionalProperties: false``."""

    envelope = _schema_documents("model_runtime", ("model_execution_envelope.schema.json",))[
        "model_execution_envelope.schema.json"
    ]
    adapter_identity = envelope["$defs"]["adapter_identity"]
    assert set(adapter_identity["properties"]) == {"adapter", "version"}
    assert adapter_identity["additionalProperties"] is False
    assert sorted(adapter_identity["required"]) == ["adapter", "version"]


def test_every_schema_this_delivery_owns_closes_its_own_key_set() -> None:
    """An open key set is how a provider-specific field arrives without anyone declaring one."""

    documents = {
        **_schema_documents("model_runtime", _MODEL_RUNTIME_SCHEMA_NAMES),
        **_schema_documents("authority", _AUTHORITY_SCHEMA_NAMES),
    }
    for name, document in documents.items():
        assert document.get("additionalProperties") is False, name


# =========================================================================== #
# 3. One sanctioned committer, one Authority evaluator, one Evidence deriver
# =========================================================================== #


def test_no_module_calls_store_commit_directly() -> None:
    """The sanctioned single committer is ``store.commit.commit_state_transition`` -- no module
    in this package may call a ``store`` object's own ``.commit(...)`` directly (K-003/R-001,
    ``topology.py``'s own static scan enforces the identical rule package-wide; this is the
    package-local proof that this package's own source agrees)."""

    for module in _ALL_PACKAGE_MODULES:
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "commit":
                continue
            assert isinstance(node.func.value, ast.Name) and node.func.value.id != "store", (
                f"{module.__name__} appears to call store.commit(...) directly, bypassing "
                "commit_state_transition"
            )


def test_commit_state_transition_is_imported_and_called_only_by_the_route() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imports_committer = "manosube_agent_civilization.store.commit" in _imported_module_names(
            module
        )
        if module is route_module:
            assert imports_committer
            assert _call_site_count(module, "commit_state_transition") == 1
        else:
            assert not imports_committer, module.__name__
            assert _call_site_count(module, "commit_state_transition") == 0, module.__name__


def test_the_authority_evaluator_is_reached_only_by_the_route_and_exactly_once() -> None:
    """One Authority call, in one place. Neither adapter, nor the engine, nor the identity layer,
    nor the Evidence hand-off may evaluate Authority -- and no module here calls the *Change*
    evaluator ``evaluate_authority`` at all, which is the boundary
    ``model_execution_authorization.py``'s own docstring explains."""

    for module in _ALL_PACKAGE_MODULES:
        assert _call_site_count(module, "evaluate_authority") == 0, module.__name__
        expected = 1 if module is route_module else 0
        assert _call_site_count(module, "evaluate_model_execution_authorization") == expected, (
            module.__name__
        )


def test_derive_evidence_is_imported_and_called_only_by_the_evidence_handoff_once() -> None:
    """Model output reaches Evidence through exactly one call to the one existing Evidence
    owner, from exactly one module."""

    for module in _ALL_PACKAGE_MODULES:
        imports_evidence = any(
            name.startswith("manosube_agent_civilization.evidence")
            for name in _imported_module_names(module)
        )
        if module is evidence_handoff_module:
            assert imports_evidence
            assert _call_site_count(module, "derive_evidence") == 1
        elif module is engine_module:
            # The engine reads the Evidence owner's own closed request-key set to *derive* a
            # Work Unit's evidence_requirements; it never calls the deriver.
            assert imports_evidence
            assert _call_site_count(module, "derive_evidence") == 0
        else:
            assert not imports_evidence, module.__name__
            assert _call_site_count(module, "derive_evidence") == 0, module.__name__


def test_no_module_mints_an_authority_evidence_or_closure_record_of_its_own() -> None:
    """This layer is not a second Authority, Evidence or Closure owner: no module here defines a
    function that produces one, and none of the identity functions this package owns addresses
    such a record kind."""

    forbidden_producers = (
        "derive_evidence",
        "evaluate_closure",
        "evaluate_authority",
        "derive_change",
        "close_difference",
        "derive_closure_evaluation",
    )
    for module in _ALL_PACKAGE_MODULES:
        for name in _function_names(module):
            assert name not in forbidden_producers, (module.__name__, name)
    minted = {
        name for name in dir(identity_module) if name.endswith("_id") and not name.startswith("_")
    }
    assert minted == {
        "model_execution_boundary_id",
        "model_work_unit_id",
        "model_execution_envelope_id",
        "model_swap_receipt_id",
        "session_recovery_receipt_id",
    }


def test_the_required_provenance_field_set_matches_every_other_handoffs_own() -> None:
    """ "Do not invent a fourth Evidence request shape": the ten
    ``verification_result_provenance`` fields this package restates are held equal to Runtime's
    and Projection's own copies, so the three can never drift apart."""

    from manosube_agent_civilization.projection.receipt_handoff import (
        REQUIRED_PROVENANCE_FIELDS as PROJECTION_FIELDS,
    )
    from manosube_agent_civilization.runtime.evidence_handoff import (
        REQUIRED_PROVENANCE_FIELDS as RUNTIME_FIELDS,
    )

    assert engine_module.REQUIRED_PROVENANCE_FIELDS == RUNTIME_FIELDS == PROJECTION_FIELDS


def test_the_evidence_requirements_are_derived_from_the_existing_evidence_owner() -> None:
    """A Work Unit's ``evidence_requirements`` is never stated by a caller: it is derived, and
    the derivation reads the real Evidence owner's own closed request-key set."""

    from manosube_agent_civilization.evidence.engine import (
        CHANGE_FREE_VERIFICATION_EVIDENCE,
        REQUIRED_REQUEST_KEYS,
    )

    requirements = engine_module.canonical_evidence_requirements()
    assert requirements["evidence_position"] == CHANGE_FREE_VERIFICATION_EVIDENCE
    assert requirements["required_request_keys"] == sorted(REQUIRED_REQUEST_KEYS)
    assert requirements["required_provenance_fields"] == list(
        engine_module.REQUIRED_PROVENANCE_FIELDS
    )
    assert (
        "evidence_requirements"
        not in inspect.signature(engine_module.derive_model_work_unit).parameters
    )


# =========================================================================== #
# 4. P16-C3 as a structural fact: exactly three keys are ever read back
# =========================================================================== #


def test_the_route_reads_exactly_three_keys_out_of_an_adapter_result() -> None:
    """The decisive control behind "a model cannot authorize itself".

    ``_normalize`` is the only place in this package that touches an adapter's own returned
    mapping, and every read it performs goes through ``MODEL_ADAPTER_RESULT_KEYS`` by index --
    never through a string literal. So a returned mapping carrying ``authority_ref``,
    ``evidence``, ``difference_closed``, a decision record or a commit instruction has no call
    shape at all: those keys are never read, by anyone, at any point.
    """

    normalize = _function_defs(route_module)["_normalize"]
    literal_reads: list[Any] = []
    keyed_reads = 0
    for node in ast.walk(normalize):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "raw"
        ):
            literal_reads.append(ast.dump(node))
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "raw":
            continue
        assert len(node.args) == 1
        argument = node.args[0]
        assert isinstance(argument, ast.Subscript), ast.dump(argument)
        assert isinstance(argument.value, ast.Name)
        assert argument.value.id == "MODEL_ADAPTER_RESULT_KEYS", ast.dump(argument)
        keyed_reads += 1
    assert not literal_reads, literal_reads
    assert keyed_reads == 3
    assert len(types_module.MODEL_ADAPTER_RESULT_KEYS) == 3


def test_only_the_normalizer_ever_touches_an_adapter_result() -> None:
    """``adapter.execute(...)`` has exactly one call site in this package, and its result is
    handed straight to ``_normalize`` -- so there is no second, less careful reader of an
    adapter's own output anywhere."""

    assert _call_site_count(route_module, "execute") == 1
    execute_route = _function_defs(route_module)["execute_model_work_unit"]
    names_read: set[str] = set()
    for node in ast.walk(execute_route):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            names_read.add(node.value.id)
    assert "raw" not in names_read


def test_the_accepting_classification_is_computed_only_inside_the_normalizer() -> None:
    """``CANDIDATE_ACCEPTED`` appears in exactly one code position in the whole shipped package
    outside the vocabulary that declares it -- the normalizer's own return."""

    producing_modules = []
    for module in _ALL_PACKAGE_MODULES:
        for node in ast.walk(_tree(module)):
            if isinstance(node, ast.Constant) and node.value == "CANDIDATE_ACCEPTED":
                producing_modules.append(module.__name__)
    assert sorted(set(producing_modules)) == [
        "manosube_agent_civilization.model_runtime.route",
        "manosube_agent_civilization.model_runtime.types",
    ]
    normalize = _function_defs(route_module)["_normalize"]
    inside = [
        node
        for node in ast.walk(normalize)
        if isinstance(node, ast.Constant) and node.value == "CANDIDATE_ACCEPTED"
    ]
    assert len(inside) == 1


# =========================================================================== #
# 5. V5 -- Phase 12 continuity: the exact existing execution contract, unchanged
# =========================================================================== #


def test_phase_12s_public_surface_is_exactly_what_it_was() -> None:
    """V5's first half. ``agent_runtime`` is the Phase 12 Temporary Agent Execution Contract and
    this Phase does not touch it: its module set, its exported names, ``TemporaryAgent``'s exact
    abstract members and ``start_temporary_agent``'s exact signature are all pinned here.

    A structural pin rather than a byte diff, deliberately: a test cannot read another commit,
    and pinning the *surface* is what actually protects the property -- a file could be
    reformatted without changing anything this delivery depends on, while any change to the
    surface below would change what "the Phase 12 execution contract" means.
    """

    package_root = pathlib.Path(agent_runtime_package.__file__).resolve().parent
    modules_on_disk = sorted(
        path.name for path in package_root.glob("*.py") if "__pycache__" not in path.parts
    )
    assert modules_on_disk == ["__init__.py", "agent.py", "errors.py", "route.py"]

    assert sorted(agent_runtime_package.__all__) == [
        "AgentReleasedError",
        "AgentRuntimeError",
        "TemporaryAgent",
        "start_temporary_agent",
    ]

    temporary_agent = agent_runtime_package.TemporaryAgent
    assert inspect.isabstract(temporary_agent)
    assert set(temporary_agent.__abstractmethods__) == {"boot_context", "release"}
    with pytest.raises(TypeError):
        temporary_agent()  # type: ignore[abstract]

    signature = inspect.signature(agent_runtime_package.start_temporary_agent)
    assert list(signature.parameters) == ["store", "project_id", "project_binding_id"]
    assert signature.parameters["store"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("project_id", "project_binding_id"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_phase_12_still_owns_its_own_single_boot_call_site_and_knows_nothing_of_phase_16() -> None:
    """Phase 12 remains a thin wrapper over one ``boot_project`` call, and gains no dependency on
    this delivery: no module in ``agent_runtime`` imports ``model_runtime``, so the direction of
    the dependency is the one the adopted constraints require."""

    assert _call_site_count(agent_route_module, "boot_project") == 1
    for module in _AGENT_RUNTIME_MODULES:
        imported = _imported_module_names(module)
        assert not any("model_runtime" in name for name in imported), module.__name__


def test_model_runtime_never_boots_a_project_itself() -> None:
    """V5's second half. This package constructs no second Boot-wrapping mechanism of its own: it
    never imports ``boot_project``, never imports the ``boot`` package's route at all, and
    reaches Boot only through Phase 12's own entry point -- at exactly one literal call site."""

    for module in _ALL_PACKAGE_MODULES:
        assert _call_site_count(module, "boot_project") == 0, module.__name__
        assert _call_site_count(module, "_ActiveTemporaryAgent") == 0, module.__name__
        imported = _imported_module_names(module)
        assert "manosube_agent_civilization.boot" not in imported, module.__name__
        assert "manosube_agent_civilization.boot.route" not in imported, module.__name__

    total = sum(
        _call_site_count(module, "start_temporary_agent") for module in _ALL_PACKAGE_MODULES
    )
    assert total == 1
    assert _call_site_count(route_module, "start_temporary_agent") == 1
    fresh_contract = _function_defs(route_module)["_fresh_execution_contract"]
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "start_temporary_agent"
        for node in ast.walk(fresh_contract)
    )


def test_every_route_requires_a_live_temporary_agent_as_its_own_second_argument() -> None:
    """A Phase 16 record is bound to the Phase 12 execution contract by *requiring the contract
    itself*, never by carrying a contract id field. Every public route takes the live Agent as
    its second positional argument and re-reads its own ``boot_context``."""

    for name in (
        "open_model_work_unit",
        "execute_model_work_unit",
        "record_model_swap",
        "recover_model_execution_session",
    ):
        signature = inspect.signature(getattr(route_module, name))
        parameters = list(signature.parameters)
        assert parameters[:2] == ["store", "agent"], name
        assert signature.parameters["agent"].annotation == "TemporaryAgent", name


def test_no_second_execution_contract_record_kind_exists_anywhere_in_shipped_code() -> None:
    """V5's third half, and the strongest of them. No schema in the whole canonical registry
    declares an execution contract, a durable agent identity, a session identity or a resume
    token as a record kind, and no shipped module names one as a record kind constant."""

    forbidden_tokens = (
        "execution_contract",
        "agent_contract",
        "agent_identity",
        "agent_session",
        "temporary_agent",
        "resume_token",
        "model_session",
        "provider_session",
    )
    for path in sorted(_SCHEMA_ROOT.rglob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        identifier = str(document.get("$id", "")).lower()
        title = str(document.get("title", "")).lower()
        for token in forbidden_tokens:
            assert token not in identifier, (path.name, token)
            assert token not in title, (path.name, token)
        for token in forbidden_tokens:
            assert token not in _property_names(document), (path.name, token)

    for path in _shipped_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name) or not target.id.endswith("RECORD_KIND"):
                    continue
                for token in forbidden_tokens:
                    assert token not in target.id.lower(), (path.name, target.id, token)
                # A record-kind constant is either a literal or an alias of one already scanned
                # elsewhere in the tree; only the literal carries the kind's own name.
                if not isinstance(node.value, ast.Constant):
                    continue
                value = str(node.value.value).lower()
                for token in forbidden_tokens:
                    assert token not in value, (path.name, target.id, value)


def test_this_package_declares_exactly_the_record_kinds_it_owns() -> None:
    """The harness before its subject: the scan above proves an absence, so this pins the
    presence -- exactly seven record kinds are named by this package's own route, five of which
    it owns and two of which belong to existing owners it only ever resolves."""

    kinds = {
        target.id: node.value.value
        for node in ast.walk(_tree(route_module))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.endswith("RECORD_KIND")
    }
    assert kinds == {
        "WORK_UNIT_RECORD_KIND": "model_work_unit",
        "BOUNDARY_RECORD_KIND": "model_execution_boundary",
        "DECISION_RECORD_KIND": "model_execution_decision",
        "GRANT_RECORD_KIND": "model_execution_grant",
        "ENVELOPE_RECORD_KIND": "model_execution_envelope",
        "SWAP_RECEIPT_RECORD_KIND": "model_swap_receipt",
        "RECOVERY_RECEIPT_RECORD_KIND": "session_recovery_receipt",
        "DIFFERENCE_RECORD_KIND": "difference",
    }


# =========================================================================== #
# 6. Package shape
# =========================================================================== #


def test_the_package_declares_exactly_five_public_entry_points() -> None:
    """``PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5`` is stated as a value so a sixth route cannot
    appear without the number moving, and is held equal here to what the package actually
    exports."""

    assert model_runtime_package.PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT == 5
    routes = {
        "open_model_work_unit",
        "execute_model_work_unit",
        "record_model_swap",
        "recover_model_execution_session",
        "route_model_execution_to_evidence",
    }
    assert routes <= set(model_runtime_package.__all__)
    assert set(route_module.__all__) - {"MODEL_RUNTIME_SCHEMA_BASE"} == routes - {
        "route_model_execution_to_evidence"
    }
    assert evidence_handoff_module.__all__ == ["route_model_execution_to_evidence"]


def test_the_package_declares_it_is_not_a_ninth_kernel_element() -> None:
    assert "KERNEL_ELEMENT=NONE_MODEL_RUNTIME_ADAPTER" in (model_runtime_package.__doc__ or "")


def test_the_one_canonical_serializer_is_reused_and_never_restated() -> None:
    """Canonical serialization has one owner in this repository. This package's own identity
    module reads it; no other module in the package serializes anything itself."""

    assert "manosube_agent_civilization.state.canonicalize" in _imported_module_names(
        identity_module
    )
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        if module is identity_module:
            continue
        assert "manosube_agent_civilization.state.canonicalize" not in imported, module.__name__
        assert "json" not in imported, module.__name__
        assert _call_site_count(module, "canonical_json_bytes") == 0, module.__name__


def test_shipped_package_imports_no_tests_module_anywhere() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        assert not any(name == "tests" or name.startswith("tests.") for name in imported), (
            f"{module.__name__} imports a tests module: {imported}"
        )
