const renderedFederationTokens = import.meta.glob('./federation_tokens_rendered/fed_*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/** Green/available face only. The source scans contain both faces side-by-side; these rendered
 * crops prevent both physical tokens from appearing inside one UI slot. */
export function federationTokenImageSrc(tokenId: number): string | undefined {
  return renderedFederationTokens[
    `./federation_tokens_rendered/fed_${String(tokenId).padStart(2, '0')}.webp`
  ];
}
