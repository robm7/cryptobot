import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import axios from 'axios';
import ConfigWizard from './config-wizard';

// Mock the axios module
jest.mock('axios');
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock the Navigation component
jest.mock('../components/Navigation', () => {
  return function MockNavigation() {
    return <div data-testid="navigation">Navigation</div>;
  };
});

describe('ConfigWizard', () => {
  const mockConfig = {
    services: {
      auth: {
        enabled: true,
        host: '0.0.0.0',
        port: 8000,
        workers: 1,
        description: 'Authentication service',
        dependencies: []
      },
      strategy: {
        enabled: true,
        host: '0.0.0.0',
        port: 8001,
        workers: 1,
        description: 'Strategy management service',
        dependencies: ['auth']
      }
    },
    database: {
      url: 'sqlite:///cryptobot.db',
      pool_size: 5,
      max_overflow: 10,
      echo: false
    },
    logging: {
      level: 'INFO',
      file: 'cryptobot.log',
      format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    },
    security: {
      secret_key: 'test-secret-key',
      token_expiration: 3600,
      password_hash_algorithm: 'argon2'
    }
  };

  beforeEach(() => {
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => 'test-token'),
        setItem: jest.fn(),
      },
      writable: true
    });

    // Mock successful API response
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.post.mockResolvedValue({ data: { message: 'Configuration saved successfully' } });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders the configuration wizard', async () => {
    await act(async () => {
      render(<ConfigWizard />);
    });

    expect(screen.getByText('Configuration Wizard')).toBeInTheDocument();
    expect(screen.getByTestId('navigation')).toBeInTheDocument();
  });

  test('loads configuration data on mount', async () => {
    await act(async () => {
      render(<ConfigWizard />);
    });

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('/config'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer test-token' }
        })
      );
    });
  });

  test('navigates through steps', async () => {
    await act(async () => {
      render(<ConfigWizard />);
    });

    // Step 1: Services
    expect(screen.getByText('Services Configuration')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Step 2: Database
    expect(screen.getByText('Database Configuration')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Step 3: Security
    expect(screen.getByText('Security Configuration')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Step 4: Logging
    expect(screen.getByText('Logging Configuration')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Step 5: Review
    expect(screen.getByText('Review Configuration')).toBeInTheDocument();
    
    // Click Previous button
    fireEvent.click(screen.getByText('Previous'));
    
    // Back to Step 4: Logging
    expect(screen.getByText('Logging Configuration')).toBeInTheDocument();
  });

  test('saves configuration', async () => {
    await act(async () => {
      render(<ConfigWizard />);
    });

    // Navigate to the last step
    fireEvent.click(screen.getByText('Next')); // Step 2
    fireEvent.click(screen.getByText('Next')); // Step 3
    fireEvent.click(screen.getByText('Next')); // Step 4
    fireEvent.click(screen.getByText('Next')); // Step 5
    
    // Click Save Configuration button
    fireEvent.click(screen.getByText('Save Configuration'));
    
    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/config'),
        mockConfig,
        expect.objectContaining({
          headers: { Authorization: 'Bearer test-token' }
        })
      );
    });
    
    // Check for success message
    expect(screen.getByText('Configuration saved successfully')).toBeInTheDocument();
  });
});