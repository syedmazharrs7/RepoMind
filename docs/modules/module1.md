# Module 1 – Repository Downloader

## Goal

Build a reliable repository downloading system that can clone public Git repositories and prepare them for further analysis.

---

## Problems & Decisions

### Problem 1: How should repositories be cloned?

#### Options Considered

- Using the `git clone` command through `subprocess`
- Using the GitPython library

#### Final Decision

Use **GitPython**.

#### Why?

- Cleaner Python API
- Better exception handling
- Easier to test
- No manual shell command management

---

### Problem 2: What if cloning fails halfway?

#### Problem

A failed clone can leave a partially downloaded repository.

#### Final Decision

Automatically remove corrupted repositories.

#### Why?

Keeps the workspace clean and prevents later modules from scanning incomplete repositories.

---

### Problem 3: Should invalid URLs be accepted?

#### Final Decision

Validate repository URLs before cloning.

#### Why?

Fail early with meaningful errors instead of allowing unexpected failures later.

---

### Problem 4: How should clone information be stored?

#### Final Decision

Use an immutable `RepositoryInfo` dataclass.

#### Why?

- Better readability
- Type safety
- Predictable behavior

---

## Lessons Learned

- GitPython is safer and easier than calling Git through subprocess.
- Always clean up failed operations.
- Validate inputs before performing expensive work.
- Small utility modules become much easier to maintain when they return structured data instead of dictionaries.
