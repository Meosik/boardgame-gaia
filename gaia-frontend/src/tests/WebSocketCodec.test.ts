import { describe, expect, it } from 'vitest';
import { decodeHexCoordinates, encodeHexCoordinates } from '../api/websocket';

describe('WebSocket HexCoord codec', () => {
  it('encodes setup and multi-hex action coordinates as Rust q,r strings', () => {
    expect(
      encodeHexCoordinates({
        setup: { coord: { q: 2, r: -1 } },
        federation: { hexes: [{ q: 0, r: 0 }, { q: -3, r: 4 }] },
      }),
    ).toEqual({
      setup: { coord: '2,-1' },
      federation: { hexes: ['0,0', '-3,4'] },
    });
  });

  it('decodes snapshot coordinates while preserving coordinate map keys', () => {
    expect(
      decodeHexCoordinates({
        board: {
          hexes: {
            '2,-1': { coord: '2,-1' },
          },
          sectors: [{ origin: '0,0' }],
        },
      }),
    ).toEqual({
      board: {
        hexes: {
          '2,-1': { coord: { q: 2, r: -1 } },
        },
        sectors: [{ origin: { q: 0, r: 0 } }],
      },
    });
  });
});
