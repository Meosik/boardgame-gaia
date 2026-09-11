/**
 * Tile assets are named `<prefix>_<NN>_<한글 설명>.<ext>` (names live in
 * `scripts/asset_names.py`). Only the numeric id is a lookup key, so a description can be
 * corrected by renaming the file without touching code.
 */
export function indexAssetsById(
  modules: Record<string, string>,
  prefix: string,
): Map<number, string> {
  const pattern = new RegExp(`/${prefix}_(\\d+)(?:_[^/]*)?\\.\\w+$`);
  const byId = new Map<number, string>();
  for (const [path, url] of Object.entries(modules)) {
    const match = pattern.exec(path);
    if (match) byId.set(Number(match[1]), url);
  }
  return byId;
}
