# Module 4 — Symbol Extraction

## Problem

How can syntax trees be transformed into semantic entities that represent repository structure?

## Options Considered

- Work directly with AST nodes
- Build a dedicated Symbol model

## Decision

Introduce immutable Symbol objects extracted from Tree-sitter ASTs.

## Why

Semantic symbols provide a stable abstraction independent of Tree-sitter internals and become the foundation for graph construction, embeddings, and repository-aware AI.

## Lessons Learned

- Syntax and semantics are different layers.
- Stable IDs simplify future graph construction.
- Single-pass traversal improves scalability.
- Registry-based extractors make adding languages straightforward.