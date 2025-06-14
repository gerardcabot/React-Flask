import { useEffect, useState } from "react";
import axios from "axios";

export default function PressureHeatmap({ playerId, season }) {
  const [imgUrl, setImgUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;

    setImgUrl(null);
    setError(null);

    axios.get("http://localhost:5000/pressure_heatmap", {
      params: { player_id: playerId, season }
    })
    .then(res => {
      if (res.data.image_url) {
        const fullUrl = `http://localhost:5000${res.data.image_url}?t=${Date.now()}`;
        setImgUrl(fullUrl);
      } else {
        setError("No s'ha retornat cap URL d'imatge");
      }
    })
    .catch(err => {
      setError("Error en obtenir el mapa de calor");
      console.error(err);
    });
  }, [playerId, season]);

  return (
    <div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {imgUrl ? (
        <img
          key={imgUrl}
          src={imgUrl}
          alt="Pressure Heatmap"
          style={{ maxWidth: "100%", border: "1px solid #ccc" }}
        />
      ) : (
        !error && <p>S'està carregant el mapa de calor...</p>
      )}
    </div>
  );
}