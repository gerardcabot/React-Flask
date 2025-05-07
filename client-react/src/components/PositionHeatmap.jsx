import { useState, useEffect } from "react";
import axios from "axios";

export default function PositionHeatmap({ playerId, season }) {
  const [imgData, setImgData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;

    axios.get("http://localhost:5000/position_heatmap", {
      params: { player_id: playerId, season }
    })
    .then(res => {
      if (res.data.image) {
        setImgData(res.data.image);
        setError(null);
      } else {
        setError("No image returned");
        setImgData(null);
      }
    })
    .catch(err => {
      setError("Error fetching position heatmap");
      console.error(err);
    });
  }, [playerId, season]);

  return (
    <div>
      <h3>Position Heatmap (StatsBomb Pitch)</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {imgData ? (
        <img
          src={imgData}
          alt="Position Heatmap"
          style={{ maxWidth: "100%", border: "1px solid #ccc" }}
        />
      ) : (
        !error && <p>Loading position heatmap...</p>
      )}
    </div>
  );
}