const artifactImages = import.meta.glob('./artifacts/artifact_*.jpg', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const byId = Object.fromEntries(
  Object.entries(artifactImages).flatMap(([path, src]) => {
    const id = Number(path.match(/artifact_(\d+)/)?.[1]);
    return Number.isInteger(id) ? [[id, src]] : [];
  }),
) as Record<number, string>;

export function artifactImageSrc(artifactId: number): string | undefined {
  return byId[artifactId];
}
