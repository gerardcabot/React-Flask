// ScoutingPage.jsx
import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import dayjs from "dayjs";
import React from "react";

function calculatePlayerAge(dob, season) {
  if (!dob || !season) return null;
  const seasonString = String(season);
  if (!seasonString.match(/^\d{4}_\d{4}/)) {
    console.warn("Invalid season format for age calculation:", season);
    return null;
  }
  const seasonEndYear = parseInt(seasonString.split("_")[1], 10);
  if (isNaN(seasonEndYear)) return null;
  const dobDate = dayjs(dob);
  const referenceDateForAge = dayjs(`${seasonEndYear}-01-01`);
  if (!dobDate.isValid() || !referenceDateForAge.isValid()) return null;
  return referenceDateForAge.diff(dobDate, "year");
}

const InfoTooltip = ({ text }) => {
  const [show, setShow] = useState(false);
  return (
    <span
      style={{
        marginLeft: '8px',
        cursor: 'help',
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid #dc2626', // vermell
        borderRadius: '50%',
        width: '18px',
        height: '18px',
        textAlign: 'center',
        fontSize: '11px',
        color: '#dc2626', // vermell
        fontWeight: 'bold',
        userSelect: 'none',
        transition: 'background-color 0.2s, color 0.2s'
      }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
      tabIndex={0}
      role="tooltip"
      aria-haspopup="true"
      aria-describedby={show ? "tooltip-content" : undefined}
    >
      i
      {show && (
        <div
          id="tooltip-content"
          style={{
            position: 'absolute',
            bottom: '125%', // Slightly adjusted to reduce chance of clipping
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '7px',
            background: 'rgba(220,38,38,0.95)', // vermell fosc
            color: 'white',
            padding: '12px',
            borderRadius: '6px',
            zIndex: 1000,
            maxWidth: '300px', // Changed to max-width to allow shrinking on smaller screens
            minWidth: '200px', // Ensures readability for shorter texts
            fontSize: '0.9em',
            textAlign: 'left',
            boxShadow: '0 4px 10px rgba(0,0,0,0.35)',
            pointerEvents: 'none',
            whiteSpace: 'normal', // Ensure text wraps
            overflowWrap: 'break-word', // Break long words if necessary
            lineHeight: '1.4' // Improve readability
          }}
        >
          {text}
        </div>
      )}
    </span>
  );
};

function ScoutingPage() {
  const [allPlayers, setAllPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [predictionResult, setPredictionResult] = useState(null);
  const [isLoadingPrediction, setIsLoadingPrediction] = useState(false);
  const [predictionError, setPredictionError] = useState("");
  const [structuredKpiOptions, setStructuredKpiOptions] = useState([]);
  const [customModelName, setCustomModelName] = useState("");
  const [selectedPositionGroupForCustom, setSelectedPositionGroupForCustom] = useState("Attacker");
  const [selectedImpactKpisForCustom, setSelectedImpactKpisForCustom] = useState([]);
  const [selectedTargetKpisForCustom, setSelectedTargetKpisForCustom] = useState([]);
  const [useDefaultMlFeatures, setUseDefaultMlFeatures] = useState(true);
  const [availableMlFeaturesOptions, setAvailableMlFeaturesOptions] = useState([]);
  const [selectedCustomMlFeatures, setSelectedCustomMlFeatures] = useState([]);
  const [customModelBuildStatus, setCustomModelBuildStatus] = useState(null);
  const [isBuildingCustomModel, setIsBuildingCustomModel] = useState(false);
  const [modelTypeForPrediction, setModelTypeForPrediction] = useState("default_v14");
  const [availableCustomModels, setAvailableCustomModels] = useState([]);
  const [selectedCustomModelId, setSelectedCustomModelId] = useState("");
  const [mlFeatureSearchTerm, setMlFeatureSearchTerm] = useState("");
  const [kpiSearchTerm, setKpiSearchTerm] = useState("");

  useEffect(() => {
    axios.get("http://localhost:5000/players")
      .then(res => setAllPlayers(res.data || []))
      .catch(() => { setAllPlayers([]); setPredictionError("No s'ha pogut carregar la llista de jugadors."); });

    axios.get("http://localhost:5000/api/custom_model/available_kpis")
      .then(res => {
        setStructuredKpiOptions(res.data?.structured_kpis || []);
        setSelectedImpactKpisForCustom([]);
        setSelectedTargetKpisForCustom([]);
      })
      .catch(() => {
        setStructuredKpiOptions([]);
      });

    axios.get("http://localhost:5000/api/custom_model/available_ml_features")
      .then(res => {
        setAvailableMlFeaturesOptions(res.data?.available_ml_features || []);
      })
      .catch(() => {
        setAvailableMlFeaturesOptions([]);
        console.error("Failed to load available ML features.");
      });
  }, []);

  useEffect(() => {
    if (modelTypeForPrediction === 'custom') {
      setIsLoadingPrediction(true);
      axios.get("http://localhost:5000/api/custom_model/list")
        .then(res => {
          setAvailableCustomModels(res.data?.custom_models || []);
          setIsLoadingPrediction(false);
          if (res.data?.custom_models?.length > 0) {
            setSelectedCustomModelId(res.data.custom_models[0].id);
          } else {
            setSelectedCustomModelId("");
          }
        })
        .catch(() => { setAvailableCustomModels([]); setIsLoadingPrediction(false); });
    } else {
      setSelectedCustomModelId("");
    }
  }, [modelTypeForPrediction]);

  const u21EligiblePlayers = useMemo(() => {
    if (!allPlayers.length) return [];
    return allPlayers.filter(player =>
      player.dob && player.seasons?.length && player.seasons.some(s => {
        const age = calculatePlayerAge(player.dob, s);
        return age !== null && age <= 21;
      })
    ).sort((a, b) => a.name.localeCompare(b.name));
  }, [allPlayers]);

  const u21SeasonsForSelectedPlayer = useMemo(() => {
    if (!selectedPlayer?.seasons || !selectedPlayer.dob) return [];
    return selectedPlayer.seasons.filter(s => {
      const age = calculatePlayerAge(selectedPlayer.dob, s);
      return age !== null && age <= 21;
    }).sort((a, b) => a.localeCompare(b));
  }, [selectedPlayer]);

  const handlePlayerChange = (playerName) => {
    const player = u21EligiblePlayers.find(p => p.name === playerName);
    setSelectedPlayer(player || null);
    setSelectedSeason("");
    setPredictionResult(null);
    setPredictionError("");
  };

  const handleSeasonChange = (seasonValue) => {
    setSelectedSeason(seasonValue);
    setPredictionResult(null);
    setPredictionError("");
  };

  const handlePredict = () => {
    if (!selectedPlayer || !selectedSeason) {
      setPredictionError("Selecciona un jugador i una temporada sub-21.");
      return;
    }
    if (modelTypeForPrediction === 'custom' && !selectedCustomModelId) {
      setPredictionError("Seleccioneu un model personalitzat per utilitzar-lo per a la predicció o canvieu al model V14 per defecte.");
      return;
    }
    setIsLoadingPrediction(true);
    setPredictionResult(null);
    setPredictionError("");
    axios.get("http://localhost:5000/scouting_predict", {
      params: {
        player_id: selectedPlayer.player_id,
        season: selectedSeason,
        model_id: modelTypeForPrediction === 'custom' ? selectedCustomModelId : 'default_v14'
      }
    })
      .then(res => {
        setPredictionResult(res.data);
        setIsLoadingPrediction(false);
      })
      .catch(err => {
        const errorMsg = err.response?.data?.error || "No s'ha pogut obtenir la predicció.";
        console.error("Prediction error:", err.response || err);
        setPredictionError(errorMsg);
        setIsLoadingPrediction(false);
      });
  };

  const handleKpiToggle = (kpi_id, type) => {
    const setter = type === "impact" ? setSelectedImpactKpisForCustom : setSelectedTargetKpisForCustom;
    setter(prev =>
      prev.includes(kpi_id) ? prev.filter(x => x !== kpi_id) : [...prev, kpi_id]
    );
  };

  const handleMlFeatureToggle = (featureName) => {
    setSelectedCustomMlFeatures(prev =>
      prev.includes(featureName)
        ? prev.filter(f => f !== featureName)
        : [...prev, featureName]
    );
  };

  const handleBuildCustomModelSubmit = (event) => {
    event.preventDefault();
    if (!selectedPositionGroupForCustom ||
        !selectedImpactKpisForCustom.length ||
        !selectedTargetKpisForCustom.length) {
      setCustomModelBuildStatus({ success: false, message: "Seleccioneu un grup de posicions i com a mínim un KPI d'impacte i un KPI d'objectiu." });
      return;
    }
    let mlFeaturesPayload = null;
    if (!useDefaultMlFeatures) {
      if (selectedCustomMlFeatures.length > 0) {
        mlFeaturesPayload = selectedCustomMlFeatures;
      } else {
        mlFeaturesPayload = null;
      }
    }
    setIsBuildingCustomModel(true);
    setCustomModelBuildStatus(null);
    const backendPositionGroup = mapPositionGroupToBackend(selectedPositionGroupForCustom);
    axios.post("http://localhost:5000/api/custom_model/build", {
      position_group: backendPositionGroup,
      impact_kpis: selectedImpactKpisForCustom,
      target_kpis: selectedTargetKpisForCustom,
      model_name: customModelName || `custom_${selectedPositionGroupForCustom.toLowerCase()}`,
      ml_features: mlFeaturesPayload
    })
      .then(res => {
        setCustomModelBuildStatus({ success: true, message: res.data.message, id: res.data.custom_model_id });
        setIsBuildingCustomModel(false);
        if (modelTypeForPrediction === 'custom') {
          axios.get("http://localhost:5000/api/custom_model/list")
            .then(listRes => setAvailableCustomModels(listRes.data?.custom_models || []));
        }
      })
      .catch(err => {
        setCustomModelBuildStatus({ success: false, message: err.response?.data?.error || "No s'ha pogut crear el model personalitzat." });
        setIsBuildingCustomModel(false);
      });
  };

  const formatMlFeatureName = (featureName) => {
    let label = featureName;
    label = label.replace(/current_inter_/g, "Interaction: ").replace(/current_poly_/g, "Polynomial: ");
    label = label.replace(/current_/g, "Current: ");
    label = label.replace(/hist_avg_/g, "Historical Avg: ");
    label = label.replace(/hist_sum_/g, "Historical Sum: ");
    label = label.replace(/hist_max_/g, "Historical Max: ");
    label = label.replace(/hist_trend_/g, "Historical Trend: ");
    label = label.replace(/growth_ratio_/g, "Growth Ratio: ");
    label = label.replace(/growth_/g, "Growth: ");
    label = label.replace(/p90_sqrt/g, " p90 √");
    label = label.replace(/_p90/g, " p90");
    label = label.replace(/sqrt/g, " √");
    label = label.replace(/_kpi/g, " KPI");
    label = label.replace(/inv_kpi_base/g, " (Inv. Base)");
    label = label.replace(/_/g, " ");
    label = label.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    label = label.replace(/ X /g, " x ");
    if (label === "Num Hist Seasons") label = "Number Of Historical Seasons";
    return label;
  };

  const groupedAndFilteredMlFeatures = useMemo(() => {
    const searchTermLower = mlFeatureSearchTerm.toLowerCase();
    const filtered = mlFeatureSearchTerm
      ? availableMlFeaturesOptions.filter(f =>
          f.toLowerCase().includes(searchTermLower) ||
          formatMlFeatureName(f).toLowerCase().includes(searchTermLower)
        )
      : availableMlFeaturesOptions;

    return Object.entries(
      filtered.reduce((acc, feature) => {
        let groupNameKey = 'Other Contextual';
        let formattedLabel = formatMlFeatureName(feature);

        if (feature.startsWith('current_inter_') || feature.startsWith('current_poly_')) {
          groupNameKey = 'Temporada actual: Interaccions i polinomis';
        } else if (feature.startsWith('current_')) {
          groupNameKey = 'Temporada actual: Mètriques';
        } else if (feature.startsWith('hist_avg_') || feature.startsWith('hist_sum_') || feature.startsWith('hist_max_')) {
          groupNameKey = 'Rendiment històric: Agregats';
        } else if (feature.startsWith('hist_trend_')) {
          groupNameKey = 'Rendiment històric: Tendències';
        } else if (feature.startsWith('growth_')) {
          groupNameKey = 'Temporada rere temporada: creixement i ràtios';
        } else if (feature === 'num_hist_seasons') {
          groupNameKey = 'Context històric';
          formattedLabel = "Nombre de temporades històriques";
        }

        if (!acc[groupNameKey]) acc[groupNameKey] = [];
        acc[groupNameKey].push({ id: feature, label: formattedLabel });
        return acc;
      }, {})
    ).sort(([groupA], [groupB]) => {
      const order = ['Current Season: Metrics', 'Current Season: Interactions & Polynomials', 'Historical Performance: Aggregates', 'Historical Performance: Trends', 'Season-over-Season: Growth & Ratios', 'Historical Context', 'Other Contextual'];
      return order.indexOf(groupA) - order.indexOf(groupB);
    });
  }, [availableMlFeaturesOptions, mlFeatureSearchTerm]);

  const filteredStructuredKpiOptions = useMemo(() => {
    if (!kpiSearchTerm) return structuredKpiOptions;
    const searchTermLower = kpiSearchTerm.toLowerCase();
    return structuredKpiOptions
      .map(group => ({
        ...group,
        options: group.options.filter(option =>
          option.full_label.toLowerCase().includes(searchTermLower) ||
          group.metric_base_label.toLowerCase().includes(searchTermLower) ||
          option.id.toLowerCase().includes(searchTermLower)
        ),
      }))
      .filter(group => group.options.length > 0);
  }, [structuredKpiOptions, kpiSearchTerm]);

  const kpiSectionStyle = {
    border: '1px solid #e5e7eb',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '25px'
  };
  const kpiSectionTitleStyle = {
    marginTop: 0,
    color: '#dc2626', // vermell
    display: 'flex',
    alignItems: 'center',
    fontSize: '1.2rem',
    marginBottom: '8px'
  };
  const kpiSectionDescriptionStyle = {
    fontSize: '0.9em',
    color: '#4b5563',
    marginTop: '-5px',
    marginBottom: '18px'
  };
  const kpiGroupTitleStyle = {
    display: 'block',
    marginBottom: '8px',
    fontSize: '1rem',
    fontWeight: '600',
    color: '#1f2937'
  };
  const kpiOptionLabelStyle = {
    display: "inline-flex",
    alignItems: "center",
    background: "#f9fafb",
    border: '1px solid #d1d5db',
    borderRadius: "4px",
    padding: "7px 12px",
    cursor: "pointer",
    fontSize: "0.9rem",
    transition: 'background-color 0.2s, border-color 0.2s'
  };
  const kpiOptionLabelSelectedStyle = {
    ...kpiOptionLabelStyle,
    background: "#fee2e2", 
    border: '1px solid #dc2626' 
  };

  const mapPositionGroupToBackend = (uiValue) => {
    if (uiValue === "Migcampista") return "Midfielder";
    if (uiValue === "Defensor") return "Defender";
    if (uiValue === "Atacant") return "Attacker";
    return uiValue;
  };

  return (
    <div className="app-root" style={{
      minHeight: "100vh",
      width: "100vw",
      background: "#fff",
      padding: "0",
      margin: "0",
      boxSizing: "border-box",
      fontFamily: "'Inter', sans-serif",
      color: "#1f2937",
      overflowX: "hidden"
    }}>

      <section style={{
        width: "100%",
        maxWidth: "1100px",
        margin: "2rem auto",
        background: "#fff",
        padding: "2rem 2.5rem",
        borderRadius: "12px",
      }}>
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1.5rem"
        }}>
          <div style={{ flex: "1 1 300px" }}>
            <label htmlFor="player-select" style={{
              display: "block",
              marginBottom: "8px",
              fontWeight: 600,
              color: "#1f2937",
              fontSize: "1.1rem"
            }}>
              Jugador (temporades disponibles per a menors de 21 anys):
            </label>
            <select
              id="player-select"
              value={selectedPlayer ? selectedPlayer.name : ""}
              onChange={e => handlePlayerChange(e.target.value)}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #d1d5db",
                fontSize: "1rem",
                background: "#fff",
                color: "#1f2937",
                boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
              }}
            >
              <option value="">-- Selecciona jugador --</option>
              {u21EligiblePlayers.map(p => (
                <option key={p.player_id} value={p.name}>
                  {p.name} (ID: {p.player_id})
                </option>
              ))}
            </select>
          </div>
          {selectedPlayer && (
            <div style={{ flex: "1 1 300px" }}>
              <label htmlFor="season-select" style={{
                display: "block",
                marginBottom: "8px",
                fontWeight: 600,
                color: "#1f2937",
                fontSize: "1.1rem"
              }}>
                Temporada (rendiment sub-21):
              </label>
              <select
                id="season-select"
                value={selectedSeason}
                onChange={e => handleSeasonChange(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  borderRadius: "6px",
                  border: "1px solid #d1d5db",
                  fontSize: "1rem",
                  background: "#fff",
                  color: "#1f2937",
                  boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
                }}
                disabled={!selectedPlayer || u21SeasonsForSelectedPlayer.length === 0}
              >
                <option value="">-- Selecciona la temporada sub-21 --</option>
                {u21SeasonsForSelectedPlayer.map(s => (
                  <option key={s} value={s}>
                    {s} (Edat: {calculatePlayerAge(selectedPlayer.dob, s)})
                  </option>
                ))}
              </select>
              {selectedPlayer.dob && (
                <p style={{ fontSize: '0.9em', color: '#4b5563', marginTop: '5px' }}>
                  Data de naixement del jugador: {dayjs(selectedPlayer.dob).format("DD MMM YYYY")}
                </p>
              )}
            </div>
          )}
          <div style={{ flex: "1 1 300px" }}>
            <label htmlFor="model-type-select" style={{
              display: "block",
              marginBottom: "8px",
              fontWeight: 600,
              color: "#1f2937",
              fontSize: "1.1rem"
            }}>
              Model per fer la predicció:
            </label>
            <select
              id="model-type-select"
              value={modelTypeForPrediction}
              onChange={e => setModelTypeForPrediction(e.target.value)}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #d1d5db",
                fontSize: "1rem",
                background: "#fff",
                color: "#1f2937",
                boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                marginBottom: '10px'
              }}
            >
              <option value="default_v14">Model per defecte V14</option>
              <option value="custom">Model customitzat</option>
            </select>
            {modelTypeForPrediction === 'custom' && (
              <div>
                <label htmlFor="custom-model-select" style={{
                  display: "block",
                  marginBottom: "8px",
                  fontWeight: 500,
                  color: "#1f2937",
                  fontSize: '0.95em'
                }}>
                  Selecciona un model personalitzat:
                </label>
                <select
                  id="custom-model-select"
                  value={selectedCustomModelId}
                  onChange={e => setSelectedCustomModelId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: "6px",
                    border: "1px solid #d1d5db",
                    fontSize: "1rem",
                    background: "#fff",
                    color: "#1f2937",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
                  }}
                  disabled={availableCustomModels.length === 0}
                >
                  <option value="">
                    -- {availableCustomModels.length === 0 ? 'No hi ha models personalitzats disponibles' : 'Seleccioneu un model personalitzat'} --
                  </option>
                  {availableCustomModels.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} (Pos: {model.position_group})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        <button
          onClick={handlePredict}
          disabled={!selectedPlayer || !selectedSeason || isLoadingPrediction || (modelTypeForPrediction === 'custom' && !selectedCustomModelId)}
          style={{
            width: "100%",
            padding: "12px",
            background: (!selectedPlayer || !selectedSeason || isLoadingPrediction || (modelTypeForPrediction === 'custom' && !selectedCustomModelId)) ? "#fca5a5" : "#dc2626", // vermell clar/desactivat
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            fontSize: "1.1rem",
            fontWeight: 600,
            cursor: (!selectedPlayer || !selectedSeason || isLoadingPrediction || (modelTypeForPrediction === 'custom' && !selectedCustomModelId)) ? "not-allowed" : "pointer",
            marginTop: "20px",
            transition: "background-color 0.2s"
          }}
          onMouseOver={e => {
            if (!(!selectedPlayer || !selectedSeason || isLoadingPrediction || (modelTypeForPrediction === 'custom' && !selectedCustomModelId))) {
              e.currentTarget.style.backgroundColor = '#b91c1c'; 
            }
          }}
          onMouseOut={e => {
            if (!(!selectedPlayer || !selectedSeason || isLoadingPrediction || (modelTypeForPrediction === 'custom' && !selectedCustomModelId))) {
              e.currentTarget.style.backgroundColor = '#dc2626'; 
            }
          }}
        >
          {isLoadingPrediction ? "Calculant..." : "Predir puntuació de potencial"}
        </button>
        {isLoadingPrediction && (
          <p style={{ textAlign: 'center', marginTop: '15px', color: '#dc2626' }}>
              S'està carregant el model i s'està fent predicció...
          </p>
        )}
        {predictionError && (
          <div style={{
            marginTop: "20px",
            background: "#fef2f2",
            color: "#dc2626",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #f5c6cb",
            textAlign: "center"
          }}>
            <strong>Error:</strong> {predictionError}
          </div>
        )}
        {predictionResult && !predictionError && (
          <div style={{
            marginTop: "28px",
            background: "#fee2e2", 
            padding: "18px",
            borderRadius: "12px",
            border: "1px solid #fca5a5", 
          }}>
            <h3 style={{
              marginTop: 0,
              marginBottom: '10px',
              color: '#b91c1c', 
              fontWeight: 700,
              fontSize: "1.18rem"
            }}>
              Resultat de la predicció ({predictionResult.model_used === 'default_v14' ? 'Default V14 Model' : `Custom Model: ${predictionResult.model_used}`}):
            </h3>
            <p style={{ margin: "8px 0" }}><strong>Jugador:</strong> {predictionResult.player_name} (ID: {predictionResult.player_id})</p>
            <p style={{ margin: "8px 0" }}><strong>Temporada avaluada:</strong> {predictionResult.season_predicted_from}</p>
            <p style={{ margin: "8px 0" }}><strong>Edat avaluada:</strong> {predictionResult.age_at_season_start_of_year} </p>
            <p style={{ margin: "8px 0" }}><strong>Posició:</strong> {predictionResult.position_group}</p>
            <p style={{ margin: "8px 0" }}><strong>90s Jugats a la temporada:</strong> {predictionResult.num_90s_played_in_season}</p>
            <p style={{
              fontSize: '1.2em',
              fontWeight: 'bold',
              color: '#b91c1c', 
              margin: "18px 0 0 0"
            }}>
              Predicted U21 Potential Score: <span style={{ fontSize: '1.3em' }}>{predictionResult.predicted_potential_score} / 200</span>
            </p>
          </div>
        )}
      </section>

      <section style={{
        width: "100%",
        maxWidth: "1100px",
        margin: "2rem auto",
        background: "#fff",
        padding: "2rem 2.5rem",
        borderRadius: "12px",
      }}>
        <h2 style={{
          fontSize: "1.6rem",
          marginBottom: "25px",
          color: "#1f2937",
          borderBottom: "2px solid #dc2626", 
          paddingBottom: "10px"
        }}>
          Construeix un model de potencial personalitzat
        </h2>
        <div style={{
          display: 'flex',
          flexDirection: 'row',
          gap: '30px',
          flexWrap: 'wrap'
        }}>
          <div style={{ flex: '2', minWidth: 'clamp(350px, 60%, 700px)' }}>
            {structuredKpiOptions.length === 0 ? (
              <p style={{ color: "#4b5563" }}>S'estan carregant les opcions d'indicador clau de rendiment (KPI) per a la creació de models personalitzats...</p>
            ) : (
              <form onSubmit={handleBuildCustomModelSubmit}>
                <div style={{ marginBottom: '20px' }}>
                  <label htmlFor="custom-model-name" style={{
                    display: "block",
                    marginBottom: "5px",
                    fontWeight: 600,
                    color: "#1f2937",
                    fontSize: "1.1rem"
                  }}>
                    Nom del model personalitzat:
                  </label>
                  <input
                    type="text"
                    id="custom-model-name"
                    value={customModelName}
                    onChange={e => setCustomModelName(e.target.value)}
                    placeholder="p. ex., Atacant_Alt_xG"
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: "6px",
                      border: "1px solid #d1d5db",
                      fontSize: "1rem",
                      background: "#fff",
                      color: "#1f2937",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
                    }}
                  />
                </div>
                <div style={{ marginBottom: '25px' }}>
                  <label htmlFor="custom-model-pos-group" style={{
                    display: "block",
                    marginBottom: "5px",
                    fontWeight: 600,
                    color: "#1f2937",
                    fontSize: "1.1rem"
                  }}>
                    Grup de posició per al model:
                  </label>
                  <select
                    id="custom-model-pos-group"
                    value={selectedPositionGroupForCustom}
                    onChange={e => {
                      setSelectedPositionGroupForCustom(e.target.value);
                      setSelectedImpactKpisForCustom([]);
                      setSelectedTargetKpisForCustom([]);
                    }}
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: "6px",
                      border: "1px solid #d1d5db",
                      fontSize: "1rem",
                      background: "#fff",
                      color: "#1f2937",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
                    }}
                  >
                    {["Atacant", "Migcampista", "Defensor"].map(group => (
                      <option key={group} value={group}>{group}</option>
                    ))}
                  </select>
                </div>
                <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '15px', marginBottom: '20px' }}>
                  <div style={kpiSectionStyle}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <h4 style={{ ...kpiSectionTitleStyle, marginBottom: '0' }}>
                        Pas 1: Definir l'impacte del jugador
                        <InfoTooltip text="Seleccioneu els KPI que creieu que representen un impacte positiu general del jugador per a la posició escollida. 
                        Aquests formaran una puntuació composta. Els KPI de definició d'objectius 
                        (Pas 2) es ponderaran en funció de la seva correlació amb aquesta puntuació d'impacte composta." />
                      </h4>
                      <input
                        type="text"
                        placeholder="Busca KPIs d'impacte..."
                        value={kpiSearchTerm}
                        onChange={e => setKpiSearchTerm(e.target.value)}
                        style={{
                          padding: '6px 8px',
                          borderRadius: '4px',
                          border: '1px solid #d1d5db',
                          fontSize: '0.9em',
                          background: "#fff",
                          color: "#1f2937"
                        }}
                      />
                    </div>
                    <p style={kpiSectionDescriptionStyle}>
                      Trieu les mètriques que reflecteixin millor el rendiment impactant.
                    </p>
                    {filteredStructuredKpiOptions.map(metricGroup => (
                      <div key={`impact-group-${metricGroup.metric_base_id}`} style={{ marginBottom: '15px' }}>
                        <strong style={kpiGroupTitleStyle}>{metricGroup.metric_base_label}</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                          {metricGroup.options.map(option => (
                            <label
                              key={`impact-${option.id}`}
                              title={option.full_label}
                              style={selectedImpactKpisForCustom.includes(option.id) ? kpiOptionLabelSelectedStyle : kpiOptionLabelStyle}
                            >
                              <input
                                type="checkbox"
                                checked={selectedImpactKpisForCustom.includes(option.id)}
                                onChange={() => handleKpiToggle(option.id, "impact")}
                                style={{ marginRight: "6px" }}
                              />
                              {option.label_variant || option.full_label.replace(metricGroup.metric_base_label, "").trim().replace(/^\(|\)$/g, "") || "Total/Count"}
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                    {filteredStructuredKpiOptions.length === 0 && kpiSearchTerm && <p style={{ color: '#4b5563' }}>No hi ha cap KPI d'impacte que coincideixi amb la teva cerca.</p>}
                  </div>
                  <div style={kpiSectionStyle}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <h4 style={{ ...kpiSectionTitleStyle, marginBottom: '0' }}>
                        Pas 2: Definir l'heurística potencial
                        <InfoTooltip text="Seleccioneu els KPI que formaran directament la puntuació potencial. 
                        El model aprendrà a predir aquesta puntuació. 
                        La importància de cada KPI aquí es determina automàticament per la seva correlació amb els KPI d'impacte que heu triat al pas 1. "/>
                      </h4>
                    </div>
                    <p style={kpiSectionDescriptionStyle}>
                      Aquestes mètriques defineixen què significa "potencial" per a aquest model personalitzat.
                    </p>
                    {filteredStructuredKpiOptions.map(metricGroup => (
                      <div key={`target-group-${metricGroup.metric_base_id}`} style={{ marginBottom: '15px' }}>
                        <strong style={kpiGroupTitleStyle}>{metricGroup.metric_base_label}</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                          {metricGroup.options.map(option => (
                            <label
                              key={`target-${option.id}`}
                              title={option.full_label}
                              style={selectedTargetKpisForCustom.includes(option.id) ? kpiOptionLabelSelectedStyle : kpiOptionLabelStyle}
                            >
                              <input
                                type="checkbox"
                                checked={selectedTargetKpisForCustom.includes(option.id)}
                                onChange={() => handleKpiToggle(option.id, "target")}
                                style={{ marginRight: "6px" }}
                              />
                              {option.label_variant || option.full_label.replace(metricGroup.metric_base_label, "").trim().replace(/^\(|\)$/g, "") || "Total/Count"}
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                    {filteredStructuredKpiOptions.length === 0 && kpiSearchTerm && <p style={{ color: '#4b5563' }}>No hi ha cap KPI de definició d'objectiu que coincideixi amb la cerca.</p>}
                  </div>
                </div>
                <div style={{ ...kpiSectionStyle, marginTop: '5px' }}>
                  <h4 style={{ ...kpiSectionTitleStyle, display: 'flex', alignItems: 'center' }}>
                    Pas 3 (opcional): Avançat: selecció de funcions d'aprenentatge automàtic
                    <InfoTooltip text="Seleccioneu manualment les característiques d'entrada específiques per al model XGBoost. 
                    Això proporciona un control precís. Si l'opció 'Utilitza l'opció per defecte...' està marcada, 
                    les característiques es seleccionaran automàticament en funció dels KPI de definició d'objectiu (Pas 2), 
                    amb l'objectiu de ser rellevants. Per a la majoria d'usuaris, es recomana l'opció per defecte." />
                  </h4>
                  <p style={kpiSectionDescriptionStyle}>
                    El model utilitza aquestes característiques per aprendre.</p>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', userSelect: 'none' }}>
                      <input
                        type="checkbox"
                        checked={useDefaultMlFeatures}
                        onChange={(e) => {
                          setUseDefaultMlFeatures(e.target.checked);
                          if (e.target.checked) {
                            setSelectedCustomMlFeatures([]);
                          }
                        }}
                        style={{ marginRight: '8px', transform: 'scale(1.1)' }}
                      />
                      Utilitza la lògica de selecció de funcions d'aprenentatge automàtic predeterminada
                    </label>
                    <p style={{ fontSize: '0.8em', color: '#4b5563', margin: '5px 0 0 25px' }}>
                      Les característiques rellevants es seleccionaran automàticament. Desmarqueu la casella per a la selecció manual.
                    </p>
                  </div>
                  {!useDefaultMlFeatures && (
                    <div style={{ marginBottom: '15px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <strong style={{ display: "block", fontSize: '0.95rem', color: '#1f2937' }}>
                          Seleccioneu les funcions d'aprenentatge automàtic personalitzades:
                        </strong>
                        <input
                          type="text"
                          placeholder="Cerca característiques de ML..."
                          value={mlFeatureSearchTerm}
                          onChange={e => setMlFeatureSearchTerm(e.target.value)}
                          style={{
                            padding: '8px 10px',
                            borderRadius: '4px',
                            border: '1px solid #d1d5db',
                            fontSize: '0.9em',
                            width: '250px',
                            background: "#fff",
                            color: "#1f2937"
                          }}
                        />
                      </div>
                      {availableMlFeaturesOptions.length > 0 ? (
                        <div style={{
                          maxHeight: '400px',
                          overflowY: 'auto',
                          border: '1px solid #d1d5db',
                          padding: '15px',
                          borderRadius: '4px',
                          background: '#f9fafb'
                        }}>
                          {groupedAndFilteredMlFeatures.length > 0 ? groupedAndFilteredMlFeatures.map(([groupName, features]) => (
                            <div key={groupName} style={{ marginBottom: '18px' }}>
                              <h5 style={{
                                margin: '0 0 10px 0',
                                color: '#1f2937',
                                fontSize: '1.05rem',
                                borderBottom: '1px solid #e5e7eb',
                                paddingBottom: '5px',
                                fontWeight: '600'
                              }}>
                                {groupName}
                              </h5>
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                                {features.sort((a, b) => a.label.localeCompare(b.label)).map(feature => (
                                  <label
                                    key={feature.id}
                                    title={feature.id}
                                    style={selectedCustomMlFeatures.includes(feature.id) ? kpiOptionLabelSelectedStyle : kpiOptionLabelStyle}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={selectedCustomMlFeatures.includes(feature.id)}
                                      onChange={() => handleMlFeatureToggle(feature.id)}
                                      style={{ marginRight: "6px" }}
                                    />
                                    {feature.label.length > 45 ? `${feature.label.substring(0, 42)}...` : feature.label}
                                  </label>
                                ))}
                              </div>
                            </div>
                          )) : <p style={{ color: '#4b5563', textAlign: 'center', padding: '10px 0' }}>No hi ha cap funció d'aprenentatge automàtic que coincideixi amb la teva cerca.</p>}
                        </div>
                      ) : (
                        <p style={{ color: '#4b5563' }}>S'estan carregant les funcions d'aprenentatge automàtic disponibles o no s'ha trobat cap des del backend...</p>
                      )}
                      <p style={{ fontSize: '0.8em', color: '#4b5563', marginTop: '10px' }}>
                        El model utilitzarà aquestes característiques seleccionades. Si no se'n tria cap (i l'opció "Utilitza per defecte" està desactivada), s'aplica la lògica per defecte.
                      </p>
                      <div style={{ marginTop: '15px', fontSize: '0.9em', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span>Característiques de ML seleccionades: <strong>{selectedCustomMlFeatures.length}</strong></span>
                        {selectedCustomMlFeatures.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setSelectedCustomMlFeatures([])}
                            style={{
                              padding: '5px 10px',
                              fontSize: '0.85em',
                              background: '#6b7280',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                          >
                            Esborra la selecció
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={isBuildingCustomModel || !selectedPositionGroupForCustom || !selectedImpactKpisForCustom.length || !selectedTargetKpisForCustom.length}
                  style={{
                    background: isBuildingCustomModel || !selectedPositionGroupForCustom || !selectedImpactKpisForCustom.length || !selectedTargetKpisForCustom.length ? "#fca5a5" : "#dc2626", // vermell clar/desactivat
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    padding: "12px 20px",
                    fontWeight: 600,
                    cursor: isBuildingCustomModel || !selectedPositionGroupForCustom || !selectedImpactKpisForCustom.length || !selectedTargetKpisForCustom.length ? "not-allowed" : "pointer",
                    fontSize: "1.1rem",
                    width: "100%",
                    marginTop: "20px"
                  }}
                >
                  {isBuildingCustomModel ? "Construint el model..." : "Crea un model personalitzat"}
                </button>
              </form>
            )}
            {customModelBuildStatus && (
              <div style={{
                marginTop: "16px",
                padding: "10px",
                borderRadius: "8px",
                border: `1px solid ${customModelBuildStatus.success ? '#c5e0b4' : '#f5c6cb'}`,
                background: customModelBuildStatus.success ? '#e2f0d9' : '#fef2f2',
                color: customModelBuildStatus.success ? '#385723' : '#dc2626'
              }}>
                <strong>{customModelBuildStatus.success ? "Success!" : "Error:"}</strong> {customModelBuildStatus.message}
                {customModelBuildStatus.id && <p>Model ID: <span style={{ fontFamily: "monospace" }}>{customModelBuildStatus.id}</span></p>}
              </div>
            )}
          </div>
          <div style={{
            flex: '1',
            minWidth: '300px',
            background: '#f9fafb',
            padding: '25px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            alignSelf: 'flex-start'
          }}>
            <div style={{ marginBottom: '25px' }}>
              <h4 style={{
                marginTop: 0,
                color: '#1f2937',
                display: 'flex',
                alignItems: 'center',
                fontSize: '1.2rem',
                marginBottom: '10px'
              }}>
                Comprensió de les variants de KPI
                <InfoTooltip text="La mateixa mètrica base (per exemple, els gols) es pot representar de maneres diferents, cadascuna de les quals proporciona una perspectiva única sobre el rendiment del jugador." /></h4>
              <ul style={{ fontSize: '0.95em', listStyleType: 'disc', paddingLeft: '20px', color: '#4b5563' }}>
                <li style={{ marginBottom: '10px' }}><strong>Total / Recompte:</strong> Suma o recompte brut al llarg de la temporada. Reflecteix el volum global.</li>
                <li style={{ marginBottom: '10px' }}><strong>Per 90 Min (P90):</strong> Mètrica normalitzada per 90 minuts. Crucial per a la comparació basada en els minuts jugats.</li>
                <li style={{ marginBottom: '10px' }}><strong>P90 Sqrt (P90 √):</strong> Arrel quadrada del valor P90. Estabilitza la variància per a mètriques asimètriques i redueix l'impacte dels valors atípics.</li>
                <li style={{ marginBottom: '10px' }}><strong>KPI directe:</strong> Taxes o percentatges precalculats.</li>
                <li style={{ marginBottom: '10px' }}><strong>Invertit (Inv):</strong> Per a mètriques on com més baix és millor (per exemple, pèrdues), les puntuacions invertides més altes signifiquen un millor rendiment.</li>
              </ul>
            </div>
            <div>
              <h4 style={{
                marginTop: 0,
                color: '#1f2937',
                display: 'flex',
                alignItems: 'center',
                fontSize: '1.2rem',
                marginBottom: '10px'
              }}>
                Com afecta la selecció de funcions de ML al model
                <InfoTooltip text="Les característiques d'aprenentatge automàtic són les entrades directes que utilitza el model. Les vostres eleccions aquí influeixen significativament en el que aprèn el model." />
              </h4>
              <ul style={{ fontSize: '0.95em', listStyleType: 'disc', paddingLeft: '20px', color: '#4b5563' }}>
                <li style={{ marginBottom: '10px' }}><strong>Relevance is Key:</strong> Seleccioneu característiques que siguin realment predictives del vostre potencial definit. Les característiques irrellevants afegeixen soroll.</li>
                <li style={{ marginBottom: '10px' }}><strong>Model Complexity:</strong> Més característiques poden crear models complexos que podrien sobreajustar-se (aprendre soroll, no patrons generals).</li>
                <li style={{ marginBottom: '10px' }}><strong>Feature Types:</strong>
                  <ul style={{ paddingLeft: '20px', listStyleType: 'circle', marginTop: '5px' }}>
                    <li><em>Temporada actual</em> les característiques mostren la forma recent.</li>
                    <li><em>Agregats històrics</em> (Mitjana, Suma, Màx.) donen una línia de base de rendiment.</li>
                    <li><em>Creixement i tendències</em> indiquen desenvolupament.</li>
                  </ul>
                </li>
                <li style={{ marginBottom: '10px' }}><strong>Interaccions/Polinomis:</strong> Captura relacions no lineals.</li>
                <li style={{ marginBottom: '10px' }}><strong>Lògica per defecte:</strong> Si l'opció "Utilitza l'opció per defecte..." està marcada, el sistema selecciona les característiques relacionades amb els KPI de definició d'objectiu.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default ScoutingPage;