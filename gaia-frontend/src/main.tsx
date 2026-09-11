import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './styles/missing-classes.css';
import { App } from './App';
import { AiReplay } from './components/AiReplay';
import { RewardPreview } from './components/RewardPreview';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {new URLSearchParams(window.location.search).get('rewardPreview') === '1' ? <RewardPreview /> : new URLSearchParams(window.location.search).get('aiReplay') === '1' ? <AiReplay /> : <App />}
  </StrictMode>,
);
