# Project Context Collator

A small Python utility that walks a project directory and collates all relevant text/code files into a single Markdown document.

The output is ideal for sharing project context (e.g. with code reviewers or AI tools), producing a file like:

```text
===== FILE: src/main.rs =====
````rust
// file contents…
````
```

## Features

- Recursively scans a project directory and gathers text/code files.
- Emits a single Markdown file (default: `project_context.md`).
- Adds clear per-file headers.
- Skips common build/cache directories.
- Skips large or binary files.
- Determines code-fence language tags automatically.

## Installation

Copy the script anywhere and run with Python 3.10+.

## Usage

```bash
python3 collate_project_context.py
```

Additional options:

```
--root /path/to/project
--output my_output.md
--max-kb 2048
--include-hidden
--extra-dirs .venv build_cache
--only-exts .gd .rs .toml
```

## License

MIT (replace with your preferred license).
