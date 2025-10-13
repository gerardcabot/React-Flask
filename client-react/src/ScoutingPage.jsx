// ScoutingPage.jsx
import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import dayjs from "dayjs";
import React from "react";
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import './App.css';
import './responsive.css';

const ScoutingPage = () => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [seasons, setSeasons] = useState([]);
    const [leagues, setLeagues] = useState([]);
    const [teams, setTeams] = useState([]);
    const [players, setPlayers] = useState([]);
    const [selectedSeason, setSelectedSeason] = useState('');
    const [selectedLeague, setSelectedLeague] = useState('');
    const [selectedTeam, setSelectedTeam] = useState('');
    const [selectedPlayer, setSelectedPlayer] = useState('');
    const [kpiWeights, setKpiWeights] = useState({
        attacking: 33,
        defending: 33,
        playmaking: 34,
    });
    const [similarPlayers, setSimilarPlayers] = useState([]);
    const [error, setError] = useState(null);

    const backendUrl = import.meta.env.VITE_BACKEND_URL;

    useEffect(() => {
        fetch(`${backendUrl}/seasons`)
            .then(response => response.json())
            .then(data => setSeasons(data))
            .catch(error => console.error('Error fetching seasons:', error));
    }, [backendUrl]);

    const handleSeasonChange = (e) => {
        const seasonId = e.target.value;
        setSelectedSeason(seasonId);
        setSelectedLeague('');
        setSelectedTeam('');
        setSelectedPlayer('');
        setLeagues([]);
        setTeams([]);
        setPlayers([]);
        if (seasonId) {
            fetch(`${backendUrl}/leagues?season_id=${seasonId}`)
                .then(response => response.json())
                .then(data => setLeagues(data))
                .catch(error => console.error('Error fetching leagues:', error));
        }
    };

    const handleLeagueChange = (e) => {
        const leagueId = e.target.value;
        setSelectedLeague(leagueId);
        setSelectedTeam('');
        setSelectedPlayer('');
        setTeams([]);
        setPlayers([]);
        if (leagueId) {
            fetch(`${backendUrl}/teams?season_id=${selectedSeason}&league_id=${leagueId}`)
                .then(response => response.json())
                .then(data => setTeams(data))
                .catch(error => console.error('Error fetching teams:', error));
        }
    };

    const handleTeamChange = (e) => {
        const teamId = e.target.value;
        setSelectedTeam(teamId);
        setSelectedPlayer('');
        setPlayers([]);
        if (teamId) {
            fetch(`${backendUrl}/players?season_id=${selectedSeason}&team_id=${teamId}`)
                .then(response => response.json())
                .then(data => setPlayers(data))
                .catch(error => console.error('Error fetching players:', error));
        }
    };

    const handlePlayerChange = (e) => {
        setSelectedPlayer(e.target.value);
    };

    const handleSliderChange = (e) => {
        const { name, value } = e.target;
        const newValue = parseInt(value, 10);
        const otherSliders = Object.keys(kpiWeights).filter(k => k !== name);
        const total = otherSliders.reduce((acc, curr) => acc + kpiWeights[curr], 0);

        if (total + newValue > 100) {
            let remaining = 100 - newValue;
            let newWeights = { ...kpiWeights, [name]: newValue };
            let otherTotal = otherSliders.reduce((acc, curr) => acc + kpiWeights[curr], 0);

            if (otherTotal > 0) {
                otherSliders.forEach(slider => {
                    newWeights[slider] = Math.round((kpiWeights[slider] / otherTotal) * remaining);
                });
            } else {
                const remainingPerSlider = Math.floor(remaining / otherSliders.length);
                const remainder = remaining % otherSliders.length;
                otherSliders.forEach((slider, index) => {
                    newWeights[slider] = remainingPerSlider + (index < remainder ? 1 : 0);
                });
            }

            let currentTotal = Object.values(newWeights).reduce((a, b) => a + b, 0);
            if (currentTotal !== 100) {
                let diff = 100 - currentTotal;
                newWeights[otherSliders[0]] += diff;
            }
            setKpiWeights(newWeights);
        } else {
            setKpiWeights({ ...kpiWeights, [name]: newValue });
        }
    };

    const handleSearch = (e) => {
        e.preventDefault();
        setError(null);
        if (!selectedPlayer) {
            setError(t('error.select_player'));
            return;
        }

        const totalWeight = Object.values(kpiWeights).reduce((a, b) => a + b, 0);
        if (totalWeight !== 100) {
            setError(t('error.weights_sum'));
            return;
        }

        setLoading(true);
        const params = new URLSearchParams({
            player_id: selectedPlayer,
            season_id: selectedSeason,
            attacking_weight: kpiWeights.attacking,
            defending_weight: kpiWeights.defending,
            playmaking_weight: kpiWeights.playmaking,
        });

        fetch(`${backendUrl}/find_similar_players?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                setSimilarPlayers(data);
            })
            .catch(error => {
                console.error('Error fetching similar players:', error);
                setError(t('error.fetching_players'));
            })
            .finally(() => {
                setLoading(false);
            });
    };

    return (
        <div className="container scouting-container">
            <h1>{t('scouting.title')}</h1>
            <p>{t('scouting.description')}</p>
            <form onSubmit={handleSearch}>
                <div className="step-container">
                    <div className="step">
                        <h2>{t('scouting.step1.title')}</h2>
                        <div className="tooltip-container">
                            <i className="fas fa-info-circle info-icon"></i>
                            <span className="tooltip-text scouting-tooltip">{t('scouting.step1.tooltip')}</span>
                        </div>
                    </div>
                    <div className="form-group">
                        <label>{t('scouting.step1.attacking_kpi')}</label>
                        <input
                            type="range"
                            name="attacking"
                            min="0"
                            max="100"
                            value={kpiWeights.attacking}
                            onChange={handleSliderChange}
                        />
                        <span>{kpiWeights.attacking}%</span>
                    </div>
                    <div className="form-group">
                        <label>{t('scouting.step1.defending_kpi')}</label>
                        <input
                            type="range"
                            name="defending"
                            min="0"
                            max="100"
                            value={kpiWeights.defending}
                            onChange={handleSliderChange}
                        />
                        <span>{kpiWeights.defending}%</span>
                    </div>
                    <div className="form-group">
                        <label>{t('scouting.step1.playmaking_kpi')}</label>
                        <input
                            type="range"
                            name="playmaking"
                            min="0"
                            max="100"
                            value={kpiWeights.playmaking}
                            onChange={handleSliderChange}
                        />
                        <span>{kpiWeights.playmaking}%</span>
                    </div>
                </div>

                <div className="step-container">
                    <h2>{t('scouting.step2.title')}</h2>
                    <div className="form-group-row">
                        <div className="form-group">
                            <label htmlFor="season">{t('scouting.step2.season')}</label>
                            <select id="season" value={selectedSeason} onChange={handleSeasonChange}>
                                <option value="">{t('scouting.step2.select_season')}</option>
                                {seasons.map(season => (
                                    <option key={season.season_id} value={season.season_id}>{season.season_name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="league">{t('scouting.step2.league')}</label>
                            <select id="league" value={selectedLeague} onChange={handleLeagueChange} disabled={!selectedSeason}>
                                <option value="">{t('scouting.step2.select_league')}</option>
                                {leagues.map(league => (
                                    <option key={league.league_id} value={league.league_id}>{league.league_name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="team">{t('scouting.step2.team')}</label>
                            <select id="team" value={selectedTeam} onChange={handleTeamChange} disabled={!selectedLeague}>
                                <option value="">{t('scouting.step2.select_team')}</option>
                                {teams.map(team => (
                                    <option key={team.team_id} value={team.team_id}>{team.team_name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="player">{t('scouting.step2.player')}</label>
                            <select id="player" value={selectedPlayer} onChange={handlePlayerChange} disabled={!selectedTeam}>
                                <option value="">{t('scouting.step2.select_player')}</option>
                                {players.map(player => (
                                    <option key={player.player_id} value={player.player_id}>{player.player_name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <button type="submit" disabled={loading}>{loading ? t('scouting.searching') : t('scouting.search_button')}</button>
            </form>

            {error && <p className="error-message">{error}</p>}

            {loading && <div className="loader"></div>}

            {!loading && similarPlayers.length > 0 && (
                <div className="results">
                    <h3>{t('scouting.results.title')}</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>{t('scouting.results.rank')}</th>
                                <th>{t('scouting.results.player')}</th>
                                <th>{t('scouting.results.team')}</th>
                                <th>{t('scouting.results.position')}</th>
                                <th>{t('scouting.results.age')}</th>
                                <th>{t('scouting.results.similarity')}</th>
                                <th>{t('scouting.results.attacking_kpi')}</th>
                                <th>{t('scouting.results.defending_kpi')}</th>
                                <th>{t('scouting.results.playmaking_kpi')}</th>
                                <th>{t('scouting.results.potential')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {similarPlayers.map((player, index) => (
                                <tr key={index}>
                                    <td>{index + 1}</td>
                                    <td>{player.player_name}</td>
                                    <td>{player.team_name}</td>
                                    <td>{player.position}</td>
                                    <td>{player.age}</td>
                                    <td>{player.similarity_score.toFixed(2)}%</td>
                                    <td>{player.kpi_attacking.toFixed(2)}</td>
                                    <td>{player.kpi_defending.toFixed(2)}</td>
                                    <td>{player.kpi_playmaking.toFixed(2)}</td>
                                    <td>{player.potential}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default ScoutingPage;