/**
 * Test suite for the ScoutingPage component.
 * Tests player selection, prediction functionality, and custom model building.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n/config';
import ScoutingPage from '../ScoutingPage';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

// Mock react-hot-toast
jest.mock('react-hot-toast', () => ({
  toast: {
    error: jest.fn(),
    promise: jest.fn((promise, messages) => {
      return promise.then(
        (result) => {
          if (messages.success) messages.success(result);
          return result;
        },
        (error) => {
          if (messages.error) messages.error(error);
          throw error;
        }
      );
    })
  }
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key, options) => {
      const translations = {
        'scouting.selectPlayer': 'Select Player',
        'scouting.selectSeason': 'Select Season',
        'scouting.selectModel': 'Select Model',
        'scouting.predict': 'Predict',
        'scouting.predicting': 'Predicting...',
        'scouting.defaultModel': 'Default Model',
        'scouting.customModel.title': 'Custom Model',
        'scouting.customModel.selectCustomModel': 'Select Custom Model',
        'scouting.customModel.noModelsAvailable': 'No models available',
        'scouting.customModel.selectModelOption': 'Select model',
        'scouting.customModel.yourModel': '(Your Model)',
        'scouting.customModel.communityModel': '(Community Model)',
        'scouting.errors.selectPlayerSeason': 'Please select a player and season',
        'scouting.errors.modelLoadFailed': 'Model loading failed',
        'scouting.errors.predictionFailed': 'Prediction failed',
        'scouting.errors.playersLoadFailed': 'Failed to load players',
        'scouting.result.score': 'Score',
        'scouting.result.player': 'Player',
        'scouting.result.season': 'Season',
        'scouting.result.age': 'Age',
        'scouting.result.position': 'Position',
        'scouting.result.nineties': '90s Played',
        'scouting.result.potentialScore': 'Potential Score',
        'scouting.loadingModel': 'Loading model...',
        'scouting.age': 'Age',
        'scouting.playerDob': 'Date of Birth',
        'scouting.modelConfigButton': 'Model Configuration',
        'scouting.customModelBuilder.modelName': 'Model Name',
        'scouting.customModelBuilder.modelNamePlaceholder': 'Enter model name',
        'scouting.customModelBuilder.positionGroup': 'Position Group',
        'scouting.customModelBuilder.attacker': 'Attacker',
        'scouting.customModelBuilder.midfielder': 'Midfielder',
        'scouting.customModelBuilder.defender': 'Defender',
        'scouting.customModelBuilder.step1Title': 'Step 1: Select Impact KPIs',
        'scouting.customModelBuilder.step1Tooltip': 'Select KPIs that impact the model',
        'scouting.customModelBuilder.step1Description': 'Choose metrics that will influence the model',
        'scouting.customModelBuilder.step2Title': 'Step 2: Select Target KPIs',
        'scouting.customModelBuilder.step2Tooltip': 'Select KPIs for weighting',
        'scouting.customModelBuilder.step2Description': 'Choose metrics for model weighting',
        'scouting.customModelBuilder.step3Title': 'Step 3: ML Features',
        'scouting.customModelBuilder.step3Tooltip': 'Configure ML features',
        'scouting.customModelBuilder.step3Description': 'Select machine learning features',
        'scouting.customModelBuilder.useDefaultMlFeatures': 'Use default ML features',
        'scouting.customModelBuilder.defaultFeaturesNote': 'Recommended for most users',
        'scouting.customModelBuilder.selectCustomFeatures': 'Select Custom Features',
        'scouting.customModelBuilder.searchMlFeatures': 'Search features...',
        'scouting.customModelBuilder.mlFeaturesNote': 'Customize the feature set',
        'scouting.customModelBuilder.selectedFeatures': 'Selected features',
        'scouting.customModelBuilder.clearSelection': 'Clear Selection',
        'scouting.customModelBuilder.buildModel': 'Build Model',
        'scouting.customModelBuilder.building': 'Building...',
        'scouting.customModelBuilder.starting': 'Starting model training...',
        'scouting.customModelBuilder.successTitle': 'Success',
        'scouting.customModelBuilder.errorBuildFailed': 'Build failed',
        'scouting.customModelBuilder.errorValidation': 'Please fill all required fields',
        'scouting.customModelBuilder.loadingKpis': 'Loading KPIs...',
        'scouting.customModelBuilder.loadingMlFeatures': 'Loading ML features...',
        'scouting.customModelBuilder.noImpactKpis': 'No impact KPIs found',
        'scouting.customModelBuilder.noTargetKpis': 'No target KPIs found',
        'scouting.customModelBuilder.noMlFeatures': 'No ML features found',
        'scouting.customModelBuilder.estimatedTimeMessage': 'Estimated time: {time}',
        'scouting.customModelBuilder.monitorGitHub': 'Monitor progress on GitHub',
        'scouting.customModelBuilder.willAppear': 'Model will appear in the list when ready',
        'scouting.customModelBuilder.modelId': 'Model ID',
        'scouting.customModelBuilder.monitorProgress': 'Monitor Progress',
        'scouting.customModelBuilder.triggerManually': 'Trigger Manually',
        'scouting.sidebar.kpiVariantsTitle': 'KPI Variants',
        'scouting.sidebar.kpiVariantsTooltip': 'Different ways to measure KPIs',
        'scouting.sidebar.totalCount': 'Total/Count',
        'scouting.sidebar.totalCountDesc': 'Raw count of events',
        'scouting.sidebar.per90': 'Per 90',
        'scouting.sidebar.per90Desc': 'Normalized per 90 minutes',
        'scouting.sidebar.p90Sqrt': 'P90 √',
        'scouting.sidebar.p90SqrtDesc': 'Square root of per 90',
        'scouting.sidebar.kpiDirect': 'KPI Direct',
        'scouting.sidebar.kpiDirectDesc': 'Direct KPI calculation',
        'scouting.sidebar.inverted': 'Inverted',
        'scouting.sidebar.invertedDesc': 'Inverted values for negative metrics',
        'scouting.sidebar.mlImpactTitle': 'ML Impact',
        'scouting.sidebar.mlImpactTooltip': 'How features impact the model',
        'scouting.sidebar.relevanceKey': 'Relevance',
        'scouting.sidebar.relevanceKeyDesc': 'Feature relevance to predictions',
        'scouting.sidebar.modelComplexity': 'Complexity',
        'scouting.sidebar.modelComplexityDesc': 'Model complexity management',
        'scouting.sidebar.featureTypes': 'Feature Types',
        'scouting.sidebar.currentSeasonDesc': 'Current season metrics',
        'scouting.sidebar.historicalAggDesc': 'Historical performance aggregates',
        'scouting.sidebar.growthTrendsDesc': 'Growth and trend analysis',
        'scouting.sidebar.interactions': 'Interactions',
        'scouting.sidebar.interactionsDesc': 'Feature interaction terms',
        'scouting.sidebar.defaultLogic': 'Default Logic',
        'scouting.sidebar.defaultLogicDesc': 'Recommended feature selection',
        'scouting.mlFeatureGroups.currentMetrics': 'Current Season: Metrics',
        'scouting.mlFeatureGroups.currentInteractions': 'Current Season: Interactions & Polynomials',
        'scouting.mlFeatureGroups.historicalAggregates': 'Historical Performance: Aggregates',
        'scouting.mlFeatureGroups.historicalTrends': 'Historical Performance: Trends',
        'scouting.mlFeatureGroups.growthRatios': 'Season-over-Season: Growth & Ratios',
        'scouting.mlFeatureGroups.historicalContext': 'Historical Context',
        'scouting.mlFeatureGroups.numHistSeasons': 'Number Of Historical Seasons',
        'scouting.v14Modal.close': 'Close',
        'scouting.v14Modal.technicalTitle': 'Technical Details',
        'scouting.v14Modal.algorithm': 'Algorithm',
        'scouting.v14Modal.targetVariable': 'Target Variable',
        'scouting.v14Modal.trainingData': 'Training Data',
        'scouting.v14Modal.evaluationSeason': 'Evaluation Season',
        'scouting.v14Modal.targetKpisTitle': 'Target KPIs',
        'scouting.v14Modal.targetKpisDesc': 'KPIs used for model weighting',
        'scouting.v14Modal.impactKpisTitle': 'Impact KPIs',
        'scouting.v14Modal.impactKpisDesc': 'KPIs that impact model predictions',
        'scouting.v14Modal.featureEngineeringTitle': 'Feature Engineering'
      };
      return translations[key] || key;
    }
  })
}));

const renderWithProviders = (component) => {
  return render(
    <I18nextProvider i18n={i18n}>
      {component}
    </I18nextProvider>
  );
};

describe('ScoutingPage Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    
    // Mock successful API responses
    mockedAxios.get.mockImplementation((url) => {
      if (url.includes('/players')) {
        return Promise.resolve({
          data: [
            {
              player_id: '12345',
              name: 'Test Player',
              seasons: ['2015_2016', '2016_2017'],
              dob: '1995-01-01'
            }
          ]
        });
      }
      if (url.includes('/api/custom_model/available_kpis')) {
        return Promise.resolve({
          data: {
            structured_kpis: [
              {
                metric_base_id: 'goals',
                metric_base_label: 'Goals',
                options: [
                  { id: 'goals', full_label: 'Goals', label_variant: 'Total' },
                  { id: 'goals_p90', full_label: 'Goals (per 90 min)', label_variant: 'Per 90' }
                ]
              }
            ]
          }
        });
      }
      if (url.includes('/api/custom_model/available_ml_features')) {
        return Promise.resolve({
          data: {
            available_ml_features: ['current_goals', 'hist_avg_goals']
          }
        });
      }
      if (url.includes('/api/model/default_v14_config')) {
        return Promise.resolve({
          data: {
            model_name: 'Default V14 Model',
            description: 'Default model description'
          }
        });
      }
      if (url.includes('/api/custom_model/list')) {
        return Promise.resolve({
          data: {
            custom_models: [
              {
                id: 'custom_model_1',
                name: 'Custom Model 1',
                position_group: 'Attacker'
              }
            ]
          }
        });
      }
      if (url.includes('/scouting_predict')) {
        return Promise.resolve({
          data: {
            player_id: '12345',
            player_name: 'Test Player',
            predicted_potential_score: 150.5,
            model_used: 'default_v14'
          }
        });
      }
      return Promise.resolve({ data: {} });
    });
  });

  test('renders without crashing', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Select Player')).toBeInTheDocument();
    });
  });

  test('loads players on mount', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/players')
      );
    });
  });

  test('loads KPIs and ML features on mount', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/custom_model/available_kpis')
      );
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/custom_model/available_ml_features')
      );
    });
  });

  test('displays player selection dropdown', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Select Player')).toBeInTheDocument();
      expect(screen.getByDisplayValue('-- Select Player --')).toBeInTheDocument();
    });
  });

  test('displays season selection dropdown after player selection', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      const playerSelect = screen.getByDisplayValue('-- Select Player --');
      fireEvent.change(playerSelect, { target: { value: 'Test Player' } });
    });
    
    await waitFor(() => {
      expect(screen.getByText('Select Season')).toBeInTheDocument();
    });
  });

  test('displays model selection dropdown', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Select Model')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Default Model')).toBeInTheDocument();
    });
  });

  test('shows custom model selection when custom model is selected', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      const modelSelect = screen.getByDisplayValue('Default Model');
      fireEvent.change(modelSelect, { target: { value: 'custom' } });
    });
    
    await waitFor(() => {
      expect(screen.getByText('Select Custom Model:')).toBeInTheDocument();
    });
  });

  test('displays predict button', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Predict')).toBeInTheDocument();
    });
  });

  test('predict button is disabled when no player selected', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      const predictButton = screen.getByText('Predict');
      expect(predictButton).toBeDisabled();
    });
  });

  test('predict button is enabled when player and season selected', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      // Select player
      const playerSelect = screen.getByDisplayValue('-- Select Player --');
      fireEvent.change(playerSelect, { target: { value: 'Test Player' } });
    });
    
    await waitFor(() => {
      // Select season
      const seasonSelect = screen.getByDisplayValue('-- Select Season --');
      fireEvent.change(seasonSelect, { target: { value: '2015_2016' } });
    });
    
    await waitFor(() => {
      const predictButton = screen.getByText('Predict');
      expect(predictButton).not.toBeDisabled();
    });
  });

  test('handles prediction request', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      // Select player
      const playerSelect = screen.getByDisplayValue('-- Select Player --');
      fireEvent.change(playerSelect, { target: { value: 'Test Player' } });
    });
    
    await waitFor(() => {
      // Select season
      const seasonSelect = screen.getByDisplayValue('-- Select Season --');
      fireEvent.change(seasonSelect, { target: { value: '2015_2016' } });
    });
    
    await waitFor(() => {
      // Click predict
      const predictButton = screen.getByText('Predict');
      fireEvent.click(predictButton);
    });
    
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/scouting_predict'),
        expect.objectContaining({
          params: {
            player_id: '12345',
            season: '2015_2016',
            model_id: 'default_v14'
          }
        })
      );
    });
  });

  test('displays prediction result', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      // Select player
      const playerSelect = screen.getByDisplayValue('-- Select Player --');
      fireEvent.change(playerSelect, { target: { value: 'Test Player' } });
    });
    
    await waitFor(() => {
      // Select season
      const seasonSelect = screen.getByDisplayValue('-- Select Season --');
      fireEvent.change(seasonSelect, { target: { value: '2015_2016' } });
    });
    
    await waitFor(() => {
      // Click predict
      const predictButton = screen.getByText('Predict');
      fireEvent.click(predictButton);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Score: 150.5/200')).toBeInTheDocument();
    });
  });

  test('displays custom model builder form', async () => {
    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      expect(screen.getByText('Custom Model')).toBeInTheDocument();
      expect(screen.getByText('Model Name:')).toBeInTheDocument();
      expect(screen.getByText('Position Group:')).toBeInTheDocument();
    });
  });

  test('handles custom model building', async () => {
    mockedAxios.post.mockResolvedValue({
      data: {
        success: true,
        message: 'Model training started',
        custom_model_id: 'custom_model_123'
      }
    });

    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      // Fill in model name
      const modelNameInput = screen.getByPlaceholderText('Enter model name');
      fireEvent.change(modelNameInput, { target: { value: 'Test Model' } });
      
      // Select position group
      const positionSelect = screen.getByDisplayValue('Attacker');
      fireEvent.change(positionSelect, { target: { value: 'Migcampista' } });
      
      // Select some KPIs (this would require more complex setup in real test)
      // For now, just test that the form exists
      expect(screen.getByText('Build Model')).toBeInTheDocument();
    });
  });

  test('handles API errors gracefully', async () => {
    mockedAxios.get.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      // Should still render without crashing
      expect(screen.getByText('Select Player')).toBeInTheDocument();
    });
  });

  test('filters U21 eligible players', async () => {
    mockedAxios.get.mockImplementation((url) => {
      if (url.includes('/players')) {
        return Promise.resolve({
          data: [
            {
              player_id: '12345',
              name: 'Young Player',
              seasons: ['2015_2016', '2016_2017'],
              dob: '1995-01-01' // 21 years old in 2016
            },
            {
              player_id: '67890',
              name: 'Old Player',
              seasons: ['2015_2016', '2016_2017'],
              dob: '1990-01-01' // 26 years old in 2016
            }
          ]
        });
      }
      return Promise.resolve({ data: {} });
    });

    renderWithProviders(<ScoutingPage />);
    
    await waitFor(() => {
      const playerSelect = screen.getByDisplayValue('-- Select Player --');
      fireEvent.change(playerSelect, { target: { value: 'Young Player' } });
    });
    
    await waitFor(() => {
      // Should only show U21 eligible seasons
      expect(screen.getByText('2015_2016 (Age: 21)')).toBeInTheDocument();
    });
  });
});
