import { indexAssetsById } from './assetIndex';

const baseFederationTokens = indexAssetsById(
  import.meta.glob('./federation_tokens/normalized/fed_*.webp', {
    eager: true,
    import: 'default',
  }) as Record<string, string>,
  'fed',
);

const lostFleetFederationTokens = indexAssetsById(
  import.meta.glob('./federation_tokens_lost_fleet/normalized/fed_*.png', {
    eager: true,
    import: 'default',
  }) as Record<string, string>,
  'fed',
);

const federationTokenBacks = indexAssetsById(
  import.meta.glob('./federation_tokens/normalized/back/runtime/fed_*.webp', {
    eager: true,
    import: 'default',
  }) as Record<string, string>,
  'fed',
);

/** Green/available face only. Base tokens use the 1254 px upscaled sources after deterministic
 * single-face extraction and orientation correction. Token 7 is deliberately absent: that
 * reward belongs to the Gleens-only token (id 16), not the shared Federation supply. */
export function federationTokenImageSrc(tokenId: number): string | undefined {
  if (tokenId === 7) return undefined;

  return baseFederationTokens.get(tokenId) ?? lostFleetFederationTokens.get(tokenId);
}

/** Gray/used face. Token 1 has identical faces, so its approved front asset is reused. */
export function federationTokenBackImageSrc(tokenId: number): string | undefined {
  if (tokenId === 1) return federationTokenImageSrc(tokenId);
  if (tokenId === 7) return undefined;

  return federationTokenBacks.get(tokenId);
}
