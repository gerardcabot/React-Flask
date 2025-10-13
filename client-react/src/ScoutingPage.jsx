import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const ScoutingPage = () => {
    const { t } = useTranslation();
    const [positions, setPositions] = useState([]);
    const [selectedPosition, setSelectedPosition] = useState('');
    const [kpis, setKpis] = useState({
        atacant: { pes_regat: 0, pes_gol: 0, pes_remat: 0, pes_passada_clau: 0, pes_assistencia: 0, pes_conduccio: 0, pes_xG: 0, pes_xA: 0 },
        defensor: { pes_entrada: 0, pes_intercepcio: 0, pes_falta_comesa: 0, pes_targeta_grogra: 0, pes_targeta_vermella: 0, pes_duel_aeri: 0 },
        migcampista: { pes_passada_clau: 0, pes_assistencia: 0, pes_passada_progressiva: 0, pes_conduccio: 0, pes_pre_assistencia: 0, pes_xA: 0 }
    });
    const [similarPlayers, setSimilarPlayers] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        fetch('/api/positions')
            .then(res => res.json())
            .then(data => setPositions(data))
            .catch(() => setError(t('scouting.error_positions')));
    }, [t]);

    const handleKpiChange = (position, kpi, value) => {
        setKpis(prev => ({
            ...prev,
            [position]: { ...prev[position], [kpi]: parseFloat(value) }
        }));
    };

    const findSimilarPlayers = () => {
        if (!selectedPosition) {
            setError(t('scouting.error_select_position'));
            return;
        }

        const weights = kpis[selectedPosition];
        const totalWeight = Object.values(weights).reduce((sum, value) => sum + value, 0);

        if (totalWeight <= 0) {
            setError(t('scouting.error_positive_kpi'));
            return;
        }

        setIsLoading(true);
        setError('');
        setSimilarPlayers([]);

        fetch('/api/similar_players', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ position: selectedPosition, weights })
        })
        .then(res => {
            if (!res.ok) {
                throw new Error('Network response was not ok');
            }
            return res.json();
        })
        .then(data => {
            setSimilarPlayers(data);
        })
        .catch(() => {
            setError(t('scouting.error_finding_players'));
        })
        .finally(() => {
            setIsLoading(false);
        });
    };
    
    const renderKpiSliders = (position) => {
        return Object.keys(kpis[position]).map(kpi => (
            <div key={kpi} style={{ marginBottom: '15px' }}>
                <label>
                    {t(`kpis.${kpi}`)}: {kpis[position][kpi]}
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={kpis[position][kpi]}
                        onChange={(e) => handleKpiChange(position, kpi, e.target.value)}
                        style={{ width: '100%' }}
                    />
                </label>
            </div>
        ));
    };

    return (
        <div className="scouting-container" style={{ padding: '20px' }}>
            <h1>{t('scouting.title')}</h1>
            
            <div className="scouting-row" style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                <div className="scouting-column" style={{ flex: 1, padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
                    <h2>{t('scouting.step1_title')}
                        <span className="tooltip">
                            <i className="info-icon">i</i>
                            <span className="tooltip-text">{t('scouting.step1_tooltip')}</span>
                        </span>
                    </h2>
                    <div className="scouting-controls">
                        <select onChange={(e) => setSelectedPosition(e.target.value)} value={selectedPosition}>
                            <option value="">{t('scouting.select_position')}</option>
                            {positions.map(pos => (
                                <option key={pos} value={pos}>{t(`positions.${pos}`)}</option>
                            ))}
                        </select>
                    </div>
                    {selectedPosition && (
                        <div>
                            <h3>{t('scouting.define_kpis', { position: t(`positions.${selectedPosition}`) })}</h3>
                            {renderKpiSliders(selectedPosition)}
                        </div>
                    )}
                    <button onClick={findSimilarPlayers} disabled={isLoading || !selectedPosition}>
                        {isLoading ? t('scouting.searching') : t('scouting.find_players')}
                    </button>
                </div>

                <div className="scouting-column" style={{ flex: 2, padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
                    <h2>{t('scouting.step2_title')}
                        <span className="tooltip">
                           <i className="info-icon">i</i>
                           <span className="tooltip-text">{t('scouting.step2_tooltip')}</span>
                        </span>
                    </h2>
                    {error && <p style={{ color: 'red' }}>{error}</p>}
                    <div className="results-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', justifyContent: 'center' }}>
                        {similarPlayers.length > 0 ? (
                            similarPlayers.map(player => (
                                <div key={player.player_id} className="player-card" style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '15px', flexBasis: 'calc(33.333% - 30px)', boxSizing: 'border-box' }}>
                                    <h4>{player.player_name}</h4>
                                    <p>{t('scouting.similarity')}: {(player.similarity * 100).toFixed(2)}%</p>
                                    <p>{t('scouting.season')}: {player.season_name}</p>
                                </div>
                            ))
                        ) : (
                            !isLoading && <p>{t('scouting.no_results')}</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ScoutingPage;