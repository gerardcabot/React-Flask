import { useEffect, useState } from "react";
import axios from "axios";

export default function GoalkeeperStats({ playerId, season }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;

    setError(null);
    setImageUrl(null);

    axios.get("http://localhost:5000/goalkeeper_stats", {
      params: { player_id: playerId, season }
    })
    .then(res => {
      if (res.data.image_url) {
        setImageUrl(res.data.image_url);
      } else {
        setError("No shot-save map data available.");
      }
    })
    .catch(err => {
      setError("Error fetching shot-save map.");
      console.error(err);
    });
  }, [playerId, season]);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!imageUrl) return <p>Loading shot-save map...</p>;

  return (
    <div style={{ marginTop: "20px" }}>
      <h3>Shot-Save Map</h3>
      <img src={imageUrl} alt="Shot-Save Map" style={{ maxWidth: "100%", height: "auto" }} />
    </div>
  );
}