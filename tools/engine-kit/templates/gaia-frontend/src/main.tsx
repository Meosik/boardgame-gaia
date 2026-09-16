import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './styles/missing-classes.css';
import { AiReplay } from './components/AiReplay';

createRoot(document.getElementById('root')!).render(
  <StrictMode><AiReplay /></StrictMode>,
);
