import { Bar } from 'react-chartjs-2';

export default function GoalkeeperPerformanceChart({ events }) {
  const gk = events.filter(e => e.type?.name === "Goal Keeper" && e.goalkeeper_outcome?.name);

  const outcomeCount = {};
  gk.forEach(e => {
    const o = e.goalkeeper_outcome.name;
    outcomeCount[o] = (outcomeCount[o] || 0) + 1;
  });

  const data = {
    labels: Object.keys(outcomeCount),
    datasets: [{
      label: "GK Outcomes",
      data: Object.values(outcomeCount),
      backgroundColor: "purple"
    }]
  };

  return <Bar data={data} />;
}
