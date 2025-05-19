/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SetupWizard from './SetupWizard';
import * as firstRunUtils from '../utils/firstRunUtils';

// Mock the next/router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock the firstRunUtils
jest.mock('../utils/firstRunUtils', () => ({
  markFirstRunComplete: jest.fn(),
  saveSetupPreferences: jest.fn(),
  getSampleConfig: jest.fn(() => ({
    services: {
      trade: {
        enabled: true,
        host: 'localhost',
        port: 8000,
        workers: 2,
        description: 'Trade execution service'
      },
      data: {
        enabled: true,
        host: 'localhost',
        port: 8001,
        workers: 2,
        description: 'Market data service'
      }
    },
    database: {
      url: 'sqlite:///cryptobot.db',
      pool_size: 5,
      max_overflow: 10,
      echo: false
    },
    security: {
      secret_key: 'test-key',
      token_expiration: 86400,
      password_hash_algorithm: 'argon2'
    },
    logging: {
      level: 'INFO',
      file: 'cryptobot.log',
      format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }
  }))
}));

describe('SetupWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the welcome screen as the first step', () => {
    render(<SetupWizard />);
    
    expect(screen.getByText('Welcome to CryptoBot')).toBeInTheDocument();
    expect(screen.getByText('Your automated cryptocurrency trading platform')).toBeInTheDocument();
    expect(screen.getByText('What is CryptoBot?')).toBeInTheDocument();
  });

  it('navigates to the next step when Next button is clicked', () => {
    render(<SetupWizard />);
    
    // Initial step is Welcome
    expect(screen.getByText('Welcome to CryptoBot')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Should now be on Configuration Preset step
    expect(screen.getByText('Configuration Preset')).toBeInTheDocument();
    expect(screen.getByText('Choose a configuration preset that matches your needs')).toBeInTheDocument();
  });

  it('allows skipping the setup process', () => {
    const onCompleteMock = jest.fn();
    render(<SetupWizard onComplete={onCompleteMock} />);
    
    // Click Skip Setup button
    fireEvent.click(screen.getByText('Skip Setup'));
    
    // Should call markFirstRunComplete and onComplete
    expect(firstRunUtils.markFirstRunComplete).toHaveBeenCalledWith(true);
    expect(firstRunUtils.saveSetupPreferences).toHaveBeenCalled();
    expect(onCompleteMock).toHaveBeenCalled();
  });

  it('allows selecting different configuration presets', async () => {
    render(<SetupWizard />);
    
    // Navigate to Configuration Preset step
    fireEvent.click(screen.getByText('Next'));
    
    // Click on Backtesting preset
    fireEvent.click(screen.getByText('Backtesting'));
    
    // The Backtesting preset should be highlighted
    const backtestingCard = screen.getByText('Backtesting').closest('div');
    expect(backtestingCard).toHaveClass('border-blue-500');
  });

  it('completes the setup process when Get Started is clicked on the final step', async () => {
    const onCompleteMock = jest.fn();
    render(<SetupWizard onComplete={onCompleteMock} />);
    
    // Navigate through all steps
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByText('Next'));
    }
    
    // Should now be on the final step
    expect(screen.getByText('Setup Complete')).toBeInTheDocument();
    
    // Click Get Started button
    fireEvent.click(screen.getByText('Get Started'));
    
    // Should call markFirstRunComplete and onComplete
    expect(firstRunUtils.markFirstRunComplete).toHaveBeenCalledWith(true);
    expect(firstRunUtils.saveSetupPreferences).toHaveBeenCalled();
    expect(onCompleteMock).toHaveBeenCalled();
  });

  it('allows navigating back to previous steps', () => {
    render(<SetupWizard />);
    
    // Navigate to second step
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Configuration Preset')).toBeInTheDocument();
    
    // Navigate back to first step
    fireEvent.click(screen.getByText('Previous'));
    expect(screen.getByText('Welcome to CryptoBot')).toBeInTheDocument();
  });
});