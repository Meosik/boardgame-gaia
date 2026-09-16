// Low-memory visual QA: the real viewer/data, with only its existing board viewport hidden.
import { createRoot } from 'react-dom/client';
import '../../src/index.css';
import '../../src/styles/missing-classes.css';
import { AiReplay } from '../../src/components/AiReplay';

createRoot(document.getElementById('root')!).render(<AiReplay />);
let attempts = 0;
const timer = setInterval(() => {
  const select = document.querySelector<HTMLSelectElement>('[aria-label="리플레이 게임"]');
  const option = select && Array.from(select.options).find(item => item.value.startsWith('live-'));
  if (select && option) {
    select.value = option.value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
    clearInterval(timer);
  } else if (++attempts === 20) clearInterval(timer);
}, 500);
