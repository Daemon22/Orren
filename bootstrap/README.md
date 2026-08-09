# Orren Bootstrap Interpreter v1.0.0

The seed that makes all 133+ .orn files executable.
This is the ONLY non-.orn component in the Orren ecosystem.
Once the Orren self-hosted compiler becomes operational through
this bootstrap, this file can be retired.

## First Law

> Meaning shall never be lost because of language.

## Architecture

```
orren_bootstrap.py
  |-- Tokenizer (Section 1)   - Lexes Orren source into token stream
  |-- Parser (Section 2)      - Recursive-descent parser producing AST
  |-- Runtime (Section 3)     - OrrenEntity, OrrenEnum, Environment types
  |-- Evaluator (Section 4)   - Tree-walking interpreter
  |-- Builtins (Section 5)    - 60+ built-in functions
  `-- CLI (Section 6)         - run, repl, check, ast, test, version
```

## Supported Syntax

| Construct | Syntax | Status |
|-----------|--------|--------|
| Module declaration | `module name.path` | Full |
| Imports | `import a.b.c::{X, Y}`, `import a.b.c` | Full |
| Intents | `intent "description"` | Full |
| Constants | `const NAME = value` | Full |
| Entities | `entity Name ... end` | Full |
| Properties | `property name: Type = default` | Full |
| Functions | `fn name(params) -> Type ... end` | Full |
| Static methods | `EntityName.method(args)` | Full |
| Instance methods | `instance.method(args)` | Full |
| Enums | `enum Name VARIANT_A VARIANT_B end` | Full |
| Let bindings | `let x = expr`, `let x be expr` | Full |
| If/else | `if cond [then] ... [else] ... end` | Full |
| For-in | `for x in list [do] ... end` | Full |
| For-C | `for i < n [do] ... end` | Full |
| While | `while cond [do] ... end` | Full |
| Match | `match expr with ... end` | Full |
| Return | `return expr` | Full |
| Exports | `export {A, B}`, `export Name` | Full |
| Comments | `-- line`, `/// doc` | Full |
| List literals | `[1, 2, 3]` | Full |
| Map literals | `{key: val}`, `{}` | Full |
| String ops | `+`, `str_*()` | Full |
| Namespace access | `Optional::some(x)` | Full |
| Entity construct | `Name{field: val}` | Full |

## Built-in Functions (60+)

- **I/O**: print, println, read_line, read_file, write_file, join_lines
- **Type conversion**: str, int, float, int_to_string, string_to_int, string_to_float, float_to_string
- **List operations**: list_append, list_length, list_contains, list_reverse, list_sort, list_unique, list_take, list_drop, list_head, list_tail, list_concat, list_flatten, list_join, list_find, list_empty, list_clear
- **String operations**: str_length, str_contains, str_split, str_trim, str_upper, str_lower, str_starts_with, str_ends_with, str_replace, str_substring, str_join
- **Math**: int_abs, int_max, int_min, float_abs, float_ceil, float_floor, float_round
- **Map operations**: map_new, map_get, map_put, map_has, map_keys, map_values, map_size
- **JSON**: json_parse, json_encode
- **System**: system_args, system_env, exit, panic
- **Debug**: debug_print, error_print, type_of, to_string, len, range
- **Semantic bridge**: attributes_of, with_confidence, propagate

## Usage

```bash
# Run an Orren file
python orren_bootstrap.py run file.orn

# Interactive REPL
python orren_bootstrap.py repl

# Parse check
python orren_bootstrap.py check file.orn

# Print AST
python orren_bootstrap.py ast file.orn

# Run test suite (56 tests)
python orren_bootstrap.py test

# Show version
python orren_bootstrap.py version
```

## Module Resolution

When running a file, the interpreter searches for imported modules:
1. In the same directory as the loaded file
2. In the current working directory

Module paths map to file paths:
- `orren.prelude` -> `orren/prelude/prelude.orn` or `orren/prelude.orn`
- `sire.domain.types` -> `sire/domain/types.orn`

## Parse Coverage

45 of 227 .orn files parse successfully, including:
- All core library files (prelude, foundation)
- Standard library files
- Runtime prelude

The remaining files use extended syntax patterns (doc comment formatting,
complex match expressions, etc.) that can be added incrementally as needed.
