import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "anthropic",
    "fastapi",
    "google",
    "openai",
    "pyaudio",
    "sounddevice",
    "sqlalchemy",
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_domain_and_application_layers_do_not_import_frameworks_or_providers() -> None:
    app_root = Path(__file__).parents[1] / "app"
    source_files = [
        *sorted((app_root / "domain").glob("*.py")),
        *sorted((app_root / "application").glob("*.py")),
    ]

    violations = {
        str(path.relative_to(app_root)): sorted(imported_roots(path) & FORBIDDEN_IMPORTS)
        for path in source_files
        if imported_roots(path) & FORBIDDEN_IMPORTS
    }

    assert violations == {}

