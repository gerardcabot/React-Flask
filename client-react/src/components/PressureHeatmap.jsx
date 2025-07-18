// // // import { useEffect, useState } from "react";
// // // import axios from "axios";

// // // export default function PressureHeatmap({ playerId, season }) {
// // //   const [imgUrl, setImgUrl] = useState(null);
// // //   const [error, setError] = useState(null);

// // //   useEffect(() => {
// // //     if (!playerId || !season) return;

// // //     setImgUrl(null);
// // //     setError(null);

// // //     axios.get("http://localhost:5000/pressure_heatmap", {
// // //       params: { player_id: playerId, season }
// // //     })
// // //     .then(res => {
// // //       if (res.data.image_url) {
// // //         const fullUrl = `http://localhost:5000${res.data.image_url}?t=${Date.now()}`;
// // //         setImgUrl(fullUrl);
// // //       } else {
// // //         setError("No s'ha retornat cap URL d'imatge");
// // //       }
// // //     })
// // //     .catch(err => {
// // //       setError("Error en obtenir el mapa de calor");
// // //       console.error(err);
// // //     });
// // //   }, [playerId, season]);

// // //   return (
// // //     <div>
// // //       {error && <p style={{ color: 'red' }}>{error}</p>}
// // //       {imgUrl ? (
// // //         <img
// // //           key={imgUrl}
// // //           src={imgUrl}
// // //           alt="Pressure Heatmap"
// // //           style={{ maxWidth: "100%", border: "1px solid #ccc" }}
// // //         />
// // //       ) : (
// // //         !error && <p>S'està carregant el mapa de calor...</p>
// // //       )}
// // //     </div>
// // //   );
// // // }

// // import { useEffect, useState } from "react";
// // import axios from "axios";

// // // 1. Definir la variable de la API al principio del archivo
// // const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// // export default function PressureHeatmap({ playerId, season }) {
// //   const [imgUrl, setImgUrl] = useState(null);
// //   const [error, setError] = useState(null);

// //   useEffect(() => {
// //     if (!playerId || !season) return;

// //     setImgUrl(null);
// //     setError(null);

// //     // 2. Modificar la llamada a axios y la construcción de la URL
// //     axios.get(`${API_URL}/pressure_heatmap`, {
// //       params: { player_id: playerId, season }
// //     })
// //     .then(res => {
// //       if (res.data.image_url) {
// //         const fullUrl = `${API_URL}${res.data.image_url}?t=${Date.now()}`;
// //         setImgUrl(fullUrl);
// //       } else {
// //         setError(res.data.error || "No s'ha retornat cap URL d'imatge");
// //       }
// //     })
// //     .catch(err => {
// //       setError(err.response?.data?.error || "Error en obtenir el mapa de calor");
// //       console.error(err);
// //     });
// //   }, [playerId, season]);

// //   return (
// //     <div>
// //       {error && <p style={{ color: 'red' }}>{error}</p>}
// //       {imgUrl ? (
// //         <img
// //           key={imgUrl}
// //           src={imgUrl}
// //           alt="Pressure Heatmap"
// //           style={{ maxWidth: "100%", border: "1px solid #ccc" }}
// //         />
// //       ) : (
// //         !error && <p>S'està carregant el mapa de calor...</p>
// //       )}
// //     </div>
// //   );
// // }

// import React from 'react';

// const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// export default function PressureHeatmap({ playerId, season }) {
//   if (!playerId || !season) {
//     return <p>Selecciona un jugador i una temporada per veure el mapa de calor.</p>;
//   }

//   // Aquesta URL apunta al teu backend. El backend farà la redirecció a R2.
//   const imageUrl = `${API_URL}/pressure_heatmap?player_id=${playerId}&season=${season}`;

//   return (
//     <div>
//       <img
//         key={imageUrl}
//         src={imageUrl}
//         alt={`Mapa de calor de pressió per al jugador ${playerId} en la temporada ${season}`}
//         style={{ maxWidth: "100%", border: "1px solid #ccc", minHeight: '100px', display: 'block' }}
//         onError={(e) => {
//           e.target.style.display = 'none';
//           if (e.target.nextSibling) {
//             e.target.nextSibling.style.display = 'block';
//           }
//         }}
//       />
//       <p style={{ display: 'none', color: 'red' }}>No s'ha pogut carregar el mapa de calor. Potser no existeix per a aquesta selecció.</p>
//     </div>
//   );
// }

import React from 'react';

const R2_PUBLIC_URL = import.meta.env.VITE_R2_PUBLIC_URL;

export default function PressureHeatmap({ playerId, season }) {
  if (!playerId || !season || !R2_PUBLIC_URL) {
    return <p>Selecciona un jugador i una temporada.</p>;
  }

  const imageUrl = `${R2_PUBLIC_URL}/${playerId}_${season}_pressure_heatmap.png`;

  return (
    <div>
      <img
        key={imageUrl}
        src={imageUrl}
        alt={`Mapa de calor de pressió per a ${playerId} en la temporada ${season}`}
        style={{ maxWidth: "100%", border: "1px solid #ccc", minHeight: '100px', display: 'block' }}
        onError={(e) => {
          e.target.style.display = 'none';
          if (e.target.nextSibling) e.target.nextSibling.style.display = 'block';
        }}
      />
      <p style={{ display: 'none', color: 'red' }}>No s'ha pogut carregar el mapa de calor. Potser no existeix per a aquesta selecció.</p>
    </div>
  );
}