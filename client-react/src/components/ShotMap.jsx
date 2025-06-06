import { useEffect, useState } from "react";
import axios from "axios";
import { Stage, Layer, Rect, Line, RegularPolygon, Text } from "react-konva";

export default function ShotMap({ playerId, season }) {
  const [shots, setShots] = useState([]);
  const [error, setError] = useState(null);
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, xg: 0 });
  const [stats, setStats] = useState({
    totalGoals: 0,
    totalXg: 0,
    overallXgDiff: 0,
  });

  const pitchWidth = 120;
  const pitchHeight = 80;
  const canvasWidth = 600;
  const canvasHeight = 400;
  const scaleX = canvasWidth / pitchWidth;
  const scaleY = canvasHeight / pitchHeight;

  useEffect(() => {
    if (!playerId || !season) return;
    setShots([]);
    setError(null);

    axios
      .get("http://localhost:5000/shot_map", {
        params: { player_id: playerId, season }
      })
      .then(res => {
        if (res.data.shots) {
          const shotData = res.data.shots;
          setShots(shotData);

          // Calculate statistics
          const totalGoals = shotData.filter(shot => shot.goal).length;
          const totalXg = shotData.reduce((sum, shot) => sum + shot.xg, 0).toFixed(2);
          const overallXgDiff = (totalGoals - parseFloat(totalXg)).toFixed(2);

          setStats({
            totalGoals,
            totalXg: parseFloat(totalXg),
            overallXgDiff: parseFloat(overallXgDiff),
          });
        } else {
          setError("No shot data returned");
        }
      })
      .catch(err => {
        console.error("Axios error:", err.response ? err.response.data : err.message);
        setError("Error fetching shot map: " + (err.response ? err.response.data.error : err.message));
      });
  }, [playerId, season]);

  const drawPitch = () => {
    const goalCenterY = pitchHeight / 2;
    const penaltyAreaWidth = 16.5;
    const penaltyAreaHeight = 33;
    const goalAreaWidth = 5.5;
    const goalAreaHeight = 11;
    const goalHeight = 7.32;

    return (
      <>
        <Rect
          x={0}
          y={0}
          width={canvasWidth}
          height={canvasHeight}
          fill="white"
        />
        <Line
          points={[0, 0, canvasWidth, 0, canvasWidth, canvasHeight, 0, canvasHeight, 0, 0]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + penaltyAreaHeight / 2) * scaleY,
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY + penaltyAreaHeight / 2) * scaleY,
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + goalAreaHeight / 2) * scaleY,
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY + goalAreaHeight / 2) * scaleY,
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            pitchWidth * scaleX, (goalCenterY - goalHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + goalHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={4}
        />
        <RegularPolygon
          x={(pitchWidth - 11) * scaleX}
          y={goalCenterY * scaleY}
          sides={6}
          radius={2}
          fill="black"
        />
        <Rect x={10} y={10} width={15} height={15} fill="#b94b75" />
        <Text x={30} y={10} text="Shot (No gol)" fontSize={12} />
        <Rect x={10} y={30} width={15} height={15} fill="#00ff00" />
        <Text x={30} y={30} text="Shot (Gol)" fontSize={12} />
      </>
    );
  };

  const handleMouseEnter = (shot, e) => {
    const stage = e.target.getStage();
    const pointerPosition = stage.getPointerPosition();
    setTooltip({
      visible: true,
      x: pointerPosition.x + 10,
      y: pointerPosition.y - 20,
      xg: shot.xg
    });
  };

  const handleMouseLeave = () => {
    setTooltip({ visible: false, x: 0, y: 0, xg: 0 });
  };

  return (
    <div style={{ position: "relative" }}>
      {/* <h3>Shot Map</h3> */}
      {error && <p style={{ color: "red" }}>{error}</p>}
      <Stage width={canvasWidth} height={canvasHeight}>
        <Layer>
          {drawPitch()}
          {shots.map((shot, index) => {
            const x = shot.x * scaleX;
            const y = shot.y * scaleY;
            const size = shot.xg * 500 + 100;
            return (
              <RegularPolygon
                key={index}
                x={x}
                y={y}
                sides={6}
                radius={Math.sqrt(size / Math.PI)}
                fill={shot.goal ? "#00ff00" : "#b94b75"}
                stroke="#383838"
                strokeWidth={1}
                rotation={30}
                onMouseEnter={(e) => handleMouseEnter(shot, e)}
                onMouseLeave={handleMouseLeave}
              />
            );
          })}
        </Layer>
      </Stage>
      <div style={{ marginTop: "10px" }}>
        <p>Gols totals: {stats.totalGoals}</p>
        <p>Gols esperats (xG) totals: {stats.totalXg.toFixed(2)}</p>
        <p>Diferència entre els gols i el xG (Gols - xG): {stats.overallXgDiff.toFixed(2)} </p>
        <p>Nota: Els valors positius en aquesta diferència indiquen un millor rendiment de l'esperat</p>
      </div>
      {tooltip.visible && (
        <div
          style={{
            position: "absolute",
            left: tooltip.x,
            top: tooltip.y,
            background: "rgba(0, 0, 0, 0.8)",
            color: "white",
            padding: "5px 10px",
            borderRadius: "5px",
            fontSize: "12px",
            pointerEvents: "none",
            zIndex: 1000,
          }}
        >
          xG: {tooltip.xg.toFixed(2)}
        </div>
      )}

    </div>
  );
}