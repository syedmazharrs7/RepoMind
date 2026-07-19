# Module 2 – Repository Scanner

## Goal

Recursively scan a cloned repository and identify all supported source files for further processing.

---

## Problems & Decisions

### Problem 1: How should directories be traversed?

#### Options Considered

- os.walk()
- pathlib.Path recursion

#### Final Decision

Recursive traversal using `pathlib`.

#### Why?

- Cleaner API
- More Pythonic
- Better readability

---

### Problem 2: How should programming languages be detected?

#### Options Considered

- Content-based detection
- File extension mapping

#### Final Decision

Extension mapping.

#### Why?

- Fast
- Deterministic
- Easy to extend

---

### Problem 3: Should every folder be scanned?

#### Problem

Folders like `.git`, `venv`, `node_modules`, and `__pycache__` contain thousands of unnecessary files.

#### Final Decision

Maintain a configurable ignored-directory list.

#### Why?

Improves performance and avoids irrelevant files.

---

### Problem 4: How should discovered files be represented?

#### Final Decision

Use an immutable `SourceFile` dataclass.

#### Why?

- Structured metadata
- Easier testing
- Type safety

---

### Problem 5: Should scan order depend on the operating system?

#### Final Decision

Sort discovered files before returning.

#### Why?

Deterministic output improves testing and reproducibility.

---

## Lessons Learned

- Deterministic output makes testing significantly easier.
- Filtering unnecessary directories greatly improves scan performance.
- Using dataclasses makes future modules cleaner because metadata is already structured.
- Good scanners should only discover files, not analyze them.
