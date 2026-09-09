# 이미지 업스케일링 점검 목록

2026-09-09 기준으로 실제 사용 여부와 원본 해상도를 함께 확인한 목록이다.

## 우선 작업 권장

### 행성 이미지 8종

- 대상: `planets/desert.png`, `ice.png`, `oxide.png`, `swamp.png`, `terra.png`,
  `titanium.png`, `transdim.png`, `volcanic.png`
- 현재 크기: 각각 132×132px
- 사용 위치: 메인 게임 보드의 행성
- 판단: 기본 표시 크기에서는 사용할 수 있지만 확대/고해상도 화면에서는 다른 업스케일 자산보다 흐리다.
- 권장 결과물: 투명 배경을 유지한 528×528px PNG. 형태, 색, 조명, 테두리를 바꾸지 않고 4배 업스케일한다.

### 미확인 행동칸 덮개 타일

- 대상: `boards/new_action_slot_cover_tile.png`
- 현재 크기: 40×43px
- 현재 상태: 보정 화면에서만 사용하며 실제 게임에는 아직 배치하지 않았다.
- 판단: 실물 용도와 배치 위치가 확정되기 전에는 구현하지 않는다. 사용하기로 확정되면 원본을 다시 촬영하거나 최소 8배 업스케일이 필요하다.

## 조건부 작업

- `icons/normalized/power_badge_1.webp` (76×88px)
- `icons/normalized/power_badge_3.webp` (85×87px)
- `icons/normalized/power_badge_4.webp` (89×101px)
- `icons/normalized/range.webp` (69×77px)

현재 UI 크기에는 충분하다. 32px보다 크게 표시하도록 바꿀 때만 원본 PNG를 4배 업스케일한 뒤 WebP 런타임 자산을 다시 만든다.

## 재작업 불필요

- `boards/terraforming_selection_board.*`: 제공된 고해상도 원본을 적용했다.
- `boards/lost_planet.*`: 업스케일 원본과 최적화 WebP를 적용했다.
- 자원 아이콘: 384px 런타임 자산으로 현재 표시 크기에 충분하다.
- 연구판, 점수판, 함선 보드, 종족 보드, 탐사 보드, 기술/점수/부스터 타일: 고해상도 또는 정규화 자산을 사용한다.
- `boards/scoring_track_extension.jpg` (1190×661px)와 `boards/lost_fleet_qic_board_overlay.jpg` (1274×524px): 현재 표시 크기에 충분하다.
