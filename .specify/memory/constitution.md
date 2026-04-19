<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles:
  - Template Principle 1 -> I. Code Quality Is a Feature
  - Template Principle 2 -> II. Tests Define Done
  - Template Principle 3 -> III. Consistent User Experience
  - Template Principle 4 -> IV. Performance Budgets Are Requirements
  - Template Principle 5 -> V. Observable, Maintainable Delivery
- Added sections:
  - Engineering Standards
  - Delivery Workflow
- Removed sections:
  - None
- Templates requiring updates:
  - ✅ updated /Users/oberon/Projects/coding/python/SoundForgeEngine/.specify/templates/plan-template.md
  - ✅ updated /Users/oberon/Projects/coding/python/SoundForgeEngine/.specify/templates/spec-template.md
  - ✅ updated /Users/oberon/Projects/coding/python/SoundForgeEngine/.specify/templates/tasks-template.md
- Follow-up TODOs:
  - None
-->
# SoundForgeEngine Constitution

## Core Principles

### I. Code Quality Is a Feature
All production code MUST be readable, modular, and intentionally scoped. Changes
MUST favor clear interfaces, explicit naming, type hints where supported by the
codebase, and small units that can be tested independently. Duplication MUST be
reduced when it obscures behavior or increases defect risk, and temporary
workarounds MUST be documented with an owner and removal condition. Every change
MUST leave the touched area at least as understandable as before.

### II. Tests Define Done
Automated tests are mandatory for behavior changes, bug fixes, and new features.
At minimum, changes MUST add or update the narrowest useful test coverage at the
unit, integration, or contract level. A task is not complete until the relevant
tests fail before the fix when practical, pass after the fix, and no existing
test coverage is regressed. Untested changes require explicit written
justification in the plan or review record.

### III. Consistent User Experience
Every user-facing surface, including hardware controls, CLI flows, API behavior,
docs, and any future visual UI, MUST feel coherent with the rest of the product.
Names, defaults, error messages, response shapes, and interaction patterns MUST
be consistent across entry points. New features MUST describe the primary user
journey, expected feedback, failure handling, and any changes to discoverability
or operator workflow before implementation begins.

### IV. Performance Budgets Are Requirements
SoundForgeEngine is a real-time music system, so latency and timing stability are
product requirements, not optional polish. Changes affecting input handling,
sequencing, MIDI routing, or runtime control loops MUST define measurable
performance expectations and verify they remain within budget. Unless a feature
specifies stricter limits, planning MUST preserve the existing targets of
sub-10 ms perceptual button response, under 2 ms sequencer tick jitter, and
non-blocking behavior in timing-sensitive paths.

### V. Observable, Maintainable Delivery
The system MUST remain debuggable in live and long-running environments. Changes
MUST provide sufficient structured logging, configuration clarity, and failure
visibility to diagnose issues without guesswork. Hidden side effects, silent
fallbacks, and ambiguous runtime behavior are unacceptable unless explicitly
documented and justified. Documentation and operational notes MUST be updated
when behavior, configuration, or workflows change.

## Engineering Standards

All plans MUST state the relevant code quality constraints, testing approach,
user-facing impact, and performance expectations before implementation starts.
Specifications MUST include measurable success criteria, explicit edge cases, and
the user-facing consistency implications of the change.

For this repository:
- Python changes MUST run inside the project virtual environment.
- New dependencies MUST be justified against maintenance and latency cost.
- Timing-sensitive code MUST avoid blocking I/O, unbounded retries, and heavy
  work on critical execution paths.
- API and CLI changes MUST keep naming and semantics aligned unless a migration
  plan is included.

## Delivery Workflow

Work MUST pass these gates before merge:
- The change scope is small enough to review and reason about.
- Tests cover the primary behavior and the key failure path.
- User-facing behavior is documented consistently in specs, docs, or help text.
- Performance-sensitive changes include a validation method appropriate to the
  risk, such as targeted tests, benchmark notes, or measured manual checks.
- Reviewers can identify how the change preserves or improves observability.

When a principle cannot be fully met, the exception MUST be recorded in the
implementation plan under complexity or tradeoff tracking, along with the reason,
the risk, and the follow-up needed to restore compliance.

## Governance

This constitution overrides conflicting local habits or undocumented practice for
planning, implementation, and review. Every specification, plan, task list, and
code review MUST check compliance with these principles.

Amendments require:
- a documented rationale,
- updates to any affected templates or workflow guidance,
- a semantic version update for this constitution, and
- a migration note when the new rule changes how active work should be planned or
  reviewed.

Versioning policy for this document:
- MAJOR for removing or redefining a principle in a backward-incompatible way,
- MINOR for adding a principle or materially expanding governance expectations,
- PATCH for clarifications, wording improvements, or non-semantic edits.

Compliance review expectations:
- Plans MUST state how the change satisfies testing, UX consistency, and
  performance requirements.
- Tasks MUST include testing work and any documentation or observability work
  needed to satisfy the principles.
- Pull requests and reviews MUST call out any exception explicitly instead of
  silently accepting drift.

**Version**: 1.0.0 | **Ratified**: 2026-04-19 | **Last Amended**: 2026-04-19
