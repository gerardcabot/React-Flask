import { useEffect, useRef, useState } from "react";
import axios from "axios";

function GoalkeeperDistributionMap({ playerId, season }) {
  const [passes, setPasses] = useState([]);
  const [error, setError] = useState(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!playerId || !season) return;
    setError(null);
    setPasses([]);
    axios
      .get("http://localhost:5000/goalkeeper_distribution_map", {
        params: { player_id: playerId, season },
      })
      .then((res) => setPasses(res.data.passes || []))
      .catch((err) => setError("Failed to load distribution data"));
  }, [playerId, season]);

  useEffect(() => {
    if (!canvasRef.current || !passes.length) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw pitch (simple)
    ctx.fillStyle = "#22312b";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.strokeRect(20, 20, canvas.width - 40, canvas.height - 40);

    // Draw passes
    passes.forEach((p) => {
      const [x1, y1] = pitchCoords(p.origin, canvas.width, canvas.height);
      const [x2, y2] = pitchCoords(p.end_location, canvas.width, canvas.height);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle =
        p.outcome && p.outcome.toLowerCase().includes("complete")
          ? "#4caf50"
          : "#f44336";
      ctx.lineWidth = 2;
      ctx.stroke();
      // Draw arrow head
      drawArrowHead(ctx, x1, y1, x2, y2, ctx.strokeStyle);
    });
  }, [passes]);

  function pitchCoords([x, y], w, h) {
    // StatsBomb pitch: 120x80, map to canvas with 20px margin
    const px = 20 + (x / 120) * (w - 40);
    const py = 20 + (y / 80) * (h - 40);
    return [px, py];
  }

  function drawArrowHead(ctx, x1, y1, x2, y2, color) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const size = 8;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(
      x2 - size * Math.cos(angle - Math.PI / 7),
      y2 - size * Math.sin(angle - Math.PI / 7)
    );
    ctx.lineTo(
      x2 - size * Math.cos(angle + Math.PI / 7),
      y2 - size * Math.sin(angle + Math.PI / 7)
    );
    ctx.lineTo(x2, y2);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }

  if (error) return <div style={{ color: "red" }}>{error}</div>;
  if (!passes.length)
    return <div style={{ color: "#888" }}>No goalkeeper passes found.</div>;

  return (
    <div style={{ width: "100%", textAlign: "center" }}>
      <h4>Goalkeeper Distribution Map</h4>
      <canvas
        ref={canvasRef}
        width={400}
        height={270}
        style={{
          background: "#22312b",
          borderRadius: 8,
          border: "1px solid #dee2e6",
          maxWidth: "100%",
        }}
      />
      <div style={{ fontSize: 13, color: "#888", marginTop: 6 }}>
        Green: Completed, Red: Incomplete
      </div>
    </div>
  );
}

export default GoalkeeperDistributionMap;
