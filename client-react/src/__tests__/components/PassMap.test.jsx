import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/config';
import PassMap from '../../components/PassMap';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios;

jest.mock('react-konva', () => ({
  Stage: ({ children, ...props }) => <div data-testid="stage" {...props}>{children}</div>,
  Layer: ({ children, ...props }) => <div data-testid="layer" {...props}>{children}</div>,
  Rect: (props) => <div data-testid="rect" {...props} />,
  Line: (props) => <div data-testid="line" {...props} />,
  Text: (props) => <div data-testid="text" {...props} />
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key, options) => {
      const translations = {
        'visualization.passMapDetails.title': 'Pass Map',
        'visualization.passMapDetails.completed': 'Completed',
        'visualization.passMapDetails.incomplete': 'Incomplete',
        'visualization.passMapDetails.assists': 'Assists',
        'visualization.passMapDetails.finalThird': 'Final Third',
        'visualization.passMapDetails.finalThirdIfApplicable': 'Final Third (if applicable)',
        'visualization.passMapDetails.completionRate': 'Completion Rate',
        'visualization.passMapDetails.finalThirdRate': 'Final Third Rate',
        'visualization.passMapDetails.totalAssists': 'Total Assists',
        'visualization.passMapDetails.zoneCompletion': 'Zone Completion Rate',
        'visualization.passMapDetails.heatmapAlt': 'Pass Completion Heatmap',
        'visualization.passMapDetails.errorLoading': 'Error loading heatmap',
        'visualization.passMapDetails.loading': 'Loading heatmap...',
        'visualization.passMapDetails.errorData': 'No pass data returned',
        'visualization.passMapDetails.errorFetch': 'Error fetching pass data'
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

describe('PassMap Component', () => {
  const mockPassData = [
    {
      start_x: 50,
      start_y: 30,
      end_x: 60,
      end_y: 40,
      completed: true,
      assist: false,
      final_third: false
    },
    {
      start_x: 70,
      start_y: 50,
      end_x: 80,
      end_y: 60,
      completed: false,
      assist: false,
      final_third: true
    },
    {
      start_x: 60,
      start_y: 40,
      end_x: 85,
      end_y: 45,
      completed: true,
      assist: true,
      final_third: true
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockedAxios.get.mockResolvedValue({
      data: {
        passes: mockPassData
      }
    });
  });

  test('renders without crashing', () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    expect(screen.getByText('Pass Map')).toBeInTheDocument();
  });

  test('renders with required props', () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    expect(screen.getByText('Pass Map')).toBeInTheDocument();
  });

  test('renders without props', () => {
    renderWithProviders(<PassMap />);
    expect(screen.getByText('Pass Map')).toBeInTheDocument();
  });

  test('fetches pass data on mount', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/pass_map_plot'),
        expect.objectContaining({
          params: {
            player_id: '12345',
            season: '2015_2016'
          }
        })
      );
    });
  });

  test('displays pass statistics', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('Completion Rate')).toBeInTheDocument();
      expect(screen.getByText('Final Third Rate')).toBeInTheDocument();
      expect(screen.getByText('Total Assists')).toBeInTheDocument();
    });
  });

  test('calculates correct statistics', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('66.67%')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  test('displays filter checkboxes', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByText('Incomplete')).toBeInTheDocument();
      expect(screen.getByText('Assists')).toBeInTheDocument();
      expect(screen.getByText('Final Third')).toBeInTheDocument();
    });
  });

  test('filter checkboxes are checked by default', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      const completedCheckbox = screen.getByLabelText('Completed');
      const incompleteCheckbox = screen.getByLabelText('Incomplete');
      const assistsCheckbox = screen.getByLabelText('Assists');
      
      expect(completedCheckbox).toBeChecked();
      expect(incompleteCheckbox).toBeChecked();
      expect(assistsCheckbox).toBeChecked();
    });
  });

  test('final third checkbox is unchecked by default', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      const finalThirdCheckbox = screen.getByLabelText('Final Third');
      expect(finalThirdCheckbox).not.toBeChecked();
    });
  });

  test('toggles filter checkboxes', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      const completedCheckbox = screen.getByLabelText('Completed');
      fireEvent.click(completedCheckbox);
      expect(completedCheckbox).not.toBeChecked();
    });
  });

  test('displays heatmap when R2_PUBLIC_URL is available', () => {
    const originalEnv = process.env;
    process.env = {
      ...originalEnv,
      VITE_R2_PUBLIC_URL: 'https://example.com'
    };

    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    expect(screen.getByAltText('Pass Completion Heatmap')).toBeInTheDocument();
    expect(screen.getByAltText('Pass Completion Heatmap')).toHaveAttribute(
      'src',
      'https://example.com/12345_2015_2016_pass_completion_heatmap.png'
    );

    process.env = originalEnv;
  });

  test('shows loading message when R2_PUBLIC_URL is not available', () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    expect(screen.getByText('Loading heatmap...')).toBeInTheDocument();
  });

  test('handles API errors gracefully', async () => {
    mockedAxios.get.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('Error fetching pass data')).toBeInTheDocument();
    });
  });

  test('handles empty pass data', async () => {
    mockedAxios.get.mockResolvedValue({
      data: {
        passes: []
      }
    });

    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('No pass data returned')).toBeInTheDocument();
    });
  });

  test('handles missing pass data', async () => {
    mockedAxios.get.mockResolvedValue({
      data: {}
    });

    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByText('No pass data returned')).toBeInTheDocument();
    });
  });

  test('renders stage and layer components', async () => {
    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(screen.getByTestId('stage')).toBeInTheDocument();
      expect(screen.getByTestId('layer')).toBeInTheDocument();
    });
  });

  test('handles image loading errors', () => {
    const originalEnv = process.env;
    process.env = {
      ...originalEnv,
      VITE_R2_PUBLIC_URL: 'https://example.com'
    };

    renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    const image = screen.getByAltText('Pass Completion Heatmap');
    fireEvent.error(image);
    
    expect(screen.getByText('Error loading heatmap')).toBeInTheDocument();

    process.env = originalEnv;
  });

  test('updates when playerId or season changes', async () => {
    const { rerender } = renderWithProviders(<PassMap playerId="12345" season="2015_2016" />);
    
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });

    rerender(
      <I18nextProvider i18n={i18n}>
        <PassMap playerId="67890" season="2016_2017" />
      </I18nextProvider>
    );

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(mockedAxios.get).toHaveBeenLastCalledWith(
        expect.stringContaining('/pass_map_plot'),
        expect.objectContaining({
          params: {
            player_id: '67890',
            season: '2016_2017'
          }
        })
      );
    });
  });

  test('does not fetch data when playerId or season is missing', () => {
    renderWithProviders(<PassMap />);
    
    expect(mockedAxios.get).not.toHaveBeenCalled();
  });
});
