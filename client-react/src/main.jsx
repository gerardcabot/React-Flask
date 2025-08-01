// // import { StrictMode } from 'react'
// // import { createRoot } from 'react-dom/client'
// // import './index.css'
// // import App from './App.jsx'

// // createRoot(document.getElementById('root')).render(
// //   <StrictMode>
// //     <App />
// //   </StrictMode>,
// // )

// import { StrictMode } from 'react'
// import { createRoot } from 'react-dom/client'
// import './index.css'
// import App from './App.jsx'
// import { Chart, BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend, ArcElement, PointElement, LineElement, Filler } from 'chart.js';

// // Registra aquí tots els components de Chart.js que la teva aplicació necessita
// Chart.register(
//   BarElement,
//   CategoryScale,
//   LinearScale,
//   ArcElement,
//   PointElement,
//   LineElement,
//   Title,
//   Tooltip,
//   Legend,
//   Filler
// );

// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <App />
//   </StrictMode>,
// )

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import AppWithLocation from './App.jsx'; // Nota: Importem AppWithLocation per incloure el Router

// Importa Chart.js i els components que necessites
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

// Registra tots els components UNA SOLA VEGADA aquí, al punt d'entrada de l'app.
// Això assegura que estiguin disponibles globalment abans que qualsevol component intenti usar-los.
Chart.register(
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,       // <-- El controlador per als gràfics de barres
  ArcElement,       // Per a gràfics circulars
  PointElement,     // Per als punts en gràfics de línia
  LineElement,      // Per a les línies en gràfics de línia
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