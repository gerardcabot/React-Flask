import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './responsive.css'; 
import AppWithLocation from './App.jsx'; 

import './i18n/config';

import {
  Chart,
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

Chart.register(
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,       
  ArcElement,       
  PointElement,     
  LineElement,      
  Title,
  Tooltip,
  Legend,
  Filler
);

const root = createRoot(document.getElementById('root'));
root.render(
  <StrictMode>
    <AppWithLocation />
  </StrictMode>
);