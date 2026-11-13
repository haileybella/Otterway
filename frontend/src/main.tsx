import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import '@fontsource/fraunces/900.css';
import './styles/global.css';
import App from './App.tsx';
import { AppStateProvider } from './state/AppState';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppStateProvider>
      <App />
    </AppStateProvider>
  </StrictMode>,
);
