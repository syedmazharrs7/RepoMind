# Architectural Decisions

## ADR-001

Use GitPython instead of subprocess.

Reason:

Better API and error handling.

---

## ADR-002

Separate scanning from parsing.

Reason:

Single Responsibility Principle.

---

## ADR-003

Registry-based ParserFactory.

Reason:

Supports unlimited languages without changing factory logic.

---

## ADR-004

Parse bytes instead of file paths.

Reason:

Future IDE integration.

---

## ADR-005

Immutable ParseResult.

Reason:

Thread safety and predictable behavior.
