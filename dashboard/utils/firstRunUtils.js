/**
 * Utility functions for first-run detection and setup assistance
 */

/**
 * Check if this is the first time the application is being run
 * @returns {boolean} True if this is the first run, false otherwise
 */
export function isFirstRun() {
  // Check if the first-run flag exists in localStorage
  return localStorage.getItem('cryptobot_first_run') === null;
}

/**
 * Mark the application as having been run
 * @param {boolean} completed - Whether the setup was completed (default: true)
 */
export function markFirstRunComplete(completed = true) {
  localStorage.setItem('cryptobot_first_run', JSON.stringify({
    completed: completed,
    timestamp: new Date().toISOString()
  }));
}

/**
 * Reset the first-run status (for testing or user-requested reset)
 */
export function resetFirstRunStatus() {
  localStorage.removeItem('cryptobot_first_run');
}

/**
 * Get the first run status object
 * @returns {Object|null} The first run status object or null if not set
 */
export function getFirstRunStatus() {
  const status = localStorage.getItem('cryptobot_first_run');
  return status ? JSON.parse(status) : null;
}

/**
 * Save user preferences from the setup process
 * @param {Object} preferences - User preferences object
 */
export function saveSetupPreferences(preferences) {
  localStorage.setItem('cryptobot_setup_preferences', JSON.stringify(preferences));
}

/**
 * Get saved user preferences from the setup process
 * @returns {Object|null} User preferences or null if not set
 */
export function getSetupPreferences() {
  const preferences = localStorage.getItem('cryptobot_setup_preferences');
  return preferences ? JSON.parse(preferences) : null;
}

/**
 * Get sample configurations for different use cases
 * @param {string} useCase - The use case to get configuration for
 * @returns {Object} Sample configuration object
 */
export function getSampleConfig(useCase = 'basic') {
  const configs = {
    basic: {
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
        },
        strategy: {
          enabled: true,
          host: 'localhost',
          port: 8002,
          workers: 1,
          description: 'Strategy execution service'
        },
        backtest: {
          enabled: false,
          host: 'localhost',
          port: 8003,
          workers: 1,
          description: 'Backtesting service'
        }
      },
      database: {
        url: 'sqlite:///cryptobot.db',
        pool_size: 5,
        max_overflow: 10,
        echo: false
      },
      security: {
        secret_key: Array.from(window.crypto.getRandomValues(new Uint8Array(32)))
          .map(b => b.toString(16).padStart(2, '0'))
          .join(''),
        token_expiration: 86400,
        password_hash_algorithm: 'argon2'
      },
      logging: {
        level: 'INFO',
        file: 'cryptobot.log',
        format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      }
    },
    backtesting: {
      services: {
        trade: {
          enabled: false,
          host: 'localhost',
          port: 8000,
          workers: 1,
          description: 'Trade execution service'
        },
        data: {
          enabled: true,
          host: 'localhost',
          port: 8001,
          workers: 2,
          description: 'Market data service'
        },
        strategy: {
          enabled: true,
          host: 'localhost',
          port: 8002,
          workers: 1,
          description: 'Strategy execution service'
        },
        backtest: {
          enabled: true,
          host: 'localhost',
          port: 8003,
          workers: 4,
          description: 'Backtesting service'
        }
      },
      database: {
        url: 'sqlite:///cryptobot_backtest.db',
        pool_size: 10,
        max_overflow: 20,
        echo: true
      },
      security: {
        secret_key: Array.from(window.crypto.getRandomValues(new Uint8Array(32)))
          .map(b => b.toString(16).padStart(2, '0'))
          .join(''),
        token_expiration: 86400,
        password_hash_algorithm: 'argon2'
      },
      logging: {
        level: 'DEBUG',
        file: 'cryptobot_backtest.log',
        format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      }
    },
    advanced: {
      services: {
        trade: {
          enabled: true,
          host: 'localhost',
          port: 8000,
          workers: 4,
          description: 'Trade execution service'
        },
        data: {
          enabled: true,
          host: 'localhost',
          port: 8001,
          workers: 4,
          description: 'Market data service'
        },
        strategy: {
          enabled: true,
          host: 'localhost',
          port: 8002,
          workers: 2,
          description: 'Strategy execution service'
        },
        backtest: {
          enabled: true,
          host: 'localhost',
          port: 8003,
          workers: 2,
          description: 'Backtesting service'
        }
      },
      database: {
        url: 'postgresql://user:password@localhost/cryptobot',
        pool_size: 20,
        max_overflow: 40,
        echo: false
      },
      security: {
        secret_key: Array.from(window.crypto.getRandomValues(new Uint8Array(32)))
          .map(b => b.toString(16).padStart(2, '0'))
          .join(''),
        token_expiration: 3600,
        password_hash_algorithm: 'argon2'
      },
      logging: {
        level: 'INFO',
        file: 'cryptobot.log',
        format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      }
    }
  };
  
  return configs[useCase] || configs.basic;
}