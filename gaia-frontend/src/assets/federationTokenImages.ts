const normalizedBaseFederationTokens = import.meta.glob('./federation_tokens/normalized/fed_*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const normalizedLostFleetFederationTokens = import.meta.glob(
  './federation_tokens_lost_fleet/normalized/fed_*.png',
  { eager: true, import: 'default' },
) as Record<string, string>;

const normalizedFederationTokenBacks = import.meta.glob(
  './federation_tokens/normalized/back/runtime/fed_*.webp',
  { eager: true, import: 'default' },
) as Record<string, string>;

/** Green/available face only. Base tokens use the 1254 px upscaled sources after deterministic
 * single-face extraction and orientation correction. Token 7 is deliberately absent: that
 * reward belongs to the Gleens-only token (id 16), not the shared Federation supply. */
export function federationTokenImageSrc(tokenId: number): string | undefined {
  if (tokenId === 7) return undefined;

  const normalizedBase = normalizedBaseFederationTokens[
    `./federation_tokens/normalized/fed_${String(tokenId).padStart(2, '0')}.webp`
  ];
  if (normalizedBase) return normalizedBase;

  const normalizedLostFleet = normalizedLostFleetFederationTokens[
    `./federation_tokens_lost_fleet/normalized/fed_${String(tokenId).padStart(2, '0')}.png`
  ];
  return normalizedLostFleet;
}

/** Gray/used face. Token 1 has identical faces, so its approved front asset is reused. */
export function federationTokenBackImageSrc(tokenId: number): string | undefined {
  if (tokenId === 1) return federationTokenImageSrc(tokenId);
  if (tokenId === 7) return undefined;

  return normalizedFederationTokenBacks[
    `./federation_tokens/normalized/back/runtime/fed_${String(tokenId).padStart(2, '0')}.webp`
  ];
}
