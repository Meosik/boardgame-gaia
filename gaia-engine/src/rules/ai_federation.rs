//! Exact, resource-bounded federation search over zero-cost connected components.
//! DP terminals match the rule validator's free clusters; route reconstruction contracts
//! those clusters too, retaining all minimum satellite sets without cycling through their
//! internal paths. Building subsets are still checked separately against the actual rules.
//! Truly separated empires remain exponential. On SearchLimit, ai_decisions logs a warning
//! and retains non-federation legal actions instead of failing the entire turn.
use super::*;
use std::collections::BTreeSet;

const MAX_DP_CELLS: usize = 2_000_000;
const MAX_WORK: usize = 50_000_000;
const INF: usize = usize::MAX / 4;

struct Graph {
    coords: Vec<HexCoord>,
    weight: Vec<usize>,
    edges: Vec<Vec<usize>>,
    zero_component: Vec<Option<usize>>,
    components: Vec<Vec<usize>>,
    route_edges: Vec<Vec<usize>>,
}

impl Graph {
    fn new(state: &GameState, player: PlayerId, growth: bool) -> Self {
        let existing = &state.player(player).map(|p| p.federated_hexes.clone()).unwrap_or_default();
        let mut coords: Vec<_> = state.board.hexes.keys().copied().filter(|coord| {
            if !growth && (existing.contains(coord) || coord.neighbors().iter().any(|n| existing.contains(n))) {
                return false;
            }
            (growth && existing.contains(coord)) || player_owns_colonized_hex(state, player, *coord)
                || can_be_satellite_node(state, player, *coord)
        }).collect();
        coords.sort_by_key(|c| (c.q, c.r));
        let by_coord: HashMap<_, _> = coords.iter().enumerate().map(|(i, c)| (*c, i)).collect();
        let weight = coords.iter().map(|c| usize::from(!(player_owns_colonized_hex(state, player, *c)
            || (growth && existing.contains(c))))).collect();
        let edges = coords.iter().map(|c| c.neighbors().iter().filter_map(|n| by_coord.get(n).copied()).collect()).collect();
        Self::from_nodes(coords, weight, edges)
    }

    fn from_nodes(coords: Vec<HexCoord>, weight: Vec<usize>, edges: Vec<Vec<usize>>) -> Self {
        let mut zero_component = vec![None; coords.len()];
        let mut components = Vec::new();
        for start in 0..coords.len() {
            if weight[start] != 0 || zero_component[start].is_some() { continue; }
            let component = components.len();
            zero_component[start] = Some(component);
            let mut members = Vec::new();
            let mut queue = VecDeque::from([start]);
            while let Some(node) = queue.pop_front() {
                members.push(node);
                for &next in &edges[node] {
                    if weight[next] == 0 && zero_component[next].is_none() {
                        zero_component[next] = Some(component);
                        queue.push_back(next);
                    }
                }
            }
            components.push(members);
        }
        // Trace the quotient graph, not every zero-cost path/cycle inside a cluster.
        // DP still uses the original nodes and seeds every possible cluster entrance.
        let representative = |v: usize| zero_component[v].map_or(v, |c| components[c][0]);
        let mut route_edges = vec![Vec::new(); coords.len()];
        for (node, neighbors) in edges.iter().enumerate() {
            let from = representative(node);
            for &next in neighbors {
                let to = representative(next);
                if from != to { route_edges[from].push(to); }
            }
        }
        for neighbors in &mut route_edges { neighbors.sort_unstable(); neighbors.dedup(); }
        Self { coords, weight, edges, zero_component, components, route_edges }
    }

    fn terminals(&self, nodes: &[usize]) -> Vec<usize> {
        nodes.iter().filter_map(|&v| self.zero_component[v])
            .collect::<BTreeSet<_>>().into_iter().collect()
    }

    fn routes(&self, terminals: &[usize], max_satellites: usize, budget: &mut usize,
        cache: &mut BTreeMap<Vec<usize>, Vec<usize>>,
    ) -> Result<BTreeSet<Vec<usize>>, AiActionError> {
        let Some(count) = 1usize.checked_shl(terminals.len() as u32) else {
            return Err(AiActionError::SearchLimit("terminal count"));
        };
        let n = self.coords.len();
        if count.saturating_mul(n) > MAX_DP_CELLS {
            return Err(AiActionError::SearchLimit("DP cells"));
        }
        let keys: Vec<Vec<usize>> = (0..count).map(|mask| {
            let mut key: Vec<_> = terminals.iter().enumerate()
                .filter(|(bit, _)| mask & (1 << bit) != 0).map(|(_, &v)| v).collect();
            key.sort_unstable(); key
        }).collect();
        for mask in 1..count {
            if cache.contains_key(&keys[mask]) { continue; }
            if (cache.len() + 1).saturating_mul(n) > MAX_DP_CELLS {
                return Err(AiActionError::SearchLimit("cached DP cells"));
            }
            let mut costs = vec![INF; n];
            if mask.is_power_of_two() {
                for &node in &self.components[terminals[mask.trailing_zeros() as usize]] {
                    costs[node] = 0;
                }
            }
            let mut sub = (mask - 1) & mask;
            while sub > 0 {
                let other = mask ^ sub;
                if sub < other {
                    spend(budget, n)?;
                    let left = &cache[&keys[sub]];
                    let right = &cache[&keys[other]];
                    for v in 0..n {
                        let value = left[v].saturating_add(right[v]).saturating_sub(self.weight[v]);
                        costs[v] = costs[v].min(value);
                    }
                }
                sub = (sub - 1) & mask;
            }
            let mut heap = BinaryHeap::new();
            for (v, &cost) in costs.iter().enumerate() {
                if cost < INF { heap.push((Reverse(cost), v)); }
            }
            while let Some((Reverse(cost), v)) = heap.pop() {
                spend(budget, 1)?;
                if cost != costs[v] { continue; }
                for &u in &self.edges[v] {
                    let next = cost + self.weight[u];
                    if next < costs[u] { costs[u] = next; heap.push((Reverse(next), u)); }
                }
            }
            cache.insert(keys[mask].clone(), costs);
        }
        // All subsets of a building combination reuse the same graph/terminal cost rows,
        // including subsets seen while enumerating a different federation combination.
        let dp: Vec<&[usize]> = keys.iter().map(|key| cache.get(key).map(Vec::as_slice).unwrap_or(&[])).collect();
        // A cluster's representative has all its entrances in the quotient graph.
        let root = self.components[terminals[0]][0];
        if dp[count - 1][root] == INF || dp[count - 1][root] > max_satellites { return Ok(BTreeSet::new()); }
        let trees = self.trace(&dp, terminals, (count - 1, root), &mut BTreeSet::new(), budget, &mut BTreeMap::new())?;
        Ok(trees.into_iter().map(|tree| tree.into_iter().filter(|&v| self.weight[v] != 0).collect()).collect())
    }

    fn trace(&self, dp: &[&[usize]], terminals: &[usize], position: (usize, usize),
        stack: &mut BTreeSet<(usize, usize)>, budget: &mut usize,
        memo: &mut BTreeMap<(usize, usize), BTreeSet<Vec<usize>>>,
    ) -> Result<BTreeSet<Vec<usize>>, AiActionError> {
        let (mask, node) = position;
        let unconstrained = !stack.iter().any(|(ancestor_mask, _)| *ancestor_mask == mask);
        if unconstrained {
            if let Some(trees) = memo.get(&(mask, node)) { return Ok(trees.clone()); }
        }
        spend(budget, 1)?;
        if !stack.insert((mask, node)) { return Ok(BTreeSet::new()); }
        let mut trees = BTreeSet::new();
        if mask.is_power_of_two() && self.zero_component[node] == Some(terminals[mask.trailing_zeros() as usize]) {
            trees.insert(vec![node]);
        }
        for &prev in &self.route_edges[node] {
            if dp[mask][prev].saturating_add(self.weight[node]) == dp[mask][node] {
                for mut tree in self.trace(dp, terminals, (mask, prev), stack, budget, memo)? {
                    tree.push(node); tree.sort_unstable(); tree.dedup();
                    trees.insert(tree);
                }
            }
        }
        let mut sub = (mask - 1) & mask;
        while sub > 0 {
            let other = mask ^ sub;
            if sub < other && dp[sub][node] < INF && dp[other][node] < INF
                && dp[sub][node] + dp[other][node] - self.weight[node] == dp[mask][node] {
                let left = self.trace(dp, terminals, (sub, node), stack, budget, memo)?;
                let right = self.trace(dp, terminals, (other, node), stack, budget, memo)?;
                for a in &left {
                    for b in &right {
                        spend(budget, 1)?;
                        let mut tree = a.clone(); tree.extend(b); tree.sort_unstable(); tree.dedup();
                        if tree.iter().map(|&v| self.weight[v]).sum::<usize>() == dp[mask][node] {
                            trees.insert(tree);
                        }
                    }
                }
            }
            sub = (sub - 1) & mask;
        }
        stack.remove(&(mask, node));
        // Cache only calls with no same-mask path restriction. Memoizing a cycle-pruned
        // recursive call would incorrectly hide an alternative shortest path from another root.
        if unconstrained { memo.insert((mask, node), trees.clone()); }
        Ok(trees)
    }
}

fn spend(budget: &mut usize, count: usize) -> Result<(), AiActionError> {
    *budget = budget.checked_sub(count).ok_or(AiActionError::SearchLimit("search work"))?;
    Ok(())
}

pub(super) fn federation_candidates(state: &GameState, player_id: PlayerId) -> Result<Vec<GameAction>, AiActionError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let growth = player.faction == Some(FactionId::Ivits) && !player.federated_hexes.is_empty();
    let graph = Graph::new(state, player_id, growth);
    let owned: Vec<_> = graph.coords.iter().copied().filter(|c|
        player_owns_colonized_hex(state, player_id, *c) && !player.federated_hexes.contains(c)).collect();
    let minimum = federation_minimum_power(player, growth);
    if federation_power_total(state, player_id, &owned, &player.federated_hexes, growth) < minimum {
        return Ok(Vec::new());
    }
    let tokens: Vec<_> = state.research_board.federation_tokens.iter()
        .map(|token| FederationTokenChoice::Supply { kind: token.0 })
        .chain(SpaceshipId::all().into_iter().map(|ship| FederationTokenChoice::Spaceship { ship }))
        .filter(|token| resolve_federation_token_choice(state, player_id, *token).is_ok()).collect();
    if tokens.is_empty() { return Ok(Vec::new()); }
    let Some(subsets) = 1usize.checked_shl(owned.len() as u32) else {
        return Err(AiActionError::SearchLimit("owned structures"));
    };
    if subsets > MAX_WORK { return Err(AiActionError::SearchLimit("building combinations")); }
    let index: HashMap<_, _> = graph.coords.iter().enumerate().map(|(i, c)| (*c, i)).collect();
    let available = if player.faction == Some(FactionId::Ivits) { usize::from(player.resources.qic) }
        else { usize::from(player.resources.power.bowl1) + usize::from(player.resources.power.bowl2) + usize::from(player.resources.power.bowl3) };
    let supply_left = 25usize.saturating_sub(state.board.hexes.values().filter(|h| h.satellites.contains(&player_id)).count());
    let max_satellites = available.min(supply_left);
    let mut pair_distances = HashMap::default();
    for &source in index.values().filter(|&&v| graph.weight[v] == 0) {
        let mut distances = vec![INF; graph.coords.len()];
        distances[source] = 0;
        let mut heap = BinaryHeap::from([(Reverse(0usize), source)]);
        while let Some((Reverse(cost), node)) = heap.pop() {
            if cost != distances[node] { continue; }
            for &next in &graph.edges[node] {
                let new_cost = cost + graph.weight[next];
                if new_cost < distances[next] { distances[next] = new_cost; heap.push((Reverse(new_cost), next)); }
            }
        }
        pair_distances.insert(source, distances);
    }
    let mut shapes = BTreeMap::new();
    let mut budget = MAX_WORK;
    let mut route_cache = BTreeMap::new();
    for mask in 1..subsets {
        spend(&mut budget, 1)?;
        let required: Vec<_> = owned.iter().enumerate().filter(|(i, _)| mask & (1 << i) != 0).map(|(_, c)| *c).collect();
        if federation_power_total(state, player_id, &required, &player.federated_hexes, growth) < minimum { continue; }
        let mut required_nodes: Vec<_> = required.iter().map(|c| index[c]).collect();
        if growth {
            if let Some(anchor) = player.federated_hexes.first().and_then(|c| index.get(c)) { required_nodes.push(*anchor); }
        }
        let terminals = graph.terminals(&required_nodes);
        // Any connected solution contains a path between every pair. A pair already beyond
        // the spendable satellite budget proves the whole combination is unaffordable.
        if required_nodes.iter().any(|a| required_nodes.iter().any(|&b| pair_distances[a][b] > max_satellites)) { continue; }
        let mut connected = required.clone();
        if growth { connected.extend(&player.federated_hexes); }
        let trees = if MapEngine::is_connected(&connected) {
            BTreeSet::from([Vec::new()])
        } else { graph.routes(&terminals, max_satellites, &mut budget, &mut route_cache)? };
        for tree in trees {
            // Do not auto-include a whole cluster: extra buildings may make a federation
            // redundant. Every owned-building subset is considered by the outer loop;
            // validation rejects a subset that omits a necessary zero-cost connector.
            let hexes = required.clone();
            let satellites: Vec<_> = tree.into_iter().map(|v| graph.coords[v]).collect();
            let key = serde_json::to_string(&(&hexes, &satellites))?;
            shapes.insert(key, (hexes, satellites));
        }
    }
    let mut actions = BTreeMap::new();
    for (_, (hexes, satellite_hexes)) in shapes {
        for token in &tokens {
            let kind = resolve_federation_token_choice(state, player_id, *token)?;
            let mut bonuses = vec![(None, None, None)];
            match federation_token_kind(kind) {
                FederationTokenKind::LostFleetFreeBuildUnlimitedRange | FederationTokenKind::LostFleetFreeBuild3Steps => {
                    bonuses = state.board.hexes.keys().map(|&c| (Some(c), None, None)).collect();
                }
                FederationTokenKind::LostFleetTechTileOfChoice => {
                    for choice in valid_standard_tech_tile_choices(state, player_id) {
                        if let TechTileChoice::Standard { tile, advance_track, bonus_build_coord } = choice {
                            bonuses.push((bonus_build_coord, Some(tile), advance_track));
                        }
                    }
                }
                _ => {}
            }
            for (bonus_build_coord, bonus_tech_tile, bonus_research_track) in bonuses {
                spend(&mut budget, 1)?;
                let action = GameAction::FormFederation { hexes: hexes.clone(), satellite_hexes: satellite_hexes.clone(),
                    token: *token, bonus_build_coord, bonus_tech_tile, bonus_research_track };
                if RuleEngine::validate_action(state, player_id, &action).is_ok() {
                    actions.insert(serde_json::to_string(&action)?, action);
                }
            }
        }
    }
    Ok(actions.into_values().collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn diamond_preserves_both_minimal_routes() {
        let graph = Graph::from_nodes(
            (0..4).map(|q| HexCoord::new(q, 0)).collect(),
            vec![0, 1, 1, 0],
            vec![vec![1, 2], vec![0, 3], vec![0, 3], vec![1, 2]],
        );
        let routes = graph.routes(&graph.terminals(&[0, 3]), usize::MAX, &mut MAX_WORK.clone(), &mut BTreeMap::new()).unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(routes, BTreeSet::from([vec![1], vec![2]]));
    }

    #[test]
    fn route_solver_matches_exhaustive_small_graphs() {
        // Every connected vertex subset is an independent oracle, not a second DP.
        for edge_mask in 0..64usize {
            let pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)];
            let mut edges = vec![Vec::new(); 4];
            for (bit, &(a, b)) in pairs.iter().enumerate() {
                if edge_mask & (1 << bit) != 0 { edges[a].push(b); edges[b].push(a); }
            }
            let graph = Graph::from_nodes((0..4).map(|q| HexCoord::new(q, 0)).collect(), vec![0, 1, 1, 0], edges);
            let mut expected = BTreeSet::new();
            let mut best = usize::MAX;
            for mask in 0..16usize {
                if mask & 9 != 9 { continue; }
                let nodes: Vec<_> = (0..4).filter(|i| mask & (1 << i) != 0).collect();
                let mut visited = BTreeSet::from([0]);
                let mut queue = VecDeque::from([0]);
                while let Some(node) = queue.pop_front() {
                    for &next in &graph.edges[node] {
                        if nodes.contains(&next) && visited.insert(next) { queue.push_back(next); }
                    }
                }
                if visited.len() != nodes.len() { continue; }
                let cost = nodes.iter().map(|&i| graph.weight[i]).sum();
                if cost < best { best = cost; expected.clear(); }
                if cost == best { expected.insert(nodes.into_iter().filter(|&v| graph.weight[v] != 0).collect::<Vec<_>>()); }
            }
            let actual = graph.routes(&graph.terminals(&[0, 3]), usize::MAX, &mut MAX_WORK.clone(), &mut BTreeMap::new()).unwrap_or_else(|e| panic!("{e}"));
            assert_eq!(actual, expected, "edge mask {edge_mask}");
        }
    }

    #[test]
    fn fifteen_owned_nodes_use_three_terminal_components() {
        let weights: Vec<_> = (0..17).map(|v| usize::from(v == 5 || v == 11)).collect();
        let mut edges = vec![Vec::new(); 17];
        for a in 0..17 {
            for b in a + 1..17 {
                // Dense zero-cost cycles inside each cluster; satellite exits are at
                // the far end, not the node chosen as the component representative.
                if b == a + 1 || (weights[a] == 0 && weights[b] == 0 && a / 6 == b / 6) {
                    edges[a].push(b); edges[b].push(a);
                }
            }
        }
        let graph = Graph::from_nodes((0..17).map(|q| HexCoord::new(q, 0)).collect(), weights, edges);
        let owned: Vec<_> = (0..17).filter(|&v| graph.weight[v] == 0).collect();
        let terminals = graph.terminals(&owned);
        assert_eq!(owned.len(), 15);
        assert_eq!(terminals, vec![0, 1, 2]);
        let mut cache = BTreeMap::new();
        let mut budget = 2_000;
        let routes = graph.routes(&terminals, 2, &mut budget, &mut cache).unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(routes, BTreeSet::from([vec![5, 11]]));
        assert_eq!(cache.len(), 7, "DP rows must depend on clusters, not individual planets");
        for (component, members) in graph.components.iter().enumerate() {
            for node in members { assert_eq!(cache[&vec![component]][*node], 0); }
        }
        assert_eq!(graph.terminals(&[4, 10, 16]), terminals);
        assert!(graph.routes(&terminals, 1, &mut budget, &mut cache).unwrap_or_else(|e| panic!("{e}")).is_empty());
    }

    #[test]
    fn clustered_routes_match_exhaustive_five_node_graphs() {
        let pairs = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)];
        for edge_mask in 0..1usize << pairs.len() {
            let mut edges = vec![Vec::new(); 5];
            for (bit, &(a, b)) in pairs.iter().enumerate() {
                if edge_mask & (1 << bit) != 0 { edges[a].push(b); edges[b].push(a); }
            }
            let graph = Graph::from_nodes((0..5).map(|q| HexCoord::new(q, 0)).collect(), vec![0, 0, 1, 1, 0], edges);
            for required in [vec![0, 4], vec![0, 1, 4], vec![0, 1]] {
                let mut best = usize::MAX;
                let mut expected = BTreeSet::new();
                for mask in 1..32usize {
                    if required.iter().any(|&v| mask & (1 << v) == 0) { continue; }
                    let nodes: Vec<_> = (0..5).filter(|v| mask & (1 << v) != 0).collect();
                    let mut visited = BTreeSet::from([nodes[0]]);
                    let mut queue = VecDeque::from([nodes[0]]);
                    while let Some(node) = queue.pop_front() {
                        for &next in &graph.edges[node] {
                            if nodes.contains(&next) && visited.insert(next) { queue.push_back(next); }
                        }
                    }
                    if visited.len() != nodes.len() { continue; }
                    let satellites: Vec<_> = nodes.into_iter().filter(|&v| graph.weight[v] != 0).collect();
                    if satellites.len() < best { best = satellites.len(); expected.clear(); }
                    if satellites.len() == best { expected.insert(satellites); }
                }
                let actual = graph.routes(&graph.terminals(&required), usize::MAX, &mut MAX_WORK.clone(), &mut BTreeMap::new())
                    .unwrap_or_else(|e| panic!("{e}"));
                assert_eq!(actual, expected, "edge mask {edge_mask}, required {required:?}");
            }
        }
    }
}
