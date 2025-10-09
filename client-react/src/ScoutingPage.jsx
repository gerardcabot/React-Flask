// ScoutingPage.jsx
import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import dayjs from "dayjs";
import React from "react";
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const ADMIN_SECRET = import.meta.env.VITE_ADMIN_SECRET || ''; // Optional: for viewing GitHub workflow URLs

// Helper functions for tracking user's own models
const MY_MODELS_KEY = 'my_custom_models';

const getMyModels = () => {
  try {
    const stored = localStorage.getItem(MY_MODELS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const addMyModel = (modelId) => {
  try {
    const myModels = getMyModels();
    if (!myModels.includes(modelId)) {
      myModels.push(modelId);
      localStorage.setItem(MY_MODELS_KEY, JSON.stringify(myModels));
    }
  } catch (error) {
    console.error('Error saving model to localStorage:', error);
  }
};

const isMyModel = (modelId) => {
  const myModels = getMyModels();
  return myModels.includes(modelId);
};


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
        border: '1px solid #dc2626', 
        borderRadius: '50%',
        width: '18px',
        height: '18px',
        textAlign: 'center',
        fontSize: '11px',
        color: '#dc2626', 
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
            bottom: '125%', 
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '7px',
            background: 'rgba(220,38,38,0.95)', 
            color: 'white',
            padding: '12px',
            borderRadius: '6px',
            zIndex: 1000,
            maxWidth: '300px', 
            minWidth: '200px', 
            fontSize: '0.9em',
            textAlign: 'left',
            boxShadow: '0 4px 10px rgba(0,0,0,0.35)',
            pointerEvents: 'none',
            whiteSpace: 'normal', 
            overflowWrap: 'break-word', 
            lineHeight: '1.4' 
          }}
        >
          {text}
        </div>
      )}
    </span>
  );
};

function ScoutingPage() {
  const { t } = useTranslation();
  
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
  const [v14ModelConfig, setV14ModelConfig] = useState(null);
  const [showV14Info, setShowV14Info] = useState(false);

  useEffect(() => {
    // axios.get("http://localhost:5000/players")
    axios.get(`${API_URL}/players`)
      .then(res => setAllPlayers(res.data || []))
      .catch(() => { setAllPlayers([]); setPredictionError(t('scouting.errors.playersLoadFailed')); });

    // axios.get("http://localhost:5000/api/custom_model/available_kpis")
    axios.get(`${API_URL}/api/custom_model/available_kpis`)
      .then(res => {
        setStructuredKpiOptions(res.data?.structured_kpis || []);
        setSelectedImpactKpisForCustom([]);
        setSelectedTargetKpisForCustom([]);
      })
      .catch(() => {
        setStructuredKpiOptions([]);
      });

    // axios.get("http://localhost:5000/api/custom_model/available_ml_features")
    axios.get(`${API_URL}/api/custom_model/available_ml_features`)
      .then(res => {
        setAvailableMlFeaturesOptions(res.data?.available_ml_features || []);
      })
      .catch(() => {
        setAvailableMlFeaturesOptions([]);
        console.error("Failed to load available ML features.");
      });

    // Load V14 model configuration
    axios.get(`${API_URL}/api/model/default_v14_config`)
      .then(res => {
        setV14ModelConfig(res.data);
      })
      .catch(() => {
        console.error("Failed to load V14 model configuration.");
      });
  }, []);

  useEffect(() => {
    if (modelTypeForPrediction === 'custom') {
      setIsLoadingPrediction(true);
      // axios.get("http://localhost:5000/api/custom_model/list")
      axios.get(`${API_URL}/api/custom_model/list`)
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
      toast.error(t('scouting.errors.selectPlayerSeason'));
      return;
    }
    if (modelTypeForPrediction === 'custom' && !selectedCustomModelId) {
      toast.error(t('scouting.errors.modelLoadFailed'));
      return;
    }
    setIsLoadingPrediction(true);
    setPredictionResult(null);
    setPredictionError("");
    
    toast.promise(
    axios.get(`${API_URL}/scouting_predict`, {
      params: {
        player_id: selectedPlayer.player_id,
        season: selectedSeason,
        model_id: modelTypeForPrediction === 'custom' ? selectedCustomModelId : 'default_v14'
      }
      }),
      {
        loading: t('scouting.predicting'),
        success: (res) => {
        setPredictionResult(res.data);
          return `${t('scouting.result.score')}: ${res.data.predicted_potential_score}/200`;
        },
        error: (err) => {
          const errorMsg = err.response?.data?.error || t('scouting.errors.predictionFailed');
        setPredictionError(errorMsg);
          return errorMsg;
        },
      }
    ).finally(() => {
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
      toast.error(t('scouting.customModelBuilder.errorValidation'));
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
    
    // Prepare headers (add admin secret if available for workflow URL access)
    const headers = {};
    if (ADMIN_SECRET) {
      headers['X-Admin-Secret'] = ADMIN_SECRET;
    }
    
    // Use GitHub Actions endpoint to avoid timeout issues on Render free tier
    toast.promise(
      axios.post(`${API_URL}/api/custom_model/trigger_github_training`, {
      position_group: backendPositionGroup,
      impact_kpis: selectedImpactKpisForCustom,
      target_kpis: selectedTargetKpisForCustom,
      model_name: customModelName || `custom_${selectedPositionGroupForCustom.toLowerCase()}`,
      ml_features: mlFeaturesPayload
      }, { headers }),
      {
        loading: t('scouting.customModelBuilder.starting'),
        success: (res) => {
          const workflowUrl = res.data.workflow_url;
          const estimatedTime = res.data.estimated_time;
          const modelId = res.data.custom_model_id;
          
          // Save model ID to localStorage as "my model"
          addMyModel(modelId);
          
          // Prepare additional info for display
          let additionalInfo = `${t('scouting.customModelBuilder.estimatedTimeMessage', { time: estimatedTime })}`;
          if (workflowUrl) {
            additionalInfo += ` ${t('scouting.customModelBuilder.monitorGitHub')}`;
          } else {
            additionalInfo += ` ${t('scouting.customModelBuilder.willAppear')}`;
          }
          
          setCustomModelBuildStatus({ 
            success: true, 
            message: res.data.message,
            id: modelId,
            workflowUrl: workflowUrl,
            additionalInfo: additionalInfo
          });
          
          return `${t('scouting.customModelBuilder.successTitle')} ${additionalInfo}`;
        },
        error: (err) => {
          const errorMsg = err.response?.data?.error || t('scouting.customModelBuilder.errorBuildFailed');
          const manualUrl = err.response?.data?.manual_url;
          
          setCustomModelBuildStatus({ 
            success: false, 
            message: errorMsg,
            manualUrl: manualUrl
          });
          
          return errorMsg;
        },
      }
    ).finally(() => {
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
          groupNameKey = t('scouting.mlFeatureGroups.currentInteractions');
        } else if (feature.startsWith('current_')) {
          groupNameKey = t('scouting.mlFeatureGroups.currentMetrics');
        } else if (feature.startsWith('hist_avg_') || feature.startsWith('hist_sum_') || feature.startsWith('hist_max_')) {
          groupNameKey = t('scouting.mlFeatureGroups.historicalAggregates');
        } else if (feature.startsWith('hist_trend_')) {
          groupNameKey = t('scouting.mlFeatureGroups.historicalTrends');
        } else if (feature.startsWith('growth_')) {
          groupNameKey = t('scouting.mlFeatureGroups.growthRatios');
        } else if (feature === 'num_hist_seasons') {
          groupNameKey = t('scouting.mlFeatureGroups.historicalContext');
          formattedLabel = t('scouting.mlFeatureGroups.numHistSeasons');
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
              {t('scouting.selectPlayer')}
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
              <option value="">-- {t('scouting.selectPlayer')} --</option>
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
                {t('scouting.selectSeason')}
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
                <option value="">-- {t('scouting.selectSeason')} --</option>
                {u21SeasonsForSelectedPlayer.map(s => (
                  <option key={s} value={s}>
                    {s} ({t('scouting.age')}: {calculatePlayerAge(selectedPlayer.dob, s)})
                  </option>
                ))}
              </select>
              {selectedPlayer.dob && (
                <p style={{ fontSize: '0.9em', color: '#4b5563', marginTop: '5px' }}>
                  {t('scouting.playerDob')}: {dayjs(selectedPlayer.dob).format("DD MMM YYYY")}
                </p>
              )}
            </div>
          )}
          <div style={{ flex: "1 1 300px" }}>
            <label htmlFor="model-type-select" style={{
              display: "flex",
              alignItems: "center",
              marginBottom: "8px",
              fontWeight: 600,
              color: "#1f2937",
              fontSize: "1.1rem"
            }}>
              {t('scouting.selectModel')}
              {modelTypeForPrediction === 'default_v14' && v14ModelConfig && (
                <button
                  onClick={() => setShowV14Info(true)}
                  style={{
                    marginLeft: '10px',
                    cursor: 'pointer',
                    border: '1.5px solid #dc2626',
                    borderRadius: '50%',
                    width: '22px',
                    height: '22px',
                    background: 'white',
                    color: '#dc2626',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                    padding: 0
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = '#dc2626';
                    e.target.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'white';
                    e.target.style.color = '#dc2626';
                  }}
                  title={t('scouting.modelConfigButton')}
                >
                  i
                </button>
              )}
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
              <option value="default_v14">{t('scouting.defaultModel')}</option>
              <option value="custom">{t('scouting.customModel.title')}</option>
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
                  {t('scouting.customModel.selectCustomModel')}:
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
                    -- {availableCustomModels.length === 0 ? t('scouting.customModel.noModelsAvailable') : t('scouting.customModel.selectModelOption')} --
                  </option>
                  {availableCustomModels.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} (Pos: {model.position_group}) {isMyModel(model.id) ? t('scouting.customModel.yourModel') : t('scouting.customModel.communityModel')}
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
          {isLoadingPrediction ? t('scouting.predicting') : t('scouting.predict')}
        </button>
        {isLoadingPrediction && (
          <p style={{ textAlign: 'center', marginTop: '15px', color: '#dc2626' }}>
              {t('scouting.loadingModel')}
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
              {t('scouting.result.title')} ({predictionResult.model_used === 'default_v14' ? t('scouting.defaultModel') : `${t('scouting.customModel.title')}: ${predictionResult.model_used}`}):
            </h3>
            <p style={{ margin: "8px 0" }}><strong>{t('scouting.result.player')}:</strong> {predictionResult.player_name} (ID: {predictionResult.player_id})</p>
            <p style={{ margin: "8px 0" }}><strong>{t('scouting.result.season')}:</strong> {predictionResult.season_predicted_from}</p>
            <p style={{ margin: "8px 0" }}><strong>{t('scouting.result.age')}:</strong> {predictionResult.age_at_season_start_of_year} </p>
            <p style={{ margin: "8px 0" }}><strong>{t('scouting.result.position')}:</strong> {predictionResult.position_group}</p>
            <p style={{ margin: "8px 0" }}><strong>{t('scouting.result.nineties')}:</strong> {predictionResult.num_90s_played_in_season}</p>
            <p style={{
              fontSize: '1.2em',
              fontWeight: 'bold',
              color: '#b91c1c', 
              margin: "18px 0 0 0"
            }}>
              {t('scouting.result.potentialScore')}: <span style={{ fontSize: '1.3em' }}>{predictionResult.predicted_potential_score} / 200</span>
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
          {t('scouting.customModel.title')}
        </h2>
        <div style={{
          display: 'flex',
          flexDirection: 'row',
          gap: '30px',
          flexWrap: 'wrap'
        }}>
          <div style={{ flex: '2', minWidth: 'clamp(350px, 60%, 700px)' }}>
            {structuredKpiOptions.length === 0 ? (
              <p style={{ color: "#4b5563" }}>{t('scouting.customModelBuilder.loadingKpis')}</p>
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
                    {t('scouting.customModelBuilder.modelName')}:
                  </label>
                  <input
                    type="text"
                    id="custom-model-name"
                    value={customModelName}
                    onChange={e => setCustomModelName(e.target.value)}
                    placeholder={t('scouting.customModelBuilder.modelNamePlaceholder')}
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
                    {t('scouting.customModelBuilder.positionGroup')}:
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
                      <option key={group} value={group}>
                        {group === "Atacant" ? t('scouting.customModelBuilder.attacker') : 
                         group === "Migcampista" ? t('scouting.customModelBuilder.midfielder') : 
                         t('scouting.customModelBuilder.defender')}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '15px', marginBottom: '20px' }}>
                  <div style={kpiSectionStyle}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <h4 style={{ ...kpiSectionTitleStyle, marginBottom: '0' }}>
                        {t('scouting.customModelBuilder.step1Title')}
                        <InfoTooltip text={t('scouting.customModelBuilder.step1Tooltip')} />
                      </h4>
                      <input
                        type="text"
                        placeholder={t('scouting.customModelBuilder.search')}
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
                      {t('scouting.customModelBuilder.step1Description')}
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
                    {filteredStructuredKpiOptions.length === 0 && kpiSearchTerm && <p style={{ color: '#4b5563' }}>{t('scouting.customModelBuilder.noImpactKpis')}</p>}
                  </div>
                  <div style={kpiSectionStyle}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <h4 style={{ ...kpiSectionTitleStyle, marginBottom: '0' }}>
                        {t('scouting.customModelBuilder.step2Title')}
                        <InfoTooltip text={t('scouting.customModelBuilder.step2Tooltip')} />
                      </h4>
                    </div>
                    <p style={kpiSectionDescriptionStyle}>
                      {t('scouting.customModelBuilder.step2Description')}
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
                    {filteredStructuredKpiOptions.length === 0 && kpiSearchTerm && <p style={{ color: '#4b5563' }}>{t('scouting.customModelBuilder.noTargetKpis')}</p>}
                  </div>
                </div>
                <div style={{ ...kpiSectionStyle, marginTop: '5px' }}>
                  <h4 style={{ ...kpiSectionTitleStyle, display: 'flex', alignItems: 'center' }}>
                    {t('scouting.customModelBuilder.step3Title')}
                    <InfoTooltip text={t('scouting.customModelBuilder.step3Tooltip')} />
                  </h4>
                  <p style={kpiSectionDescriptionStyle}>
                    {t('scouting.customModelBuilder.step3Description')}</p>
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
                      {t('scouting.customModelBuilder.useDefaultMlFeatures')}
                    </label>
                    <p style={{ fontSize: '0.8em', color: '#4b5563', margin: '5px 0 0 25px' }}>
                      {t('scouting.customModelBuilder.defaultFeaturesNote')}
                    </p>
                  </div>
                  {!useDefaultMlFeatures && (
                    <div style={{ marginBottom: '15px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <strong style={{ display: "block", fontSize: '0.95rem', color: '#1f2937' }}>
                          {t('scouting.customModelBuilder.selectCustomFeatures')}
                        </strong>
                        <input
                          type="text"
                          placeholder={t('scouting.customModelBuilder.searchMlFeatures')}
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
                          )) : <p style={{ color: '#4b5563', textAlign: 'center', padding: '10px 0' }}>{t('scouting.customModelBuilder.noMlFeatures')}</p>}
                        </div>
                      ) : (
                        <p style={{ color: '#4b5563' }}>{t('scouting.customModelBuilder.loadingMlFeatures')}</p>
                      )}
                      <p style={{ fontSize: '0.8em', color: '#4b5563', marginTop: '10px' }}>
                        {t('scouting.customModelBuilder.mlFeaturesNote')}
                      </p>
                      <div style={{ marginTop: '15px', fontSize: '0.9em', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span>{t('scouting.customModelBuilder.selectedFeatures')} <strong>{selectedCustomMlFeatures.length}</strong></span>
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
                            {t('scouting.customModelBuilder.clearSelection')}
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
                  {isBuildingCustomModel ? t('scouting.customModelBuilder.building') : t('scouting.customModelBuilder.buildModel')}
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
                <strong>{customModelBuildStatus.success ? t('scouting.customModelBuilder.successTitle') : "Error:"}</strong> {customModelBuildStatus.message}
                {customModelBuildStatus.id && (
                  <p style={{ marginTop: "8px", marginBottom: "4px" }}>
                    {t('scouting.customModelBuilder.modelId')} <span style={{ fontFamily: "monospace" }}>{customModelBuildStatus.id}</span>
                  </p>
                )}
                {customModelBuildStatus.additionalInfo && (
                  <p style={{ marginTop: "4px", fontSize: "0.9em" }}>
                    {customModelBuildStatus.additionalInfo}
                  </p>
                )}
                {customModelBuildStatus.workflowUrl && (
                  <p style={{ marginTop: "8px" }}>
                    <a 
                      href={customModelBuildStatus.workflowUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ 
                        color: '#385723', 
                        textDecoration: 'underline',
                        fontWeight: 'bold'
                      }}
                    >
                      {t('scouting.customModelBuilder.monitorProgress')}
                    </a>
                  </p>
                )}
                {customModelBuildStatus.manualUrl && (
                  <p style={{ marginTop: "8px" }}>
                    <a 
                      href={customModelBuildStatus.manualUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ 
                        color: '#dc2626', 
                        textDecoration: 'underline'
                      }}
                    >
                      {t('scouting.customModelBuilder.triggerManually')}
                    </a>
                  </p>
                )}
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
                {t('scouting.sidebar.kpiVariantsTitle')}
                <InfoTooltip text={t('scouting.sidebar.kpiVariantsTooltip')} /></h4>
              <ul style={{ fontSize: '0.95em', listStyleType: 'disc', paddingLeft: '20px', color: '#4b5563' }}>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.totalCount')}</strong> {t('scouting.sidebar.totalCountDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.per90')}</strong> {t('scouting.sidebar.per90Desc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.p90Sqrt')}</strong> {t('scouting.sidebar.p90SqrtDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.kpiDirect')}</strong> {t('scouting.sidebar.kpiDirectDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.inverted')}</strong> {t('scouting.sidebar.invertedDesc')}</li>
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
                {t('scouting.sidebar.mlImpactTitle')}
                <InfoTooltip text={t('scouting.sidebar.mlImpactTooltip')} />
              </h4>
              <ul style={{ fontSize: '0.95em', listStyleType: 'disc', paddingLeft: '20px', color: '#4b5563' }}>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.relevanceKey')}</strong> {t('scouting.sidebar.relevanceKeyDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.modelComplexity')}</strong> {t('scouting.sidebar.modelComplexityDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.featureTypes')}</strong>
                  <ul style={{ paddingLeft: '20px', listStyleType: 'circle', marginTop: '5px' }}>
                    <li><em>{t('scouting.mlFeatureGroups.currentMetrics')}</em> {t('scouting.sidebar.currentSeasonDesc')}</li>
                    <li><em>{t('scouting.mlFeatureGroups.historicalAggregates')}</em> {t('scouting.sidebar.historicalAggDesc')}</li>
                    <li><em>{t('scouting.mlFeatureGroups.historicalTrends')}</em> {t('scouting.sidebar.growthTrendsDesc')}</li>
                  </ul>
                </li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.interactions')}</strong> {t('scouting.sidebar.interactionsDesc')}</li>
                <li style={{ marginBottom: '10px' }}><strong>{t('scouting.sidebar.defaultLogic')}</strong> {t('scouting.sidebar.defaultLogicDesc')}</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Modal informatiu del Model V14 */}
      {showV14Info && v14ModelConfig && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px'
          }}
          onClick={() => setShowV14Info(false)}
        >
          <div
            style={{
              background: 'white',
              borderRadius: '12px',
              maxWidth: '900px',
              width: '100%',
              maxHeight: '85vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{
              position: 'sticky',
              top: 0,
              background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
              color: 'white',
              padding: '20px 30px',
              borderRadius: '12px 12px 0 0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              zIndex: 1
            }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 600 }}>
                  {v14ModelConfig.model_name}
                </h2>
                <p style={{ margin: '5px 0 0 0', fontSize: '0.9rem', opacity: 0.9 }}>
                  {v14ModelConfig.description}
                </p>
              </div>
              <button
                onClick={() => setShowV14Info(false)}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  border: 'none',
                  color: 'white',
                  fontSize: '24px',
                  cursor: 'pointer',
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background 0.2s',
                  padding: 0
                }}
                onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.3)'}
                onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.2)'}
                title={t('scouting.v14Modal.close')}
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div style={{ padding: '30px' }}>
              {/* Informació general */}
              <div style={{
                background: '#f9fafb',
                padding: '20px',
                borderRadius: '8px',
                marginBottom: '25px',
                border: '1px solid #e5e7eb'
              }}>
                <h3 style={{ marginTop: 0, color: '#1f2937', fontSize: '1.2rem', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.technicalTitle')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px', fontSize: '0.95rem' }}>
                  <div>
                    <strong style={{ color: '#dc2626' }}>{t('scouting.v14Modal.algorithm')}</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#4b5563' }}>{v14ModelConfig.algorithm}</p>
                  </div>
                  <div>
                    <strong style={{ color: '#dc2626' }}>{t('scouting.v14Modal.targetVariable')}</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#4b5563' }}>{v14ModelConfig.target_variable}</p>
                  </div>
                  <div>
                    <strong style={{ color: '#dc2626' }}>{t('scouting.v14Modal.trainingData')}</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#4b5563' }}>{v14ModelConfig.training_data}</p>
                  </div>
                  <div>
                    <strong style={{ color: '#dc2626' }}>{t('scouting.v14Modal.evaluationSeason')}</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#4b5563' }}>{v14ModelConfig.evaluation_season}</p>
                  </div>
                </div>
              </div>

              {/* KPIs per posició */}
              <div style={{ marginBottom: '25px' }}>
                <h3 style={{ color: '#1f2937', fontSize: '1.2rem', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.targetKpisTitle')}
                </h3>
                <p style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.targetKpisDesc')}
                </p>
                {Object.entries(v14ModelConfig.kpi_definitions_for_weight_derivation).map(([position, kpis]) => (
                  <div key={position} style={{
                    background: '#fff',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '15px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <h4 style={{
                      margin: '0 0 10px 0',
                      color: '#dc2626',
                      fontSize: '1.1rem',
                      fontWeight: 600
                    }}>
                      {position}
                    </h4>
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '8px'
                    }}>
                      {kpis.map((kpi, idx) => (
                        <span key={idx} style={{
                          background: '#fee2e2',
                          color: '#991b1b',
                          padding: '5px 12px',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          border: '1px solid #fecaca'
                        }}>
                          {kpi}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Composite Impact KPIs */}
              <div style={{ marginBottom: '25px' }}>
                <h3 style={{ color: '#1f2937', fontSize: '1.2rem', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.impactKpisTitle')}
                </h3>
                <p style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.impactKpisDesc')}
                </p>
                {Object.entries(v14ModelConfig.composite_impact_kpis).map(([position, kpis]) => (
                  <div key={position} style={{
                    background: '#fff',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '15px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <h4 style={{
                      margin: '0 0 10px 0',
                      color: '#059669',
                      fontSize: '1.1rem',
                      fontWeight: 600
                    }}>
                      {position}
                    </h4>
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '8px'
                    }}>
                      {kpis.map((kpi, idx) => (
                        <span key={idx} style={{
                          background: '#d1fae5',
                          color: '#065f46',
                          padding: '6px 14px',
                          borderRadius: '4px',
                          fontSize: '0.9rem',
                          border: '1px solid #6ee7b7',
                          fontWeight: 500
                        }}>
                          {kpi}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Feature Engineering */}
              <div style={{
                background: '#fef3c7',
                padding: '20px',
                borderRadius: '8px',
                border: '1px solid #fde68a'
              }}>
                <h3 style={{ marginTop: 0, color: '#92400e', fontSize: '1.2rem', marginBottom: '15px' }}>
                  {t('scouting.v14Modal.featureEngineeringTitle')}
                </h3>
                <ul style={{ margin: 0, paddingLeft: '20px', color: '#78350f', fontSize: '0.95rem' }}>
                  {Object.entries(v14ModelConfig.feature_engineering).map(([key, value]) => (
                    <li key={key} style={{ marginBottom: '8px' }}>
                      <strong>{key.replace(/_/g, ' ')}:</strong> {value}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ScoutingPage;