import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n/config';
import App from '../App';

jest.mock('../ScoutingPage', () => {
  return function MockScoutingPage() {
    return <div data-testid="scouting-page">Scouting Page</div>;
  };
});

jest.mock('../VisualizationPage', () => {
  return function MockVisualizationPage() {
    return <div data-testid="visualization-page">Visualization Page</div>;
  };
});

jest.mock('react-hot-toast', () => ({
  Toaster: () => <div data-testid="toaster">Toaster</div>
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: {
      changeLanguage: jest.fn(),
      language: 'en'
    }
  })
}));

jest.mock('../components/LanguageSelector', () => {
  return function MockLanguageSelector() {
    return <div data-testid="language-selector">Language Selector</div>;
  };
});

const renderWithProviders = (component) => {
  return render(
    <I18nextProvider i18n={i18n}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </I18nextProvider>
  );
};

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders without crashing', () => {
    renderWithProviders(<App />);
    expect(screen.getByText('app.title')).toBeInTheDocument();
  });

  test('displays header with title and language selector', () => {
    renderWithProviders(<App />);
    expect(screen.getByText('app.title')).toBeInTheDocument();
    expect(screen.getByTestId('language-selector')).toBeInTheDocument();
  });

  test('shows navigation links', () => {
    renderWithProviders(<App />);
    expect(screen.getByText('nav.visualization')).toBeInTheDocument();
    expect(screen.getByText('nav.scouting')).toBeInTheDocument();
  });

  test('navigates to visualization page by default', () => {
    renderWithProviders(<App />);
    expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
  });

  test('navigates to scouting page when scouting link is clicked', async () => {
    renderWithProviders(<App />);
    
    const scoutingLink = screen.getByText('nav.scouting');
    fireEvent.click(scoutingLink);
    
    await waitFor(() => {
      expect(screen.getByTestId('scouting-page')).toBeInTheDocument();
    });
  });

  test('navigates to visualization page when visualization link is clicked', async () => {
    renderWithProviders(<App />);
    
    const scoutingLink = screen.getByText('nav.scouting');
    fireEvent.click(scoutingLink);
    
    await waitFor(() => {
      expect(screen.getByTestId('scouting-page')).toBeInTheDocument();
    });
    
    const visualizationLink = screen.getByText('nav.visualization');
    fireEvent.click(visualizationLink);
    
    await waitFor(() => {
      expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
    });
  });

  test('redirects root path to visualization', () => {
    renderWithProviders(<App />);
    expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
  });

  test('shows toaster component', () => {
    renderWithProviders(<App />);
    expect(screen.getByTestId('toaster')).toBeInTheDocument();
  });

  test('applies correct styling to active navigation link', () => {
    renderWithProviders(<App />);
    
    const visualizationLink = screen.getByText('nav.visualization');
    const scoutingLink = screen.getByText('nav.scouting');
    
    expect(visualizationLink).toHaveStyle('color: #fff');
    expect(scoutingLink).toHaveStyle('color: #adb5bd');
  });
});

describe('App Integration', () => {
  test('maintains state across navigation', () => {
    renderWithProviders(<App />);
    
    fireEvent.click(screen.getByText('nav.scouting'));
    
    fireEvent.click(screen.getByText('nav.visualization'));
    
    expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
  });

  test('handles browser back/forward navigation', () => {
    renderWithProviders(<App />);
    
    expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('nav.scouting'));
    expect(screen.getByTestId('scouting-page')).toBeInTheDocument();
    
    window.history.back();
    
    expect(screen.getByTestId('visualization-page')).toBeInTheDocument();
  });
});
