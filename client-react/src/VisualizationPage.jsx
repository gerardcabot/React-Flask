import React, { useState, useEffect } from 'react';
import ShotMap from './components/ShotMap';
import PassMap from './components/PassMap';
import PositionHeatmap from './components/PositionHeatmap';
import PressureHeatmap from './components/PressureHeatmap';
import { useTranslation } from 'react-i18next';

const VisualizationPage = () => {
  const { t } = useTranslation();
  const [seasons, setSeasons] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedSeason, setSelectedSeason] = useState('');
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [passType, setPassType] = useState('all');
  const [shotData, setShotData] = useState([]);
  const [passData, setPassData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/seasons')
      .then(res => res.json())
      .then(data => setSeasons(data))
      .catch(() => setError(t('error_fetching_seasons')));
  }, [t]);

  useEffect(() => {
    if (selectedSeason) {
      setIsLoading(true);
      fetch(`/api/players?season_id=${selectedSeason}`)
        .then(res => res.json())
        .then(data => {
          setPlayers(data);
          setSelectedPlayer('');
          setShotData([]);
          setPassData([]);
        })
        .catch(() => setError(t('error_fetching_players')))
        .finally(() => setIsLoading(false));
    } else {
      setPlayers([]);
    }
  }, [selectedSeason, t]);

  const handleFetchData = () => {
    if (selectedPlayer && selectedSeason) {
      setIsLoading(true);
      setError('');
      
      const shotRequest = fetch(`/api/shots?player_id=${selectedPlayer}&season_id=${selectedSeason}`)
        .then(res => res.json());
      
      const passRequest = fetch(`/api/passes?player_id=${selectedPlayer}&season_id=${selectedSeason}`)
        .then(res => res.json());

      Promise.all([shotRequest, passRequest])
        .then(([shotData, passData]) => {
          setShotData(shotData);
          setPassData(passData);
        })
        .catch(() => setError(t('error_fetching_data')))
        .finally(() => setIsLoading(false));
    }
  };

  const filteredPassData = passType === 'all' 
    ? passData 
    : passData.filter(p => p.pass_outcome_name === passType);

  return (
    <div>
      <h1>{t('visualizations_title')}</h1>
      <div className="controls">
        <select onChange={e => setSelectedSeason(e.target.value)} value={selectedSeason}>
          <option value="">{t('select_season')}</option>
          {seasons.map(season => (
            <option key={season.season_id} value={season.season_id}>
              {season.season_name}
            </option>
          ))}
        </select>
        <select onChange={e => setSelectedPlayer(e.target.value)} value={selectedPlayer} disabled={!selectedSeason}>
          <option value="">{t('select_player')}</option>
          {players.map(player => (
            <option key={player.player_id} value={player.player_id}>
              {player.player_name}
            </option>
          ))}
        </select>
        <button onClick={handleFetchData} disabled={!selectedPlayer || !selectedSeason || isLoading}>
          {isLoading ? t('loading') : t('get_visualizations')}
        </button>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div className="visualization-content">
        {shotData.length > 0 && (
          <div className="shot-map-section">
            <h2>{t('shot_map')}
                <span className="tooltip">
                    <i className="info-icon">i</i>
                    <span className="tooltip-text">{t('shot_map_tooltip')}</span>
                </span>
            </h2>
            <div className="map-container">
                <ShotMap shotData={shotData} />
            </div>
          </div>
        )}

        {passData.length > 0 && (
          <div className="pass-map-section">
            <h2>{t('pass_map')}
                <span className="tooltip">
                    <i className="info-icon">i</i>
                    <span className="tooltip-text">{t('pass_map_tooltip')}</span>
                </span>
            </h2>
            <div className="pass-options">
              <label><input type="radio" name="passType" value="all" checked={passType === 'all'} onChange={e => setPassType(e.target.value)} /> {t('all_passes')}</label>
              <label><input type="radio" name="passType" value="Complete" checked={passType === 'Complete'} onChange={e => setPassType(e.target.value)} /> {t('complete')}</label>
              <label><input type="radio" name="passType" value="Incomplete" checked={passType === 'Incomplete'} onChange={e => setPassType(e.target.value)} /> {t('incomplete')}</label>
            </div>
             <div className="map-container">
                <PassMap passData={filteredPassData} />
            </div>
          </div>
        )}
        
        {selectedPlayer && selectedSeason && (
            <div className="heatmaps-section">
                <h2>{t('heatmaps')}
                    <span className="tooltip">
                        <i className="info-icon">i</i>
                        <span className="tooltip-text">{t('heatmaps_tooltip')}</span>
                    </span>
                </h2>
                <div style={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap' }}>
                    <PositionHeatmap playerId={selectedPlayer} seasonId={selectedSeason} />
                    <PressureHeatmap playerId={selectedPlayer} seasonId={selectedSeason} />
                </div>
            </div>
        )}

      </div>
    </div>
  );
};

export default VisualizationPage;