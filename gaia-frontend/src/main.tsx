import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './styles/missing-classes.css';
import { App } from './App';
import { AiReplay } from './components/AiReplay';
import { RewardPreview } from './components/RewardPreview';
import { LiveActivityPreview } from './components/LiveActivityPreview';

const params = new URLSearchParams(window.location.search);
const screen = params.get('rewardPreview') === '1' ? <RewardPreview />
  : params.get('activityPreview') === '1' ? <LiveActivityPreview />
    : params.get('aiReplay') === '1' ? <AiReplay />
      : <App />;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {screen}
  </StrictMode>,
);
