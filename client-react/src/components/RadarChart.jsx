import { useState, useEffect } from "react";
import axios from "axios";

export default function RadarChart({ playerId, season }) {
  const [imgUrl, setImgUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;

    setImgUrl(null);
    setError(null);

    axios.get("http://localhost:5000/radar_chart", {
      params: { player_id: playerId, season }
    })
    .then(res => {
      if (res.data.image_url) {
        setImgUrl("http://localhost:5000" + res.data.image_url);
      } else {
        setError("No image returned");
      }
    })
    .catch(err => {
      console.error(err);
      setError("Error fetching radar chart");
    });
  }, [playerId, season]);

  return (
    <div>
      <h3>Player Stats Radar Chart</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {imgUrl ? (
        <img
          src={imgUrl}
          alt="Radar Chart"
          style={{ maxWidth: "100%", border: "1px solid #ccc" }}
        />
      ) : (
        !error && <p>Loading radar chart...</p>
      )}
    </div>
  );
}
