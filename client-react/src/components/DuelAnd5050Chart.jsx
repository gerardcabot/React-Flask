import { Pie } from 'react-chartjs-2';

export default function DuelAnd5050Chart({ events }) {
  const duelResults = {};
  const fifty = {};

  events.forEach(e => {
    if (e.duel_outcome?.name) duelResults[e.duel_outcome.name] = (duelResults[e.duel_outcome.name] || 0) + 1;
    if (e["50_50"]) fifty["50_50"] = (fifty["50_50"] || 0) + 1;
  });

  const data = {
    labels: [...Object.keys(duelResults), ...Object.keys(fifty)],
    datasets: [{
      data: [...Object.values(duelResults), ...Object.values(fifty)],
      backgroundColor: ['#FFCE56', '#36A2EB', '#FF6384']
    }]
  };

  return <Pie data={data} />;
}
