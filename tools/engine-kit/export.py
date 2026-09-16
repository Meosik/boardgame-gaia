"""Export an allowlisted, local-only engine kit; never publish or copy Git history."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent / "templates"
FILES = (
    "rust-toolchain.toml",
    "gaia-engine/Cargo.toml",
    "gaia-rl/Cargo.toml",
    "gaia-rl/Cargo.lock",
    "gaia-rl/build.rs",
    "gaia-rl/python/gaia_rl/__init__.py",
    "gaia-rl/python/gaia_rl/aec.py",
    "gaia-rl/python/gaia_rl/encoding.py",
    "gaia-rl/python/gaia_rl/vocabulary.py",
    "gaia-rl/python/gaia_rl/versions.py",
    "gaia-rl/python/tests/test_native.py",
    "gaia-rl/python/tests/test_aec.py",
    "gaia-rl/python/tests/test_encoding.py",
    "gaia-rl/python/tests/test_versions.py",
)
TREES = {
    "gaia-engine/src": ".rs",
    "gaia-engine/data": ".toml",
    "gaia-rl/src": ".rs",
    "gaia-rl/tests": ".rs",
}
TEMPLATE_FILES = ("README.md", "examples/random_bot.py")
ASSET_PATTERNS = (
    "*/normalized/*.webp", "round_scoring_tiles/normalized/round_*.png",
    "federation_tokens/normalized/back/runtime/*.webp",
    "federation_tokens_lost_fleet/normalized/fed_*.png",
    "structures/upscaled/*.png", "structures/special/*.png", "planets/*.png",
    "icons/game-piece-icons.png", "tech_tiles/rendered/*.webp", "boards/scoring_track_extension.jpg",
)


def viewer_payload(root: Path, templates: Path) -> dict[str, bytes]:
    files = {}
    for path in sorted((root / "gaia-frontend/src").rglob("*")):
        relative = path.relative_to(root)
        if "tests" in relative.parts or any(p.startswith(".") for p in relative.parts):
            continue
        if path.is_file() and path.suffix in (".ts", ".tsx", ".css"):
            files[relative.as_posix()] = read_regular(root, relative.as_posix())
    for pattern in ASSET_PATTERNS:
        matches = sorted((root / "gaia-frontend/src/assets").glob(pattern))
        if not matches:
            raise ValueError(f"Missing viewer assets: {pattern}")
        for path in matches:
            relative = path.relative_to(root).as_posix()
            files[relative] = read_regular(root, relative)
    for name in ("package.json", "package-lock.json", "tsconfig.json", "tsconfig.node.json"):
        relative = f"gaia-frontend/{name}"
        files[relative] = read_regular(root, relative)
    files["gaia-frontend/src/data/income.json"] = read_regular(root, "gaia-frontend/src/data/income.json")
    for name in ("setup.ts", "AiReplay.test.tsx", "AiReplayLive.test.tsx", "ReplayRecords.test.ts",
                 "ReplayReadOnly.test.ts", "LiveReplay.test.ts", "fixtures/replay.json"):
        relative = f"gaia-frontend/src/tests/{name}"
        files[relative] = read_regular(root, relative)
    for name in ("live_replays.py", "replay_log.py", "replay_income.py", "test_live_replays.py"):
        relative = f"gaia-rl/tools/{name}"
        files[relative] = read_regular(root, relative)
    # Copy only the existing pure frame/validation helpers, not the publication
    # and model-evaluation entry points from their original module.
    source = read_regular(root, "gaia-rl/tools/evaluation_replays.py").decode()
    helpers = [ast.get_source_segment(source, node) for node in ast.parse(source).body
               if isinstance(node, ast.FunctionDef) and node.name in ("frame", "validate_replay")]
    if len(helpers) != 2 or any(helper is None for helper in helpers):
        raise ValueError("Replay helper interface changed; review the export")
    files["gaia-rl/tools/evaluation_replays.py"] = ("import copy\n\n" + "\n\n".join(helpers) + "\n").encode()
    files["gaia-rl/examples/replay_income.rs"] = read_regular(root, "gaia-engine/examples/replay_income.rs")
    for name in ("gaia-frontend/src/main.tsx", "gaia-frontend/index.html", "gaia-frontend/vite.config.ts",
                 "gaia-frontend/src/tests/setup.ts",
                 "examples/watch_game.py", "examples/test_watch_game.py", "setup_viewer.py", "VIEWER.md"):
        files[name] = read_regular(templates, name)
    files["ASSET-NOTICE.md"] = (
        "# Image distribution status\n\n"
        "Runtime game artwork is included at the owner's explicit request for this private development handoff.\n"
        "Private sharing is not proof of redistribution permission. No artwork license or public redistribution\n"
        "permission has been established by this project. Keep this notice and review permissions before\n"
        "further distribution. Rulebook PDFs, unused source scans, and third-party strategy articles are excluded.\n"
    ).encode()
    for name, value in (("ai-replays/index.json", {"schema_version": 1, "games": []}),
                        ("ai-replays/publication-times.json", {}),
                        ("ai-live/index.json", {"schema_version": 1, "games": []})):
        files[f"gaia-frontend/public/{name}"] = (json.dumps(value) + "\n").encode()
    return files


def read_regular(root: Path, relative: str) -> bytes:
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"Refusing source symlink: {relative}")
    if not path.is_file():
        raise ValueError(f"Required source file missing: {relative}")
    return path.read_bytes()


def package_metadata(root: Path) -> bytes:
    source = tomllib.loads(read_regular(root, "gaia-rl/pyproject.toml").decode())
    project, build = source["project"], source["build-system"]
    # Keep the existing versions; training frameworks are not part of this kit.
    return (f'''[build-system]
requires = {json.dumps(build["requires"])}
build-backend = {json.dumps(build["build-backend"])}

[project]
name = {json.dumps(project["name"])}
version = {json.dumps(project["version"])}
description = "Offline Gaia game environment; no bundled training policy."
requires-python = {json.dumps(project["requires-python"])}
dependencies = []

[project.optional-dependencies]
aec = {json.dumps(project["dependencies"])}

[tool.maturin]
python-source = "python"
module-name = "gaia_rl._native"
features = ["python"]
''').encode()


def payload(root: Path, templates: Path) -> dict[str, bytes]:
    result = {name: read_regular(root, name) for name in FILES}
    for directory, suffix in TREES.items():
        base = root / directory
        if base.is_symlink() or not base.is_dir():
            raise ValueError(f"Required source directory missing or symlinked: {directory}")
        selected = []
        for path in sorted(base.rglob("*")):
            name = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"Refusing source symlink: {name}")
            if any(part.startswith(".") for part in path.relative_to(base).parts):
                continue
            if path.is_file() and path.suffix == suffix:
                selected.append(name)
                result[name] = read_regular(root, name)
        if not selected:
            raise ValueError(f"No {suffix} files in required directory: {directory}")
    for name in TEMPLATE_FILES:
        result[name] = read_regular(templates, name)
    result["gaia-rl/pyproject.toml"] = package_metadata(root)
    result[".gitignore"] = b"**/target/\n**/.venv/\n__pycache__/\n*.pyc\n*.so\n*.pyd\n*.egg-info/\n.env\n.env.*\n/runs/\n/dist/\n"
    return result


def export(root: Path, destination: Path, templates: Path = TEMPLATES, *, with_viewer: bool = False) -> dict:
    root = root.resolve()
    if destination.is_symlink():
        raise ValueError("Destination must not be a symlink")
    destination = destination.resolve()
    if destination == root or root in destination.parents:
        raise ValueError("Choose a new destination outside the source repository")
    if destination.exists():
        raise FileExistsError("Destination already exists; nothing overwritten")
    files = payload(root, templates)
    if with_viewer:
        files.update(viewer_payload(root, templates))
        files["README.md"] = ("# 관전 UI 포함 전달본\n\n설치·AI 실행·관전은 [VIEWER.md](VIEWER.md)를 먼저 보세요.\n"
                              "이 전달본은 예외적으로 관전 UI와 런타임 이미지를 포함합니다.\n"
                              "아래 엔진 전용 설명의 이미지/UI 제외 문구는 기본 배포 모드에 해당합니다.\n"
                              "이미지 이용 조건은 [ASSET-NOTICE.md](ASSET-NOTICE.md)에 남겨두었습니다.\n\n").encode() + files["README.md"]
        files[".gitignore"] += b"**/node_modules/\n**/dist/\n*.tsbuildinfo\n"
    manifest = {
        "schema_version": 1,
        "scope": "engine-python-and-private-viewer" if with_viewer else "engine-and-python-environment",
        "release_ready": False,
        "license_status": "Owner must decide licensing and distribution before publication.",
        "files": {name: sha256(data).hexdigest() for name, data in sorted(files.items())},
        "adaptations": [
            "Python base dependencies removed; existing environment dependencies offered as aec extra.",
            "Training modules, policies, checkpoints and frontend-coupled integration tests excluded.",
            "Rust runtime source, data, build inputs and Python environment modules copied unchanged.",
        ],
    }
    if with_viewer:
        manifest["adaptations"].extend([
            "Explicit private handoff includes existing spectator UI/runtime artwork, not unused source scans or old games.",
            "Viewer entry is spectator-only; game-server proxies removed; local runner serves generated games only.",
            "Native income example reused under gaia-rl; only pure replay helpers extracted; no model/deploy entry points.",
        ])
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(files.items()):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    with (destination / "MANIFEST.json").open("x") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New folder outside this repository")
    parser.add_argument("--with-viewer", action="store_true", help="Include spectator UI and runtime artwork for explicitly authorized sharing")
    args = parser.parse_args()
    try:
        manifest = export(ROOT, args.output, with_viewer=args.with_viewer)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Export failed: {error}\n")
    print(json.dumps({"output": str(args.output.resolve()), "files": len(manifest["files"]),
                      "release_ready": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
