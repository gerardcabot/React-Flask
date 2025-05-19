import { useEffect, useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";

export default function XGGoalTrend({ playerId }) {
  const [trendData, setTrendData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId) return;

    setError(null);
    axios.get("http://localhost:5000/xg_goal_trend", {
      params: { player_id: playerId }
    })
    .then(res => {
      setTrendData(res.data.trend_data || []);
    })
    .catch(err => {
      setError("Error fetching xG and Goal trend data");
      console.error(err);
    });
  }, [playerId]);

  if (error) {
    return <p style={{ color: "red" }}>{error}</p>;
  }

//   if (!trendData.length) {
//     return <p>No xG or Goal data available across seasons.</p>;
//   }

  const seasons = trendData.map(data => data.season);
  const xgData = trendData.map(data => data.total_xg);
  const goalsData = trendData.map(data => data.goals);

  const chartData = {
    labels: seasons,
    datasets: [
      {
        label: "Total xG",
        data: xgData,
        borderColor: "rgba(75, 192, 192, 1)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
        fill: false,
        tension: 0.1,
      },
      {
        label: "Goals",
        data: goalsData,
        borderColor: "rgba(255, 99, 132, 1)",
        backgroundColor: "rgba(255, 99, 132, 0.2)",
        fill: false,
        tension: 0.1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top",
      },
      title: {
        display: true,
        text: "xG and Goals Trend Over Seasons",
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const datasetLabel = context.dataset.label || "";
            const value = context.parsed.y;
            const season = context.label;
            const data = trendData.find(d => d.season === season);
            if (datasetLabel === "Total xG") {
              return [
                `${datasetLabel}: ${value}`,
                `Shots Taken: ${data.shots_taken}`,
                `Avg xG/Shot: ${data.avg_xg_per_shot}`,
              ];
            } else {
              return [
                `${datasetLabel}: ${value}`,
                `Shots Taken: ${data.shots_taken}`,
              ];
            }
          },
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Season",
        },
      },
      y: {
        title: {
          display: true,
          text: "Value",
        },
        beginAtZero: true,
      },
    },
  };

  return (
    <div style={{ marginTop: "20px" }}>
      <Line data={chartData} options={options} />
    </div>
  );
}