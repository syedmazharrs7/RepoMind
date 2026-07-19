# Module 3 – Tree-sitter Parsing

## Goal

Convert every SourceFile into a Tree-sitter Abstract Syntax Tree (AST).

This is the foundation for symbol extraction, dependency analysis, semantic search, and repository intelligence.

---

## Problems & Decisions

### Problem 1: Should parsing and file reading happen in the same class?

#### Options Considered

- Parser reads files directly
- RepositoryParser handles file I/O

#### Final Decision

RepositoryParser performs file reading.

BaseParser only parses bytes.

#### Why?

Keeps parsing independent of storage.

Allows future support for:

- Git blobs
- IDE integrations
- In-memory editing
- Language servers

---

### Problem 2: How should parsers be selected?

#### Options Considered

- Large if/elif chain
- Registry-based factory

#### Final Decision

Registry-based ParserFactory.

#### Why?

- Open/Closed Principle
- Easy language expansion
- Cleaner architecture

---

### Problem 3: Should BaseParser know about programming languages?

#### Final Decision

No.

Concrete language parsers load their own grammars.

#### Why?

Keeps BaseParser completely language-agnostic.

---

### Problem 4: Should a parser be created for every file?

#### Final Decision

Reuse parser instances.

#### Why?

- Lower memory usage
- Better performance
- Scales to large repositories

---

### Problem 5: How should syntax errors be handled?

#### Options Considered

- Throw exceptions
- Let Tree-sitter recover

#### Final Decision

Use `tree.root_node.has_error`.

#### Why?

Tree-sitter is designed for error recovery and still produces useful ASTs.

---

### Problem 6: How should parse results be represented?

#### Final Decision

Create an immutable `ParseResult` dataclass.

Include parsing time.

#### Why?

Supports future:

- Performance metrics
- Health analysis
- Benchmarking

---

## Lessons Learned

- Tree-sitter is fault tolerant rather than compiler-like.
- Separating parsing from file I/O makes the parser reusable.
- Registry patterns scale much better than conditional logic.
- Immutable models simplify reasoning and reduce bugs.
- Building a strong parsing layer now prevents architectural changes in future modules.
