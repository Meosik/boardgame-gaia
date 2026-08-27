const rendered = import.meta.glob('./tech_tiles/rendered/*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

function renderedTechTile(prefix: 'std' | 'adv', tileId: number): string | undefined {
  return rendered[`./tech_tiles/rendered/${prefix}_${String(tileId).padStart(2, '0')}.webp`];
}

export function standardTechTileImageSrc(tileId: number): string | undefined {
  return renderedTechTile('std', tileId);
}

export function advancedTechTileImageSrc(tileId: number): string | undefined {
  return renderedTechTile('adv', tileId);
}
