import { describe, it, expect } from 'vitest';
import { selectableFederationHexes, validateFederationSelection } from '../components/federationSelection';
import type { GameState, PlayerState, Hex } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 0,
      credits: 0,
      knowledge: 0,
      qic: 0,
      power: { bowl1: 4, bowl2: 4, bowl3: 4, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    federated_hexes: [{ q: 0, r: 0 }],
    ...overrides,
  };
}

function mockHex(overrides: Partial<Hex> & { q: number; r: number }): Hex {
  const { q, r, ...rest } = overrides;
  return {
    coord: { q, r },
    planet: null,
    space_tile_kind: null,
    structures: [],
    satellites: [],
    ...rest,
  };
}

// Rulebook p.14, "Connecting Planets": a newly formed federation's planets/satellites cannot be
// directly adjacent to planets/satellites of any of the player's existing federations. This used
// to be enforced by silently omitting such hexes from the clickable set (no feedback at all); the
// fix makes them clickable and lets `validateFederationSelection`'s own adjacency check produce
// an explanatory reason instead.
describe('federation adjacency-exclusivity UX', () => {
  function stateWithAdjacentCandidate(): GameState {
    const hexes: Record<string, Hex> = {
      '0,0': mockHex({
        q: 0,
        r: 0,
        planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
        structures: [{ owner: 0, kind: 'Mine' }],
      }),
      // Directly adjacent to (0,0) — see HexCoord::neighbors, (q+1, r) is a neighbor.
      '1,0': mockHex({
        q: 1,
        r: 0,
        planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
        structures: [{ owner: 0, kind: 'Mine' }],
      }),
    };
    return {
      players: [mockPlayer()],
      board: { sectors: [], hexes, lost_planet: null, spaceship_tiles: {} },
    } as unknown as GameState;
  }

  it('includes a hex adjacent to an existing federation in the clickable set', () => {
    const state = stateWithAdjacentCandidate();
    const selectable = selectableFederationHexes(state, 0, []);
    expect(selectable).toContainEqual({ q: 1, r: 0 });
  });

  it('rejects that hex with an explanatory reason once selected, instead of silently doing nothing', () => {
    const state = stateWithAdjacentCandidate();
    const status = validateFederationSelection(state, 0, [{ q: 1, r: 0 }]);
    expect(status.valid).toBe(false);
    expect(status.reason).toBe('기존 연방과 인접한 칸은 새 연방에 사용할 수 없습니다.');
  });

  it('counts gray Ivits tokens and excludes only the Terraforming 5 bonus', () => {
    const state = stateWithAdjacentCandidate();
    const player = state.players[0];
    player.faction = 'Ivits';
    player.federation_tokens = [3];
    player.gray_federation_tokens = [4];
    expect(validateFederationSelection(state, 0, []).minimumPower).toBe(21);
    player.research_tracks.terraforming = 5;
    expect(validateFederationSelection(state, 0, []).minimumPower).toBe(14);
    player.federation_tokens.push(5);
    expect(validateFederationSelection(state, 0, []).minimumPower).toBe(21);
  });

  it('requires the Xenos institute for the six-power minimum', () => {
    const state = stateWithAdjacentCandidate();
    state.players[0].faction = 'Xenos';
    expect(validateFederationSelection(state, 0, []).minimumPower).toBe(7);
    state.players[0].structures.push({ hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' });
    expect(validateFederationSelection(state, 0, []).minimumPower).toBe(6);
  });

  it('still allows Ivits to grow their one federation into an adjacent hex', () => {
    const state = stateWithAdjacentCandidate();
    state.players[0].faction = 'Ivits';
    const selectable = selectableFederationHexes(state, 0, []);
    expect(selectable).toContainEqual({ q: 1, r: 0 });
    const status = validateFederationSelection(state, 0, [{ q: 1, r: 0 }]);
    expect(status.reason).not.toBe('기존 연방과 인접한 칸은 새 연방에 사용할 수 없습니다.');
  });
});

describe('Ivits first federation QIC cost', () => {
  function firstFederation(qic: number, power: number): GameState {
    const player = mockPlayer({ faction: 'Ivits', federated_hexes: [] });
    player.resources.qic = qic;
    player.resources.power = { ...player.resources.power, bowl1: power, bowl2: 0, bowl3: 0 };
    const hexes: Record<string, Hex> = {};
    for (const q of [0, 1, 2, 3]) {
      const kind = q === 0 ? 'PlanetaryInstitute' : 'TradingStation';
      hexes[`${q},0`] = mockHex({ q, r: 0, ...(q !== 1 ? {
        planet: { planet_type: 'Oxide' as const, owner: 0, is_gaia_formed: false },
        structures: [{ owner: 0, kind }],
      } : {}) });
    }
    return { players: [player], board: { hexes, spaceship_tiles: {} } } as unknown as GameState;
  }
  const selected = [0, 1, 2, 3].map(q => ({ q, r: 0 }));
  it('allows a first bridge with QIC even without power', () => {
    const state = firstFederation(1, 0);
    expect(validateFederationSelection(state, 0, selected).valid).toBe(true);
    expect(selectableFederationHexes(state, 0, [{ q: 0, r: 0 }])).toContainEqual({ q: 1, r: 0 });
  });
  it('rejects a first bridge without QIC even when power is available', () => {
    const state = firstFederation(0, 12);
    expect(validateFederationSelection(state, 0, selected).reason).toBe('정보 큐브가 부족합니다.');
    expect(selectableFederationHexes(state, 0, [{ q: 0, r: 0 }])).not.toContainEqual({ q: 1, r: 0 });
  });
});
