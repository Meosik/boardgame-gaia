# UIQOO setup-only example: 145526867337

Local preview: `http://localhost:5173/previews/randomizer-145526867337/`

Low-load static map capture: `http://localhost:5173/previews/randomizer-145526867337/map-preview.png`
Isolated map rendering check: `http://localhost:5173/previews/randomizer-145526867337/map-check.html`

Source: https://uiqoo.kr/boardgames/gaiaproject/randomizer.html?player=4&seed=145526867337&centerbalance=true&expan=lostfleet

This is a **read-only initial setup**, not a recorded or completed match. It uses the
existing App and replay parser without changing production routing, room rules,
or the public replay catalog. Start the existing frontend dev server to open it.

Confirmed from the rendered reference: all 18 sector placements/rotations/faces,
10 interspaces and four ship locations; round/final scoring, boosters, technology,
ship rewards, artifacts, terraforming token/color order and board faces.

The source offers Geodens, Tinkeroids, HadschHallas and Moweyds. Source order is
not treated as an observed player/seat assignment. Bids, initial mines, selected
boosters and actions remain unspecified. The four unassigned player records and
their resource/VP fields are native pre-selection placeholders, not video evidence.
The page banner explains this distinction.

The reference displays the **25 VP** advanced-tech requirement face. The preview
preserves that face; the engine's normal four-player **3 shuttles** rule is unchanged.
Booster display order follows the existing frontend, not the source's layout.

## Reproduce (from repository root)

Use a saved, fully rendered module DOM, not the unexecuted HTML source. Browser
capture is deliberately separate from the offline importer; it is not OCR or a
general video-recognition system. Unknown assets/layouts fail instead of guessing.

```sh
python3 gaia-rl/tools/import_uiqoo_setup.py \
  --dom /path/to/rendered-module.html \
  --url 'https://uiqoo.kr/boardgames/gaiaproject/randomizer.html?player=4&seed=145526867337&centerbalance=true&expan=lostfleet' \
  --output /tmp/new-observed-setup.json
CARGO_BUILD_JOBS=1 cargo run --offline -p gaia-engine --example import_uiqoo_setup -- \
  /tmp/new-observed-setup.json /tmp/new-setup-replay.json
```

Both exporters refuse to overwrite their output. Review a generated snapshot
before replacing this example's `setup-replay.json`. Do not publish this as a match.

## Targeted checks

```sh
python3 -m unittest discover -s gaia-rl/tools -p test_import_uiqoo_setup.py -v
cd gaia-frontend
./node_modules/.bin/vitest run previews/randomizer-145526867337/preview.test.ts --maxWorkers=1 --minWorkers=1
./node_modules/.bin/tsc -p previews/randomizer-145526867337/tsconfig.json
```

Capture/test evidence is in
`gaia-rl/runs/randomizer-import-145526867337.1ufwCEak/` (local, git-ignored).
Use `observed-setup-verified.json` and `setup-replay-verified.json`; the earlier
unqualified files are retained diagnostic captures with a superseded color mapping.
`visual-verdict` is not installed, so comparison is manual, not a skill verdict.
The bounded typecheck timed out at 180 seconds under a 50%-of-one-core CPU cap;
no typecheck/build pass is claimed. Runtime snapshot parsing and targeted tests
are separate evidence, not a replacement for a completed typecheck.

Verified: five Python tests and three frontend snapshot tests pass, including
source tile IDs, unassigned factions, all eight outer-sector faces, ship reward
ownership and the actual frontend's blue/brown/gray/red/white/yellow/orange mapping.
The initial App capture loaded successfully; a later full-height capture hit its
180-second limit near the 1 GiB memory cap. The final isolated map capture succeeded
under a 768 MiB cap and was compared manually against the source's sector layout,
rotation, outer-sector faces and spaceship positions. No full-page visual pass is
claimed. No existing game was played or modified and no public deployment occurred.

The final Rust example compiled and ran successfully. Its output matches this
preview except for the native creation timestamp. Smoke checks also confirmed
the other known board faces, refusal to overwrite an existing file, and rejection
of an unknown requirement face. `rustfmt --check` passed. These example checks do
not establish a production frontend build pass.

User correction (2026-09-14): source `shipfed1`/`shiptech0` belong to **TFMars**,
and `shipfed2`/`shiptech1` to **Eclipse**, not the reverse. Updated the adapter,
preview snapshot and regression expectations. Only these two ships' federation
tokens and technology piles changed; map positions and all other setup values
remain unchanged. Earlier run snapshots retain the superseded assignment.
