DESCRIPTION: This skill helps you to read a large codebase efficiently. It gives you techniques to analyse a code base efficiently.

---
name: code-reading
description: "Use this skill whenever an agent needs to read, navigate, or understand a code repository and match the user's prompt/task context with the relevant parts of that codebase. Triggers: any mention of a repo, codebase, source directory, or project folder; tasks like 'understand this code', 'find where X is implemented', 'explain this project', 'make a change to the codebase', 'debug this repo', or 'add a feature'. Also use when asked to trace a data flow, find a function definition, understand an architecture, or locate the right file to edit."
---

# Reading a Code Repository

## Why this skill exists

Code repositories are large, hierarchical, and heterogeneous. Blindly reading every file
is slow, wasteful, and burns context. This skill gives you a repeatable, efficient protocol
for orienting yourself in any codebase and matching the user's task to the right files —
without reading what you don't need.

---

## Phase 1 — Orient (always do this first)

Before reading a single source file, run these commands to form a mental model of the repo.

### 1a. Get the top-level layout

```bash
find . -maxdepth 2 -not -path '*/\.*' -not -path '*/node_modules/*' \
       -not -path '*/__pycache__/*' -not -path '*/dist/*' \
       -not -path '*/build/*' | sort
```

Or if the `tree` command is available:

```bash
tree -L 2 -I 'node_modules|.git|dist|build|__pycache__|*.egg-info'
```

**What to look for:**
- Entry points (`main.py`, `index.ts`, `app.js`, `cmd/`, `src/main.*`)
- Config files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`)
- Test directories (`tests/`, `spec/`, `__tests__/`)
- Documentation (`README.md`, `docs/`, `ARCHITECTURE.md`)
- Infrastructure / deployment (`Dockerfile`, `docker-compose.yml`, `.github/`, `k8s/`)

### 1b. Read the README

```bash
cat README.md 2>/dev/null || cat readme.md 2>/dev/null || echo "No README found"
```

A good README gives you: purpose, architecture overview, setup instructions, and key
concepts. Read it fully — it saves more time than it costs.

### 1c. Read the manifest / config file

This reveals dependencies, scripts, and the project structure the author intended.

| Stack       | File to read                      | Key fields                                       |
|-------------|-----------------------------------|--------------------------------------------------|
| Node / JS   | `package.json`                    | `scripts`, `dependencies`, `main`, `exports`     |
| Python      | `pyproject.toml` / `setup.py`     | `[tool.poetry]`, `install_requires`, `entry_points` |
| Rust        | `Cargo.toml`                      | `[dependencies]`, `[[bin]]`, `[lib]`             |
| Go          | `go.mod`                          | `module`, `require`                              |
| Java/Kotlin | `pom.xml` / `build.gradle`        | `<dependencies>`, `plugins`                      |
| Ruby        | `Gemfile`                         | gem names and versions                           |

```bash
cat package.json 2>/dev/null | head -60
# or
cat pyproject.toml 2>/dev/null
```

### 1d. Identify the language(s)

```bash
# Count files by extension
find . -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' \
  -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
```

---

## Phase 2 — Match the Prompt Context

Once you have a mental model, map the user's task to specific locations in the repo.
Do not read full files yet — locate first.

### 2a. Keyword / symbol search

```bash
# Find where a function, class, or variable is defined
grep -rn "def process_order\|class OrderService\|function processOrder" \
     --include="*.py" --include="*.ts" --include="*.js" .

# Case-insensitive search
grep -rni "authentication" --include="*.py" . | grep -v "test_\|_test"

# Ripgrep (faster, if available)
rg "handlePayment" --type ts -n
```

**Match the prompt to grep terms:**

| Prompt says…                   | Grep for…                                 |
|--------------------------------|-------------------------------------------|
| "user login / auth"            | `login`, `authenticate`, `jwt`, `session` |
| "database / DB queries"        | `query`, `execute`, `cursor`, `orm`, `sql` |
| "API endpoint / route"         | `@app.route`, `router.get`, `app.use`, `@GET` |
| "configuration / settings"     | `config`, `settings`, `env`, `dotenv`     |
| "error handling"               | `try`, `except`, `catch`, `raise`, `throw` |
| "background job / task queue"  | `celery`, `worker`, `queue`, `job`, `cron` |
| "file upload / storage"        | `upload`, `s3`, `blob`, `multipart`       |

### 2b. Find entry points and call chains

```bash
# Find the main entry point
grep -rn "if __name__\|app.listen\|func main\|void main" --include="*.py" \
     --include="*.go" --include="*.java" --include="*.ts" . | head -10

# Trace what a route/function calls
grep -n "def handle_checkout" src/orders/views.py
# Then read just that function
sed -n '45,80p' src/orders/views.py
```

### 2c. Understand the module / package structure

```bash
# Python: find all modules and their __init__ exports
find . -name "__init__.py" | head -20
grep -rn "^from \|^import " src/ --include="*.py" | \
  grep -v "test" | sed 's/:.*from / -> /' | sort -u | head -40

# Node: find all index files (package entry points)
find . -name "index.ts" -o -name "index.js" | grep -v node_modules | head -20
```

---

## Phase 3 — Read Strategically

Now read files, but only as much as you need.

### 3a. Size before you read

```bash
wc -l src/orders/service.py
# < 200 lines → read fully
# 200–500 lines → read with context (grep + surrounding lines)
# > 500 lines → read by section (head, grep -A/-B, sed ranges)
```

### 3b. Read a whole small file

```bash
cat src/auth/utils.py          # Python
cat src/components/Button.tsx  # TypeScript/React
```

### 3c. Read a section of a large file

```bash
# Show lines 100–150
sed -n '100,150p' src/orders/service.py

# Show a function and 5 lines of context
grep -n "def calculate_total" src/orders/service.py
# → found at line 212
sed -n '210,260p' src/orders/service.py

# Show surrounding lines for a match
grep -n -A 20 -B 5 "def calculate_total" src/orders/service.py
```

### 3d. Read tests to understand expected behavior

Tests are often the clearest documentation of what a function is supposed to do.

```bash
find . -path "*/test*" -name "*.py" | head -10
grep -rn "def test_checkout\|it('checkout" tests/ --include="*.py" --include="*.ts"
cat tests/test_orders.py
```

---

## Phase 4 — Understand the Architecture

For tasks that require cross-cutting changes or deep understanding, build a map.

### 4a. Find all classes and functions (Python)

```bash
grep -rn "^class \|^def \|    def " src/ --include="*.py" | \
  grep -v "__pycache__" | head -60
```

### 4b. Find all exported symbols (TypeScript / JavaScript)

```bash
grep -rn "^export " src/ --include="*.ts" --include="*.tsx" | head -40
```

### 4c. Map inter-module dependencies

```bash
# Python imports across the project
grep -rn "^from \." src/ --include="*.py" | \
  awk -F: '{print $1, $3}' | sort -u | head -30

# Node imports
grep -rn "require\('\.\|from '\." src/ --include="*.ts" | \
  sed "s/.*from '//;s/'.*//" | sort -u | head -30
```

### 4d. Find config / environment variables in use

```bash
grep -rn "os.environ\|process.env\|getenv\|config\." src/ \
     --include="*.py" --include="*.ts" | grep -v "test" | sort -u | head -30
```

---

## Phase 5 — Git History (when available)

The git log reveals intent and change patterns — invaluable for "why is this here?"

```bash
# Recent changes
git log --oneline -20

# Who changed a specific file and when
git log --oneline --follow src/orders/service.py

# What changed in a specific commit
git show abc1234 --stat

# Find when a line or function was introduced
git log -S "def calculate_total" --oneline

# See the diff of recent changes to a file
git diff HEAD~3 src/orders/service.py
```

---

## Decision Table — What to Read and When

| User task                              | What to read                                                   |
|----------------------------------------|----------------------------------------------------------------|
| "Explain this project"                 | README → manifest → top-level layout → entry point            |
| "Find where X is implemented"          | `grep -rn "X"` → read matched file section                    |
| "Fix a bug in feature Y"               | grep for Y → read the function → read its tests               |
| "Add a new feature"                    | Find similar existing feature → read its module + tests        |
| "Understand data flow for Z"           | Entry point → grep for Z → trace calls → read each hop        |
| "What does this file do?"              | `wc -l` → if small cat it; if large grep for class/def names  |
| "Are there any security issues?"       | grep for env vars, auth, SQL queries, file I/O                 |
| "Write tests for module M"             | Read M fully → read existing tests for patterns                |
| "Refactor / rename X"                  | `grep -rn "X"` to find all usages before touching anything    |

---

## Anti-Patterns — What NOT to Do

| Anti-pattern                                 | Why it's wrong                                              |
|----------------------------------------------|-------------------------------------------------------------|
| `cat` a file > 500 lines immediately         | Floods context; use sections instead                        |
| Reading `node_modules/` or `dist/`           | Third-party or compiled code; never what you need           |
| Grepping without `--include` filter          | Matches binary files, lock files, fixtures — too much noise |
| Reading every file before forming a hypothesis | Orient first, read second                                 |
| Ignoring test files                          | Tests reveal contracts, edge cases, and expected behavior   |
| Skipping the README                          | Often contains critical architectural decisions             |
| Assuming file names match function names     | Always verify with grep before assuming                     |

---

## Quick-Reference Commands

```bash
# Orient
tree -L 2 -I 'node_modules|.git|dist|build|__pycache__'
cat README.md
cat package.json | head -40

# Locate
grep -rn "TERM" --include="*.py" .
rg "TERM" --type ts -n
find . -name "*.py" | xargs grep -l "TERM"

# Read by section
sed -n 'START,ENDp' FILE
grep -n -A 20 -B 3 "PATTERN" FILE

# Size check
wc -l FILE
wc -c FILE

# Git context
git log --oneline -10
git log --oneline --follow FILE
git diff HEAD~1 FILE
```

---

## Notes

- Always start with Phase 1 (Orient) even if you think you know the structure.
- Prefer `rg` (ripgrep) over `grep` when available — it's faster and respects `.gitignore` automatically.
- When in doubt about where something lives, search before reading — one grep can save reading five files.
- If the repo has a `ARCHITECTURE.md`, `CONTRIBUTING.md`, or `docs/` folder, read those before diving into source files.
- Lock files (`package-lock.json`, `poetry.lock`, `Cargo.lock`) are rarely useful to read; they are machine-generated. Skip unless debugging a dependency conflict.