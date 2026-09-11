import { indexAssetsById } from './assetIndex';

const artifacts = indexAssetsById(
  import.meta.glob('./artifacts/normalized/artifact_*.webp', {
    eager: true,
    import: 'default',
  }) as Record<string, string>,
  'artifact',
);

export function artifactImageSrc(artifactId: number): string | undefined {
  return artifacts.get(artifactId);
}
