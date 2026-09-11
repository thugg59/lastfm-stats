from pathlib import Path

PROJECT_DIR = Path(".")
OUTPUT_FILE = Path("all_code.txt")

INCLUDED_DIRS = {
    "src",
    "tests",
    "sql",
    "scripts",
}

INCLUDED_ROOT_FILES = {
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    ".dockerignore",
    "Dockerfile",
    "docker-compose.yml",
}


def should_include(file: Path, relative: Path) -> bool:
    # Root-level files
    if len(relative.parts) == 1:
        if relative.name in INCLUDED_ROOT_FILES:
            return True

        # Include every Python file in the root
        return file.suffix == ".py"

    # Files inside included directories
    if relative.parts[0] not in INCLUDED_DIRS:
        return False

    # Ignore Python cache directories
    if "__pycache__" in relative.parts:
        return False

    # Include EVERYTHING inside sql/ and scripts/
    if relative.parts[0] in {"sql", "scripts"}:
        return True

    # src/ and tests/ only include Python files
    return file.suffix == ".py"


with OUTPUT_FILE.open("w", encoding="utf-8") as output:
    for file in sorted(PROJECT_DIR.rglob("*")):
        if not file.is_file():
            continue

        relative_path = file.relative_to(PROJECT_DIR)

        if not should_include(file, relative_path):
            continue

        output.write(f"\n{'=' * 60}\n")
        output.write(f"# {relative_path}\n")
        output.write(f"{'=' * 60}\n\n")

        output.write(file.read_text(encoding="utf-8"))
        output.write("\n\n")