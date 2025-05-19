/**
 * @jest-environment jsdom
 */

import {
  isFirstRun,
  markFirstRunComplete,
  resetFirstRunStatus,
  getFirstRunStatus,
  saveSetupPreferences,
  getSetupPreferences,
  getSampleConfig
} from './firstRunUtils';

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: jest.fn(key => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn(key => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    })
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock crypto for random key generation
Object.defineProperty(window, 'crypto', {
  value: {
    getRandomValues: jest.fn(() => new Uint8Array(32).fill(1))
  }
});

describe('First Run Utils', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  describe('isFirstRun', () => {
    it('should return true when cryptobot_first_run is not set', () => {
      expect(isFirstRun()).toBe(true);
      expect(localStorageMock.getItem).toHaveBeenCalledWith('cryptobot_first_run');
    });

    it('should return false when cryptobot_first_run is set', () => {
      localStorageMock.setItem('cryptobot_first_run', JSON.stringify({ completed: true }));
      expect(isFirstRun()).toBe(false);
    });
  });

  describe('markFirstRunComplete', () => {
    it('should set cryptobot_first_run with completed status', () => {
      markFirstRunComplete();
      expect(localStorageMock.setItem).toHaveBeenCalled();
      
      const storedValue = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
      expect(storedValue.completed).toBe(true);
      expect(storedValue.timestamp).toBeDefined();
    });

    it('should allow setting completed to false', () => {
      markFirstRunComplete(false);
      
      const storedValue = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
      expect(storedValue.completed).toBe(false);
    });
  });

  describe('resetFirstRunStatus', () => {
    it('should remove cryptobot_first_run from localStorage', () => {
      resetFirstRunStatus();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('cryptobot_first_run');
    });
  });

  describe('getFirstRunStatus', () => {
    it('should return null when status is not set', () => {
      expect(getFirstRunStatus()).toBeNull();
    });

    it('should return the status object when set', () => {
      const status = { completed: true, timestamp: '2025-05-15T12:00:00Z' };
      localStorageMock.setItem('cryptobot_first_run', JSON.stringify(status));
      
      expect(getFirstRunStatus()).toEqual(status);
    });
  });

  describe('saveSetupPreferences', () => {
    it('should save preferences to localStorage', () => {
      const preferences = { 
        showTooltips: true,
        theme: 'dark'
      };
      
      saveSetupPreferences(preferences);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'cryptobot_setup_preferences',
        JSON.stringify(preferences)
      );
    });
  });

  describe('getSetupPreferences', () => {
    it('should return null when preferences are not set', () => {
      expect(getSetupPreferences()).toBeNull();
    });

    it('should return the preferences object when set', () => {
      const preferences = { showTooltips: true, theme: 'dark' };
      localStorageMock.setItem('cryptobot_setup_preferences', JSON.stringify(preferences));
      
      expect(getSetupPreferences()).toEqual(preferences);
    });
  });

  describe('getSampleConfig', () => {
    it('should return basic config by default', () => {
      const config = getSampleConfig();
      expect(config.services.trade.enabled).toBe(true);
      expect(config.services.backtest.enabled).toBe(false);
    });

    it('should return backtesting config when specified', () => {
      const config = getSampleConfig('backtesting');
      expect(config.services.trade.enabled).toBe(false);
      expect(config.services.backtest.enabled).toBe(true);
      expect(config.logging.level).toBe('DEBUG');
    });

    it('should return advanced config when specified', () => {
      const config = getSampleConfig('advanced');
      expect(config.services.trade.enabled).toBe(true);
      expect(config.services.backtest.enabled).toBe(true);
      expect(config.database.url).toContain('postgresql');
    });

    it('should fall back to basic config for unknown use case', () => {
      const config = getSampleConfig('unknown');
      expect(config.services.trade.enabled).toBe(true);
      expect(config.database.url).toContain('sqlite');
    });
  });
});