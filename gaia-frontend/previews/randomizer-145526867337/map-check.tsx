// Isolated visual QA harness: avoid decoding every other board's artwork at once.
import { createRoot } from 'react-dom/client';
import '../../src/index.css';
import '../../src/styles/missing-classes.css';
import { GameBoard } from '../../src/components/GameBoard';
import { parseReplay } from '../../src/replay/records';
import { useGameStore } from '../../src/store/gameStore';

const root = createRoot(document.getElementById('root')!);
fetch('./setup-replay.json').then(response => response.json()).then(value => {
  const state = parseReplay(value).frames[0].state;
  useGameStore.getState().actions.setReadOnly(true);
  useGameStore.getState().actions.setGameState(state);
  root.render(<GameBoard board={state.board} players={state.players} />);
}).catch((error: unknown) => root.render(<p role="alert">{String(error)}</p>));
