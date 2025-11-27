#!/usr/bin/env python3
"""
Collate a project’s text source files into a single Markdown document.

- Creates headings like:
  ===== FILE: path/to/file.rs =====
  ```rust
  ...contents...
  ```

- Skips common build/cache folders (e.g., .git, .godot/, .import/, target/, node_modules/).
- Skips large files by default (> 512 KB) to avoid accidental binary dumps.
- Detects probable binary files and ignores them safely.
- Orders files alphabetically for consistent output.
"""

import argparse
import os
import sys
from pathlib import Path

# ---- Configuration: default directory excludes typical for Godot + Rust ----
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vs",
    ".vscode",
    ".godot",
    ".import",
    ".cache",
    "target",
    "node_modules",
    "dist",
    "build",
    "out",
    "__pycache__",
}

# ---- Reasonable default file extensions considered "text/code" ----
DEFAULT_ALLOWED_EXTENSIONS = {
    # Godot
    ".gd", ".tres", ".cfg", ".ini", ".shader", ".gdshader",
    # Rust
    ".rs", ".toml", ".md",
    # GDExtension / C++ (in case you have any)
    ".h", ".hpp", ".c", ".cpp", ".cc", ".cxx",
    # Web / tooling
    ".json", ".yml", ".yaml", ".js", ".ts", ".html", ".css",
    # Scripts
    ".py", ".ps1", ".bat", ".sh", ".zsh",
    # Misc text
    ".txt", ".csv", ".gitattributes", ".gitignore", ".editorconfig",
}

# ---- Map extension -> Markdown code fence language tag ----
LANG_FROM_EXTENSION = {
    ".gd": "gdscript",
    ".rs": "rust",
    ".toml": "toml",
    ".lock": "",
    ".md": "md",
    ".h": "cpp",
    ".hpp": "cpp",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".js": "javascript",
    ".ts": "typescript",
    ".html": "html",
    ".css": "css",
    ".py": "python",
    ".ps1": "powershell",
    ".bat": "bat",
    ".sh": "bash",
    ".zsh": "bash",
    ".tscn": "",
    ".tres": "",
    ".cfg": "",
    ".ini": "",
    ".shader": "glsl",
    ".gdshader": "glsl",
    ".import": "",
    ".txt": "",
    ".csv": "",
    ".gitattributes": "",
    ".gitignore": "",
    ".editorconfig": "",
}

def is_probably_binary(file_path: Path, sample_bytes: int = 8192) -> bool:
    """Heuristic: read some bytes and look for NULs or high binary density."""
    try:
        with open(file_path, "rb") as file_handle:
            chunk = file_handle.read(sample_bytes)
        if b"\x00" in chunk:
            return True
        if not chunk:
            return False
        control_bytes = sum(b < 9 or (13 < b < 32) for b in chunk)
        return (control_bytes / len(chunk)) > 0.30
    except Exception:
        return True

def infer_lang_from_extension(file_path: Path) -> str:
    return LANG_FROM_EXTENSION.get(file_path.suffix.lower(), "")

def should_include_file(file_path: Path, allowed_extensions: set[str]) -> bool:
    if file_path.suffix.lower() in allowed_extensions:
        return True
    return False

def walk_project(
    root_dir: Path,
    excluded_directories: set[str],
    allowed_extensions: set[str],
    include_hidden: bool,
) -> list[Path]:
    collected_paths: list[Path] = []
    for current_dir, dirnames, filenames in os.walk(root_dir):
        current_path = Path(current_dir)

        pruned_dirnames = []
        for directory_name in dirnames:
            if directory_name in excluded_directories:
                continue
            if not include_hidden and directory_name.startswith("."):
                continue
            pruned_dirnames.append(directory_name)
        dirnames[:] = pruned_dirnames

        for filename in filenames:
            file_path = current_path / filename
            if not include_hidden and filename.startswith(".") and file_path.suffix not in {".gitignore", ".gitattributes", ".editorconfig"}:
                continue
            if should_include_file(file_path, allowed_extensions):
                collected_paths.append(file_path)

    collected_paths.sort(key=lambda p: str(p).lower())
    return collected_paths

def read_text_safely(file_path: Path, max_bytes: int) -> str | None:
    """Return file content as text (UTF-8 with replacement) if under size and not binary."""
    try:
        if file_path.stat().st_size > max_bytes:
            return None
        if is_probably_binary(file_path):
            return None
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def human_kilobytes(num_bytes: int) -> str:
    return f"{num_bytes/1024:.1f} KB"

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collate a project into a single Markdown file with per-file sections."
    )
    parser.add_argument(
        "-r", "--root",
        type=str,
        default=".",
        help="Root directory of the project (default: current directory).",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="project_context.md",
        help="Output Markdown filename (default: project_context.md).",
    )
    parser.add_argument(
        "--max-kb",
        type=int,
        default=512,
        help="Skip files larger than this size in KB (default: 512).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories (default: off).",
    )
    parser.add_argument(
        "--extra-dirs",
        nargs="*",
        default=[],
        help="Additional directory names to exclude (space separated).",
    )
    parser.add_argument(
        "--only-exts",
        nargs="*",
        default=[],
        help="If supplied, only include these extensions (e.g. --only-exts .gd .rs .toml).",
    )
    args = parser.parse_args()

    project_root = Path(args.root).resolve()
    output_file = Path(args.output).resolve()
    maximum_bytes = args.max_kb * 1024

    excluded_directories = set(DEFAULT_EXCLUDED_DIRS)
    excluded_directories.update(args.extra_dirs)

    allowed_extensions = set(DEFAULT_ALLOWED_EXTENSIONS)
    if args.only_exts:
        allowed_extensions = {ext.lower() for ext in args.only_exts}

    if not project_root.exists():
        print(f"Error: root directory not found: {project_root}", file=sys.stderr)
        return 1

    collected_paths = walk_project(
        root_dir=project_root,
        excluded_directories=excluded_directories,
        allowed_extensions=allowed_extensions,
        include_hidden=args.include_hidden,
    )

    lines: list[str] = []
    lines.append("# Project Context Collation\n")
    lines.append(f"- Root: `{project_root}`")
    lines.append(f"- File count scanned (pre-size/binary filter): {len(collected_paths)}")
    lines.append(f"- Max file size included: {args.max_kb} KB")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")

    for path in collected_paths:
        try:
            file_size = path.stat().st_size
            rel = path.relative_to(project_root)
            lines.append(f"- `{rel}` ({human_kilobytes(file_size)})")
        except Exception:
            continue
    lines.append("\n---\n")

    included_count = 0
    skipped_for_size = 0
    skipped_as_binary = 0

    for file_path in collected_paths:
        relative_path = file_path.relative_to(project_root)
        content = read_text_safely(file_path, max_bytes=maximum_bytes)
        if content is None:
            try:
                if file_path.stat().st_size > maximum_bytes:
                    skipped_for_size += 1
                else:
                    skipped_as_binary += 1
            except Exception:
                skipped_as_binary += 1
            continue

        included_count += 1
        language_tag = infer_lang_from_extension(file_path)

        lines.append(f"===== FILE: {relative_path} =====\n")
        if language_tag:
            lines.append(f"```{language_tag}")
        else:
            lines.append("```")
        lines.append(content.rstrip("\n"))
        lines.append("```\n")

    lines.append("\n---")
    lines.append(f"Included files: {included_count}")
    lines.append(f"Skipped (too large): {skipped_for_size}")
    lines.append(f"Skipped (binary/non-text): {skipped_as_binary}")
    lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created: {output_file}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
