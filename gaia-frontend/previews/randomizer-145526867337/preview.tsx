import { createRoot } from 'react-dom/client';
import '../../src/index.css';
import '../../src/styles/missing-classes.css';
import { App } from '../../src/App';
import { parseReplay } from '../../src/replay/records';
import { useGameStore } from '../../src/store/gameStore';

const root = createRoot(document.getElementById('root')!);
fetch('./setup-replay.json').then(response => {
  if (!response.ok) throw new Error('초기 세팅 파일을 읽지 못했습니다.');
  return response.json();
}).then(value => {
  const record = parseReplay(value);
  const actions = useGameStore.getState().actions;
  actions.setReadOnly(true);
  actions.setMyPlayerId(0);
  actions.setGameState(record.frames[0].state);
  root.render(<>
    <p role="status" style={{ margin: 0, padding: 12, background: '#252030', color: 'white' }}>
      초기 세팅 예시 · 시드 145526867337 · 지오덴 / 팅커로이드 / 하드슈 할라 / 모웨이드<br />
      비딩·좌석·초기 건물 미배정. 자원과 점수는 경기 관측값이 아닌 초기 엔진 표시값입니다.
      확장 고급기술 조건은 원본의 25점 면을 표시합니다. 읽기 전용이며 실제 경기에는 반영하지 않습니다.
    </p>
    <App replay={{ events: [], eventStart: 0, eventEnd: 0, onEventSelect: () => {} }} />
  </>);
}).catch((error: unknown) => {
  root.render(<p role="alert">{error instanceof Error ? error.message : '세팅 읽기 실패'}</p>);
});
