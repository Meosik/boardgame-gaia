// Only the `space_sector_NN.jpg` front faces are bundled here. Three
// `_back` variants also exist on disk (02, 07, 10) but are intentionally
// excluded from this glob: `BoardState.sectors` (what the frontend receives
// at runtime) carries no `side`/`back` flag to select them with — see the
// `sectorImageSrc` doc comment below — so they are unreachable via any
// current code path. They're left on disk (unconverted, full size) rather
// than deleted so the capability isn't silently lost if `BoardState` ever
// grows a side flag; bundling them today would just be dead weight.
//
// `eager: true` is kept: the 10 remaining files are ~80KB each (~800KB
// total) after downscaling/re-encoding, so eagerly bundling them no longer
// meaningfully hurts first paint, and it keeps `sectorImageSrc` synchronous
// for the SVG render path in GameBoard/index.tsx.
const SECTOR_IMAGES = import.meta.glob('./space_sectors/space_sector_[0-9][0-9].jpg', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/**
 * Resolve the image path for a map sector tile.
 *
 * `id` is the sector's numeric id (1-10, matching `space_sector_NN.jpg`).
 * `back` selects the `_back` variant for double-sided sectors (only 02, 07 and
 * 10 have a `_back` asset on disk today) — callers should only pass `back:
 * true` when they actually know which side is showing. `BoardState.sectors`
 * (what the frontend receives at runtime) does not carry a `side`/`back`
 * flag — that information exists only on `SectorPlacement` during game setup
 * and is not threaded through to the board the client renders — so board
 * rendering always uses the front face. Note: `_back` assets are not
 * currently bundled (see glob above), so passing `back: true` will resolve
 * to `null` until that asset is added to the glob pattern.
 */
export function sectorImageSrc(id: number, back = false): string | null {
  const padded = String(id).padStart(2, '0');
  const suffix = back ? '_back' : '';
  return SECTOR_IMAGES[`./space_sectors/space_sector_${padded}${suffix}.jpg`] ?? null;
}
