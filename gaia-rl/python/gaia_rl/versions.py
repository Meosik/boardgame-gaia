"""Keep compiled rules, editable sources and saved runs from silently diverging."""
from hashlib import sha256
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

from ._native import ENGINE_BUILD_ID, ENV_SCHEMA_VERSION, SOURCE_MANIFEST


class VersionMismatchError(RuntimeError):
    """A run requires an explicit rebuild or a compatible checkpoint."""


def source_differences(root: Path) -> list[str]:
    """Compare build inputs, including added files, without changing the checkout."""
    expected = {}
    for line in SOURCE_MANIFEST.splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    actual = set(expected)
    for directory in ("gaia-engine/src", "gaia-engine/data", "gaia-rl/src"):
        actual.update(
            path.relative_to(root).as_posix()
            for path in (root / directory).rglob("*") if path.is_file()
        )
    differences = []
    for name in sorted(actual):
        path = root / name
        if not path.is_file() or name not in expected:
            differences.append(name)
        elif sha256(path.read_bytes()).hexdigest() != expected[name]:
            differences.append(name)
    return differences


def require_current_sources(root: Path) -> None:
    """Call at run startup, not during an already version-pinned simulation."""
    differences = source_differences(root)
    if differences:
        raise VersionMismatchError(
            "Compiled simulator differs from source; rebuild before starting a new run: "
            + ", ".join(differences)
        )


def runtime_versions() -> dict[str, str | int]:
    """Python implementation is versioned independently of the native engine."""
    digest = sha256()
    package = Path(__file__).parent
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    dependencies = []
    for name in ('numpy','gymnasium','pettingzoo','ray','torch'):
        try:
            dependencies.append(f'{name}={version(name)}')
        except PackageNotFoundError:
            dependencies.append(f'{name}=absent')
    return {
        "dependencies": ";".join(dependencies),
        "engine_build_id": ENGINE_BUILD_ID,
        "environment_schema": ENV_SCHEMA_VERSION,
        "python_build_id": digest.hexdigest(),
    }


def require_compatible_versions(saved: dict[str, str | int]) -> None:
    current = runtime_versions()
    mismatches = [key for key, value in current.items() if saved.get(key) != value]
    if mismatches:
        raise VersionMismatchError("Incompatible checkpoint: " + ", ".join(mismatches))
