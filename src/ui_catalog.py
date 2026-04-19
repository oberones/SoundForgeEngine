"""Metadata builders for the control dashboard UI."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Literal, Optional

from pydantic import BaseModel, Field

from config import RootConfig


ControlKind = Literal["scalar", "toggle", "enum", "mapping", "collection", "action", "readonly"]
Availability = Literal["available", "unavailable", "unsupported-context"]
PersistBehavior = Literal["session-only", "persistable", "readonly"]
DirtyState = Literal["clean", "dirty", "conflicted"]


DOMAIN_METADATA: Dict[str, Dict[str, Any]] = {
    "sequencer": {
        "title": "Sequencer",
        "description": "Core musical timing, pitch, and pattern controls.",
        "sort_order": 10,
    },
    "midi": {
        "title": "MIDI",
        "description": "MIDI routing, channels, clocking, and CC profile configuration.",
        "sort_order": 20,
    },
    "hid": {
        "title": "HID Controls",
        "description": "Arcade button and joystick mappings for physical control input.",
        "sort_order": 30,
    },
    "mapping": {
        "title": "Mappings",
        "description": "Dynamic mappings between incoming controls and semantic actions.",
        "sort_order": 40,
    },
    "scales": {
        "title": "Scales",
        "description": "Available musical scales used by the sequencer and modes.",
        "sort_order": 50,
    },
    "mutation": {
        "title": "Mutation",
        "description": "Automatic variation and mutation behavior for the running engine.",
        "sort_order": 60,
    },
    "idle": {
        "title": "Idle",
        "description": "Ambient fallback behavior when the engine is left untouched.",
        "sort_order": 70,
    },
    "synth": {
        "title": "Synth",
        "description": "Synth backend and voice-allocation configuration.",
        "sort_order": 80,
    },
    "logging": {
        "title": "Logging",
        "description": "Diagnostics and operator-facing logging settings.",
        "sort_order": 90,
    },
    "api": {
        "title": "API",
        "description": "Remote-control service exposure and runtime API settings.",
        "sort_order": 100,
    },
    "cc_profiles": {
        "title": "CC Profiles",
        "description": "Custom CC profile definitions available to external hardware.",
        "sort_order": 110,
    },
}


SPECIAL_LABELS = {
    "api": "API",
    "bpm": "BPM",
    "cc": "CC",
    "cc_profiles": "CC Profiles",
    "hid": "HID",
    "midi": "MIDI",
    "nts1": "NTS-1",
}


@dataclass(frozen=True)
class ActionMetadata:
    action_id: str
    label: str
    description: str
    confirmation_required: bool = False
    parameter_schema: Optional[Dict[str, Any]] = None
    availability: Availability = "available"
    result_message_template: str = ""


ACTION_CATALOG: List[ActionMetadata] = [
    ActionMetadata(
        action_id="trigger_step",
        label="Trigger Step",
        description="Advance the sequencer once and emit an immediate note event.",
        result_message_template="Manual step trigger sent.",
    ),
    ActionMetadata(
        action_id="tempo_up",
        label="Tempo Up",
        description="Increase the current tempo using the semantic-action handler.",
        result_message_template="Tempo increased.",
    ),
    ActionMetadata(
        action_id="tempo_down",
        label="Tempo Down",
        description="Decrease the current tempo using the semantic-action handler.",
        result_message_template="Tempo decreased.",
    ),
    ActionMetadata(
        action_id="direction_left",
        label="Direction Left",
        description="Move the direction control left through the supported patterns.",
        result_message_template="Direction moved left.",
    ),
    ActionMetadata(
        action_id="direction_right",
        label="Direction Right",
        description="Move the direction control right through the supported patterns.",
        result_message_template="Direction moved right.",
    ),
    ActionMetadata(
        action_id="set_direction_pattern",
        label="Set Direction Pattern",
        description="Switch the sequencer direction pattern using the semantic-action surface.",
        parameter_schema={
            "type": "string",
            "enum": ["forward", "backward", "ping_pong", "random", "fugue", "song"],
        },
        result_message_template="Direction pattern updated.",
    ),
    ActionMetadata(
        action_id="set_step_pattern",
        label="Set Step Pattern",
        description="Apply a named step-pattern preset through the action handler.",
        parameter_schema={"type": "string"},
        result_message_template="Step pattern updated.",
    ),
    ActionMetadata(
        action_id="reload_cc_profile",
        label="Reload CC Profile",
        description="Reload the active CC profile configuration for external hardware.",
        confirmation_required=True,
        result_message_template="CC profile reload requested.",
    ),
]


class ControlDefinition(BaseModel):
    id: str
    path: str
    control_kind: ControlKind
    label: str
    description: str = ""
    value_type: str
    current_value: Any = None
    default_value: Any = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    ui_hint: str = ""
    availability: Availability = "available"
    persist_behavior: PersistBehavior = "persistable"
    revision: str
    dirty_state: DirtyState = "clean"


class ControlDomain(BaseModel):
    id: str
    title: str
    description: str = ""
    sort_order: int
    controls: List[ControlDefinition]


class ActionDefinition(BaseModel):
    id: str
    label: str
    description: str = ""
    confirmation_required: bool = False
    availability: Availability = "available"
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)
    result_message_template: str = ""


def _titleize(segment: str) -> str:
    parts = re.split(r"[_\-.]+", segment)
    pretty: List[str] = []
    for part in parts:
        if not part:
            continue
        lower = part.lower()
        if lower in SPECIAL_LABELS:
            pretty.append(SPECIAL_LABELS[lower])
        elif part.isupper():
            pretty.append(part)
        else:
            pretty.append(part.capitalize())
    return " ".join(pretty)


def _lookup_value(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _resolve_schema(schema: Dict[str, Any], root_schema: Dict[str, Any]) -> Dict[str, Any]:
    if "$ref" not in schema:
        return schema

    ref = schema["$ref"]
    if ref.startswith("#/$defs/"):
        def_name = ref.split("/")[-1]
        return root_schema.get("$defs", {}).get(def_name, schema)
    return schema


def _extract_constraints(schema: Dict[str, Any]) -> Dict[str, Any]:
    constraints: Dict[str, Any] = {}
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems", "pattern"):
        if key in schema:
            constraints[key] = schema[key]
    if "enum" in schema:
        constraints["enum"] = schema["enum"]
    if "examples" in schema:
        constraints["examples"] = schema["examples"]
    return constraints


def _control_kind(schema: Dict[str, Any], current_value: Any) -> ControlKind:
    if schema.get("enum"):
        return "enum"
    schema_type = schema.get("type")
    if schema_type == "boolean":
        return "toggle"
    if schema_type == "array":
        return "collection"
    if schema_type == "object":
        if schema.get("additionalProperties") or current_value is None or isinstance(current_value, dict):
            return "mapping"
        return "readonly"
    return "scalar"


def _value_type(schema: Dict[str, Any], current_value: Any) -> str:
    if isinstance(current_value, bool):
        return "boolean"
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return "integer"
    if isinstance(current_value, float):
        return "float"
    if isinstance(current_value, list):
        return "array"
    if isinstance(current_value, dict):
        return "object"
    schema_type = schema.get("type")
    if schema_type == "number":
        return "float"
    if schema_type:
        return str(schema_type)
    return "string"


def _ui_hint(path: str, schema: Dict[str, Any], current_value: Any) -> str:
    lower_path = path.lower()
    if schema.get("enum"):
        return "segmented-select" if len(schema["enum"]) <= 4 else "select"
    if schema.get("type") == "boolean":
        return "switch"
    if schema.get("type") in {"integer", "number"} and ("minimum" in schema or "maximum" in schema):
        return "slider"
    if isinstance(current_value, dict):
        return "key-value-editor"
    if isinstance(current_value, list):
        return "collection-editor"
    if any(token in lower_path for token in ("note", "pattern", "profile", "mapping")):
        return "text"
    return "input"


def _build_controls_for_schema(
    schema: Dict[str, Any],
    root_schema: Dict[str, Any],
    current_values: Dict[str, Any],
    default_values: Dict[str, Any],
    revision: str,
    persistence_manager: Any,
    prefix: str = "",
) -> List[ControlDefinition]:
    resolved = _resolve_schema(schema, root_schema)
    controls: List[ControlDefinition] = []
    properties = resolved.get("properties", {})

    if resolved.get("type") == "object" and properties:
        for prop_name, prop_schema in properties.items():
            path = f"{prefix}.{prop_name}" if prefix else prop_name
            controls.extend(
                _build_controls_for_schema(
                    prop_schema,
                    root_schema,
                    current_values,
                    default_values,
                    revision,
                    persistence_manager,
                    path,
                )
            )
        return controls

    current_value = _lookup_value(current_values, prefix) if prefix else current_values
    default_value = _lookup_value(default_values, prefix) if prefix else default_values
    kind = _control_kind(resolved, current_value)
    persist_dirty = bool(persistence_manager and persistence_manager.differs_from_persisted(prefix))

    controls.append(
        ControlDefinition(
            id=prefix.replace(".", "__"),
            path=prefix,
            control_kind=kind,
            label=_titleize(prefix.split(".")[-1]),
            description=resolved.get("description", "") or resolved.get("title", ""),
            value_type=_value_type(resolved, current_value),
            current_value=current_value,
            default_value=default_value,
            constraints=_extract_constraints(resolved),
            ui_hint=_ui_hint(prefix, resolved, current_value),
            availability="available",
            persist_behavior="persistable",
            revision=revision,
            dirty_state="dirty" if persist_dirty else "clean",
        )
    )
    return controls


def build_control_domains(
    config: RootConfig,
    revision: str,
    persistence_manager: Any = None,
) -> List[ControlDomain]:
    root_schema = RootConfig.model_json_schema()
    current_values = config.model_dump()
    default_values = RootConfig().model_dump()
    domains: List[ControlDomain] = []

    for domain_id, domain_schema in root_schema.get("properties", {}).items():
        metadata = DOMAIN_METADATA.get(
            domain_id,
            {
                "title": _titleize(domain_id),
                "description": "",
                "sort_order": 999,
            },
        )
        controls = _build_controls_for_schema(
            domain_schema,
            root_schema,
            current_values,
            default_values,
            revision,
            persistence_manager,
            domain_id,
        )
        domains.append(
            ControlDomain(
                id=domain_id,
                title=metadata["title"],
                description=metadata["description"],
                sort_order=metadata["sort_order"],
                controls=controls,
            )
        )

    return sorted(domains, key=lambda domain: domain.sort_order)


def build_action_catalog() -> List[ActionDefinition]:
    return [
        ActionDefinition(
            id=action.action_id,
            label=action.label,
            description=action.description,
            confirmation_required=action.confirmation_required,
            availability=action.availability,
            parameter_schema=action.parameter_schema or {},
            result_message_template=action.result_message_template,
        )
        for action in ACTION_CATALOG
    ]


def live_control_paths() -> List[str]:
    return [
        "sequencer.bpm",
        "sequencer.swing",
        "sequencer.density",
        "sequencer.direction_pattern",
        "sequencer.root_note",
        "sequencer.gate_length",
    ]


def iter_control_paths(domains: Iterable[ControlDomain]) -> Iterable[str]:
    for domain in domains:
        for control in domain.controls:
            yield control.path
