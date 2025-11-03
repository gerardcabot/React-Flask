import { useEffect, useState } from "react";
import axios from "axios";
import { Stage, Layer, Rect, Line, Text } from "react-konva";
import { useTranslation } from 'react-i18next';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const R2_PUBLIC_URL = import.meta.env.VITE_R2_PUBLIC_URL;

export default function PassMap({ playerId, season }) {
  const { t } = useTranslation();
  const [passes, setPasses] = useState([]);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    completed: true,
    incomplete: true,
    assists: true,
    finalThird: false
  });
  const [stats, setStats] = useState({
    completionRate: 0,
    finalThirdCompletionRate: 0,
    totalAssists: 0,
  });

  const heatmapUrl = (playerId && season && R2_PUBLIC_URL)
    ? `${R2_PUBLIC_URL}/${playerId}_${season}_pass_completion_heatmap.png`
    : null;

  const pitchWidth = 120;
  const pitchHeight = 80;
  const canvasWidth = 600;
  const canvasHeight = 400;
  const scaleX = canvasWidth / pitchWidth;
  const scaleY = canvasHeight / pitchHeight;

  useEffect(() => {
    if (!playerId || !season) return;
    setPasses([]);
    setError(null);

    axios
      .get(`${API_URL}/pass_map_plot`, {
        params: { player_id: playerId, season }
      })
      .then(res => {
        if (res.data.passes) {
          const passData = res.data.passes;
          setPasses(passData);

          const totalPasses = passData.length;
          const completedPasses = passData.filter(p => p.completed).length;
          const finalThirdPasses = passData.filter(p => p.final_third).length;
          const completedFinalThirdPasses = passData.filter(p => p.completed && p.final_third).length;
          const assists = passData.filter(p => p.assist).length;

          setStats({
            completionRate: totalPasses > 0 ? (completedPasses / totalPasses * 100).toFixed(2) : 0,
            finalThirdCompletionRate: finalThirdPasses > 0 ? (completedFinalThirdPasses / finalThirdPasses * 100).toFixed(2) : 0,
            totalAssists: assists,
          });
        } else {
          setError(t('visualization.passMapDetails.errorData'));
        }
      })
      .catch(err => {
        setError(t('visualization.passMapDetails.errorFetch'));
        console.error(err);
      });
  }, [playerId, season]);

  const handleFilterChange = (filterKey) => { setFilters(prev => ({...prev, [filterKey]: !prev[filterKey]})); };
  const drawPitch = () => {return (<><Rect x={0} y={0} width={canvasWidth} height={canvasHeight} fill="white" /><Line points={[0,0,canvasWidth,0,canvasWidth,canvasHeight,0,canvasHeight,0,0]} stroke="black" strokeWidth={2} closed /><Line points={[(120-16.5)*scaleX,(80/2-33/2)*scaleY,120*scaleX,(80/2-33/2)*scaleY,120*scaleX,(80/2+33/2)*scaleY,(120-16.5)*scaleX,(80/2+33/2)*scaleY,(120-16.5)*scaleX,(80/2-33/2)*scaleY]} stroke="black" strokeWidth={2} closed /><Line points={[(120-5.5)*scaleX,(80/2-11/2)*scaleY,120*scaleX,(80/2-11/2)*scaleY,120*scaleX,(80/2+11/2)*scaleY,(120-5.5)*scaleX,(80/2+11/2)*scaleY,(120-5.5)*scaleX,(80/2-11/2)*scaleY]} stroke="black" strokeWidth={2} closed /><Line points={[120*scaleX,(80/2-7.32/2)*scaleY,120*scaleX,(80/2+7.32/2)*scaleY]} stroke="black" strokeWidth={4} /><Rect x={10} y={10} width={15} height={15} fill="green"/><Text x={30} y={10} text={t('visualization.passMapDetails.completed')} fontSize={12}/><Rect x={10} y={30} width={15} height={15} fill="red"/><Text x={30} y={30} text={t('visualization.passMapDetails.incomplete')} fontSize={12}/><Rect x={10} y={50} width={15} height={15} fill="blue"/><Text x={30} y={50} text={t('visualization.passMapDetails.assists')} fontSize={12}/><Rect x={10} y={70} width={15} height={15} fill="purple"/><Text x={30} y={70} text={t('visualization.passMapDetails.finalThirdIfApplicable')} fontSize={12}/></>);};
  const filteredPasses = passes.filter(pass => { 
    const matchesCompleted = filters.completed && pass.completed && !pass.assist; 
    const matchesIncomplete = filters.incomplete && !pass.completed && !pass.assist; 
    const matchesAssist = filters.assists && pass.assist; 
    const matchesFinalThird = !filters.finalThird || (filters.finalThird && pass.final_third); 
    return (matchesCompleted || matchesIncomplete || matchesAssist) && matchesFinalThird; 
  });
  return (
    <div>
      <h3>{t('visualization.passMapDetails.title')}</h3>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ marginBottom: "10px" }}>
        <label><input type="checkbox" checked={filters.completed} onChange={() => handleFilterChange("completed")} /> {t('visualization.passMapDetails.completed')}</label>
        <label style={{ marginLeft: "10px" }}><input type="checkbox" checked={filters.incomplete} onChange={() => handleFilterChange("incomplete")} /> {t('visualization.passMapDetails.incomplete')}</label>
        <label style={{ marginLeft: "10px" }}><input type="checkbox" checked={filters.assists} onChange={() => handleFilterChange("assists")} /> {t('visualization.passMapDetails.assists')}</label>
        <label style={{ marginLeft: "10px" }}><input type="checkbox" checked={filters.finalThird} onChange={() => handleFilterChange("finalThird")} /> {t('visualization.passMapDetails.finalThird')}</label>
      </div>
      <Stage width={canvasWidth} height={canvasHeight}>
        <Layer>
          {drawPitch()}
          {filteredPasses.map((pass, index) => {
            const startX = pass.start_x*scaleX; const startY = pass.start_y*scaleY; const endX = pass.end_x*scaleX; const endY = pass.end_y*scaleY;
            let color = pass.assist ? "blue" : pass.completed ? "green" : "red";
            if (filters.finalThird && pass.final_third) color = pass.assist ? "blue" : "purple";
            return (<Line key={index} points={[startX, startY, endX, endY]} stroke={color} strokeWidth={2} lineCap="round" lineJoin="round" opacity={0.5} />);
          })}
        </Layer>
      </Stage>
      <div style={{ marginTop: "10px" }}>
        <p>{t('visualization.passMapDetails.completionRate')} {stats.completionRate}%</p>
        <p>{t('visualization.passMapDetails.finalThirdRate')} {stats.finalThirdCompletionRate}%</p>
        <p>{t('visualization.passMapDetails.totalAssists')} {stats.totalAssists}</p>
      </div>
      <div style={{ marginTop: "20px" }}>
        <h4>{t('visualization.passMapDetails.zoneCompletion')}</h4>
        {heatmapUrl ? (
          <>
            <img
              key={heatmapUrl}
              src={heatmapUrl}
              alt={t('visualization.passMapDetails.heatmapAlt')}
              style={{ maxWidth: "100%", border: "1px solid #ccc", display: 'block' }}
              onError={(e) => { e.target.style.display = 'none'; if(e.target.nextSibling) e.target.nextSibling.style.display = 'block'; }}
            />
            <p style={{ display: 'none', color: 'red' }}>{t('visualization.passMapDetails.errorLoading')}</p>
          </>
        ) : (
          <p>{t('visualization.passMapDetails.loading')}</p>
        )}
      </div>
    </div>
  );
}