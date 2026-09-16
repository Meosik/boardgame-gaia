"""Import an observed uiqoo randomizer DOM, not a locally regenerated seed.

Offline and setup-only: no player assignment, moves, publication, or remote code execution.
The input must be the rendered Lost Fleet module DOM after its images were assigned.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

MAPS = {
    'tech': {'1o1pw': 2, '4c': 3, '1o1q': 4, '1k1c': 5, 'big': 6,
             '7vp': 7, 'gaia': 8, 'planetk_lostfleet': 9, '4pw': 10},
    'adv': {'trade': 1, 'fed': 2, 'tradeb': 3, 'mineb': 4, 'sectoro': 5,
            'sector': 6, 'labpass': 7, 'adv': 8, 'gaia': 9, 'mine': 10,
            'fedpass': 11, 'deep': 12, 'big': 13, 'asteroidpass': 14,
            'deeppass': 15, 'qaction': 16, 'terra': 17, 'planetpass_lostfleet': 19,
            '3k': 20, '3o': 21, '1q5c': 22},
    'round': {'mine2': 1, 'terra2': 2, 'gaia4': 3, 'trade3': 4, 'fed5': 5,
              'big5': 6, 'gaia3': 7, 'trade4': 8, 'adv2': 9, 'planet3': 10,
              'sector3': 11, 'lab4': 12},
    'booster': {'rl': 1, 'pwt': 2, 'm': 3, 'big': 4, 'instant': 5, 'former': 6,
                'ts': 7, 'range': 8, 'q': 9, 'planet': 10, 'gaia': 11,
                'terra': 12, '1o1k': 13, 'deep': 14},
    'final': {'gaia': 1, 'deep': 2, 'fed': 3, 'planet_lostfleet': 4, 'building': 5,
              'asteroid': 6, 'sector': 8, 'distance': 9, 'satellite': 10},
    'artifact': {'deep': 1, 'pwt': 2, '1k1o': 3, 'gaia': 4, 'sci': 5,
                 '3c3o': 6, '3k1q': 7, 'proto': 8, '5c2o': 9, 'fed': 10,
                 'planet': 11, 'asteroid': 12, 'track': 13},
    'fed': {'vp': 1, 'q': 2, 'pwt': 3, 'o': 4, 'c': 5, 'k': 6},
    'shipfed': {'c': 8, 'vp': 9, 'k': 10, 'oq': 11, 'tech': 12, 'pwt': 13,
                'terra': 14, 'range': 15},
    'shiptech': {'terra': 11, 'range': 12, '1o3k': 13},
}


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = {}
        self.colors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img' and a.get('id') and a.get('src'):
            if a['id'] in self.images:
                raise ValueError(f"Duplicate image id: {a['id']}")
            self.images[a['id']] = a
        if tag == 'div' and a.get('class') == 'colororder':
            match = re.search(r'background-color:\s*([^;]+)', a.get('style', ''))
            if match:
                self.colors.append(match[1].strip())


def rotate(q, r, n):
    for _ in range(n % 6):
        q, r = -r, q + r
    return q, r


def style_number(image, key, unit='%'):
    match = re.search(rf'{re.escape(key)}:\s*(-?[\d.]+){unit}', image['style'])
    if not match:
        raise ValueError(f"Missing {key}: {image['id']}")
    return float(match[1])


def spin(image):
    match = re.search(r'rotate\((-?[\d.]+)deg\)', image.get('style', ''))
    angle = float(match[1]) if match else 0
    if angle % 60:
        raise ValueError('Non-hexagonal rotation')
    return int(angle / 60) % 6


def convert(html, url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if parsed.hostname != 'uiqoo.kr' or parsed.path != '/boardgames/gaiaproject/randomizer.html':
        raise ValueError('Expected the uiqoo Gaia Project randomizer URL')
    if query.get('player') != ['4'] or query.get('expan') != ['lostfleet']:
        raise ValueError('This importer supports only four-player Lost Fleet')
    if len(query.get('seed', [])) != 1:
        raise ValueError('An explicit seed is required')
    page = Images()
    page.feed(html)
    images = page.images

    def image_key(id, prefix):
        src = images[id]['src']
        match = re.fullmatch(re.escape(prefix) + r'_(\w+)\.png', src)
        if not match:
            raise ValueError(f'Unexpected asset for {id}: {src}')
        return match[1]

    def mapped(id, family):
        key = image_key(id, family)
        if key not in MAPS[family]:
            raise ValueError(f'Unmapped {family} image: {key}')
        return MAPS[family][key]

    # Source art and existing GameBoard use the same flat-top, 8-radius-wide scans.
    # Anchor the lattice to observed map5; source CSS offsets are rounded percentages.
    size = 25 / 8
    anchor = (style_number(images['map5'], 'margin-left') + 12.5,
              style_number(images['map5'], 'margin-top') + size * 5 * math.sqrt(3) / 2)
    residuals = []

    def axial(x, y, centroid=(0, 0)):
        q = (x - anchor[0]) / (size * 1.5) - centroid[0]
        r = (y - anchor[1]) / (size * math.sqrt(3)) - (q + centroid[0]) / 2 - centroid[1]
        qi, ri = round(q), round(r)
        residual = max(abs(q - qi), abs(r - ri))
        if residual > .12:
            raise ValueError(f'Image placement is not on the expected lattice: {q}, {r}')
        residuals.append(residual)
        return f'{qi},{ri}'

    sectors = []
    for prefix, count in [('map', 10), ('deep', 8)]:
        for i in range(count):
            image = images[f'{prefix}{i}']
            asset = re.fullmatch(r'map_(?:tile|deep)_(\d+)([ab]?)\.png', image['src'])
            if not asset:
                raise ValueError(f"Invalid sector asset: {image['src']}")
            sector_id, side = int(asset[1]), asset[2].upper() or None
            allowed_sides = ({'A', 'B'} if prefix == 'deep' else
                             {'A'} if sector_id in {5, 6, 7} else {None})
            if side not in allowed_sides or (sector_id > 10) != (prefix == 'deep'):
                raise ValueError(f"Unsupported sector face: {image['src']}")
            left, top = [style_number(image, k) for k in ('margin-left', 'margin-top')]
            width = style_number(image, 'width')
            if prefix == 'map':
                if width != 25:
                    raise ValueError('Unexpected standard sector width')
                rotation = (spin(image) + 4) % 6
                origin = axial(left + width / 2, top + width * 5 * math.sqrt(3) / 16)
            else:
                if width != 10.9:
                    raise ValueError('Unexpected deep sector width')
                rotation = (spin(image) + 1) % 6
                centroid = rotate(1/3, 1/3, rotation)
                origin = axial(left + width * .57,
                               top + width * 2 * math.sqrt(3) / 3.5 * .505, centroid)
            sectors.append({'sector_id': sector_id, 'side': side,
                            'origin': origin, 'rotation': rotation,
                            'source_image': image['src'], 'source_slot': image['id']})
    if {s['sector_id'] for s in sectors} != set(range(1, 19)):
        raise ValueError('Expected each of the 18 sectors exactly once')
    interspaces = []
    for i in range(10):
        image = images[f'interspace{i}']
        kind = image_key(f'interspace{i}', 'map_interspace')
        if kind not in {'empty', 'proto', 'asteroid', 'eclipse', 'tfmars', 'twilight', 'rebellion'}:
            raise ValueError(f'Unknown interspace {kind}')
        width = style_number(image, 'width')
        if width != 6.4:
            raise ValueError('Unexpected interspace width')
        # Single flat-top hex: width 2 radii, height sqrt(3) radii.
        coord = axial(style_number(image, 'margin-left') + width/2,
                      style_number(image, 'margin-top') + width*math.sqrt(3)/4)
        interspaces.append({'coord': coord, 'kind': kind, 'source_image': image['src']})
    colors = {'red': 'Oxide', 'orange': 'Volcanic', 'yellow': 'Desert',
              'saddlebrown': 'Swamp', 'gray': 'Titanium', 'white': 'Ice', 'blue': 'Terra'}
    if len(page.colors) != 7 or set(page.colors) != set(colors):
        raise ValueError('Missing or ambiguous terraforming color order')
    for id, allowed in [('econ', {'pw', 'vp'}), ('advcond', {'shuttle', 'vp'})]:
        if image_key(id, id) not in allowed:
            raise ValueError(f'Unknown board face: {id}')
    # Reject duplicate/overlapping tiles rather than silently overwriting board cells.
    occupied = set()
    for sector in sectors:
        offsets = ([(q, r) for q in range(-2, 3) for r in range(-2, 3)
                    if max(abs(q), abs(r), abs(q + r)) <= 2]
                   if sector['sector_id'] <= 10 else [(0, 0), (1, 0), (0, 1)])
        oq, or_ = map(int, sector['origin'].split(','))
        for q, r in offsets:
            q, r = rotate(q, r, sector['rotation'])
            coord = (oq + q, or_ + r)
            if coord in occupied:
                raise ValueError('Overlapping sectors')
            occupied.add(coord)
    for tile in interspaces:
        coord = tuple(map(int, tile['coord'].split(',')))
        if coord in occupied:
            raise ValueError('Overlapping interspace')
        occupied.add(coord)
    kinds = [tile['kind'] for tile in interspaces]
    if any(kinds.count(ship) != 1 for ship in ('twilight', 'eclipse', 'tfmars', 'rebellion')):
        raise ValueError('Expected exactly one of each spaceship')
    return {
        'schema_version': 1, 'kind': 'observed-randomizer-setup',
        'source': {'url': url, 'seed': query['seed'][0], 'player_count': 4,
                   'center_balance': query.get('centerbalance') == ['true'],
                   'rendered_dom_sha256': hashlib.sha256(html.encode()).hexdigest()},
        'factions_in_source_order': [image_key(f'race{i}', 'race') for i in range(4)],
        'player_assignments': None, 'bids': None, 'actions': [],
        'round_tile_ids': [mapped(f'round{i}', 'round') for i in range(6)],
        'final_scoring_ids': [mapped(f'final{i}', 'final') for i in range(2)],
        'booster_ids': [mapped(f'booster{i}', 'booster') for i in range(7)],
        'tech_tile_slot_ids': [mapped(f'tech{i}', 'tech') for i in range(9)],
        'advanced_tech_tile_ids': [mapped(f'advtech{i}', 'adv') for i in range(7)],
        'terraforming_level_5_token': mapped('fed0', 'fed'),
        'economy_research_tile_side': image_key('econ', 'econ'),
        'lost_fleet_advanced_tech_requirement': image_key('advcond', 'advcond'),
        'terraforming_color_order': [colors[c] for c in page.colors],
        'artifact_ids': [mapped(f'artifact{i}', 'artifact') for i in range(4)],
        'spaceship_federation_ids': [mapped(f'shipfed{i}', 'shipfed') for i in range(4)],
        'spaceship_tech_ids': [mapped(f'shiptech{i}', 'shiptech') for i in range(3)],
        'sectors': sectors, 'interspaces': interspaces,
        'geometry_max_rounding_residual_hex': max(residuals),
        'limits': ['Initial setup only; source faction order is not a confirmed player assignment.',
                   'No initial mines, bids, selected boosters, or gameplay actions were invented.',
                   'The same numeric seed is not equivalent to the local randomizer sequence.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dom', type=Path, required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = convert(args.dom.read_text(), args.url)
    with args.output.open('x') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(args.output)


if __name__ == '__main__':
    main()
