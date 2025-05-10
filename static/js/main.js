// Main JavaScript functionality for CryptoBot

// Helper functions
function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatPercentage(value) {
  return new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value / 100);
}

function timeAgo(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  let interval = Math.floor(seconds / 31536000);
  if (interval >= 1) return interval + ' year' + (interval === 1 ? '' : 's') + ' ago';
  interval = Math.floor(seconds / 2592000);
  if (interval >= 1) return interval + ' month' + (interval === 1 ? '' : 's') + ' ago';
  interval = Math.floor(seconds / 86400);
  if (interval >= 1) return interval + ' day' + (interval === 1 ? '' : 's') + ' ago';
  interval = Math.floor(seconds / 3600);
  if (interval >= 1) return interval + ' hour' + (interval === 1 ? '' : 's') + ' ago';
  interval = Math.floor(seconds / 60);
  if (interval >= 1) return interval + ' minute' + (interval === 1 ? '' : 's') + ' ago';
  return 'just now';
}

// Store JWT token
let authToken = localStorage.getItem('authToken') || '';

// Fetch data from API with auth headers
async function fetchData(url) {
  try {
    console.log('Fetching URL:', url);
    console.log('Current authToken:', authToken);
    console.log('Current cookies:', document.cookie);
    
    const headers = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
    
    // Include both auth methods
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
      console.log('Adding Authorization header with token');
    }
    
    // Get CSRF token from cookie
    const csrfToken = document.cookie.split('; ')
      .find(row => row.startsWith('csrf_access_token='))
      ?.split('=')[1];
    
    if (csrfToken) {
      headers['X-CSRF-TOKEN'] = csrfToken;
    }
    
    // Verify at least one auth method is present
    if (!authToken && !document.cookie.includes('access_token_cookie')) {
      console.error('No authentication methods available');
      window.location.href = '/';
      return null;
    }
    
    const response = await fetch(url, {
      headers,
      credentials: 'include',
      mode: 'cors'
    });
    
    console.log('Response status:', response.status);
    if (!response.ok) {
      if (response.status === 401) {
        // Clear auth state on 401
        localStorage.removeItem('authToken');
        document.cookie = 'access_token_cookie=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/';
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Received data from', url, ':', data);
    return data;
  } catch (error) {
    console.error('Error fetching data from', url, ':', error);
    return null;
  }
}

// Handle login form submission
async function handleLogin(event) {
  event.preventDefault();
  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerHTML;
  
  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Logging in...';
    
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({
        username: form.username.value,
        password: form.password.value
      })
    });
    
    if (!response.ok) {
      throw new Error('Login failed');
    }
    
    const { access_token, username } = await response.json();
    authToken = access_token;
    // Store token in localStorage
    localStorage.setItem('authToken', access_token);
    localStorage.setItem('username', username);
    
    // Redirect to dashboard - cookies will be handled automatically
    window.location.href = '/dashboard';
    
  } catch (error) {
    console.error('Login error:', error);
    document.getElementById('login-error').textContent = error.message || 'Login failed. Please try again.';
    document.getElementById('login-error').classList.remove('hidden');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }
}

async function fetchAndDisplayBalances() {
  const container = document.getElementById('account-balances');
  if (!container) return;
  try {
    const data = await fetchData('/api/account-balance');
    console.log('Account balance data:', data);
    if (!data || data.error) {
      container.innerHTML = '<p class="text-red-500">Failed to load balances.</p>';
      return;
    }
    container.innerHTML = '';
    for (const [asset, amount] of Object.entries(data)) {
      container.innerHTML += `<div>${asset}: ${amount}</div>`;
    }
  } catch (error) {
    console.error('Error fetching balances:', error);
    container.innerHTML = '<p class="text-red-500">Error loading balances.</p>';
  }
}

// Load news feed
async function loadNewsFeed() {
  const newsFeed = document.getElementById('news-feed');
  if (!newsFeed) return;
  try {
    const news = await fetchData('/api/get-news');
    if (!news || news.length === 0) return;
    newsFeed.innerHTML = '';
    news.forEach(item => {
      const newsItem = document.createElement('div');
      newsItem.className = 'bg-gray-800 p-4 rounded-lg shadow-lg';
      newsItem.innerHTML = `
<h3 class="text-lg font-bold mb-2">${item.title}</h3>
<p class="text-gray-400 mb-2">${item.summary}</p>
<div class="flex justify-between text-sm text-gray-500">
<span>${item.source}</span>
<span>${timeAgo(item.date)}</span>
</div>`;
      newsFeed.appendChild(newsItem);
    });
  } catch (error) {
    console.error('Error loading news feed:', error);
  }
}

// Run backtest function
async function runBacktest(formData) {
  try {
    const response = await fetch('/api/backtest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({
        strategy_id: formData.strategy_id,
        symbol: formData.symbol,
        timeframe: formData.timeframe,
        start_date: formData.start_date,
        end_date: formData.end_date,
        initial_capital: parseFloat(formData.initial_capital),
        // Include optional risk parameters, converting to float and providing defaults if empty
        risk_per_trade_pct: formData.risk_per_trade_pct ? parseFloat(formData.risk_per_trade_pct) : undefined, // Send undefined if empty, backend uses default
        max_drawdown_pct: formData.max_drawdown_pct ? parseFloat(formData.max_drawdown_pct) : undefined, // Send undefined if empty, backend uses default
        position_size_pct: formData.position_size_pct ? parseFloat(formData.position_size_pct) : undefined, // Send undefined if empty, backend uses default
        // Note: Strategy-specific parameters might still be needed depending on how StrategyFactory works
        // If the backend StrategyFactory needs them passed explicitly, uncomment and adjust:
        // parameters: {
        //   lookback_period: formData.lookback_period,
        //   volatility_multiplier: formData.volatility_multiplier,
        //   reset_threshold: formData.reset_threshold,
        //   take_profit: formData.take_profit,
        //   stop_loss: formData.stop_loss
        // }
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      // Use the detailed error message from the backend if available
      throw new Error(errorData.error?.message || `HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error running backtest:', error);
    throw error;
  }
}

// Load trades
async function loadTrades() {
  const tradeList = document.getElementById('trade-list');
  if (!tradeList) return;
  try {
    const trades = await fetchData('/api/trades?limit=5');
    if (!trades || trades.length === 0) return;
    tradeList.innerHTML = '';
    trades.forEach(trade => {
      const tradeRow = document.createElement('tr');
      tradeRow.innerHTML = `
<td class="px-6 py-4 whitespace-nowrap"><span class="${trade.trade_type === 'buy' ? 'text-green-500' : 'text-red-500'}">${trade.trade_type.charAt(0).toUpperCase() + trade.trade_type.slice(1)}</span></td>
<td class="px-6 py-4 whitespace-nowrap">${formatCurrency(trade.price)}</td>
<td class="px-6 py-4 whitespace-nowrap">${trade.amount} ${trade.symbol.split('/')[0]}</td>
<td class="px-6 py-4 whitespace-nowrap text-gray-400">${timeAgo(trade.timestamp)}</td>`;
      tradeList.appendChild(tradeRow);
    });
  } catch (error) {
    console.error('Error loading trades:', error);
  }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Check if we're on login page
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
    return;
  }

  // Initialize auth UI
  const loginBtn = document.getElementById('login-btn');
  const logoutBtn = document.getElementById('logout-btn');
  const userInfo = document.getElementById('user-info');
  const loginModal = document.getElementById('login-modal');
  const cancelLogin = document.getElementById('cancel-login');

  if (loginBtn && logoutBtn && userInfo) {
    // Show/hide auth state
    if (authToken) {
      loginBtn.classList.add('hidden');
      userInfo.classList.remove('hidden');
      const username = localStorage.getItem('username') || 'User';
      document.getElementById('username-display').textContent = username;
    } else {
      loginBtn.classList.remove('hidden');
      userInfo.classList.add('hidden');
    }

    // Login button handler
    loginBtn.addEventListener('click', () => {
      loginModal.classList.remove('hidden');
    });

    // Cancel login handler
    cancelLogin.addEventListener('click', () => {
      loginModal.classList.add('hidden');
    });

    // Logout button handler
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('authToken');
      authToken = '';
      window.location.href = '/';
    });
  }

  // If no token and not on login page, redirect
  if (!authToken && window.location.pathname !== '/') {
    window.location.href = '/';
    return;
  }

  loadNewsFeed();
  loadTrades();
  fetchAndDisplayBalances();
  fetchPortfolioSummary();
  fetchOpenPositions();

  // Initialize auth state
  checkAuthStatus();

  const backtestBtn = document.getElementById('backtest-btn');
  if (backtestBtn) {
    backtestBtn.addEventListener('click', async function(e) {
      if (!checkAuthStatus()) {
        return;
      }
      e.preventDefault();
      const originalText = backtestBtn.innerHTML;
      backtestBtn.disabled = true;
      backtestBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Running...';

      try {
        const formData = {
          strategy_id: document.getElementById('strategy-select').value,
          symbol: 'BTC/USDT',
          timeframe: '1h',
          start_date: document.getElementById('start-date').value,
          end_date: document.getElementById('end-date').value,
          initial_capital: 10000,
          lookback_period: parseInt(document.getElementById('lookback-period').value),
          volatility_multiplier: parseFloat(document.getElementById('volatility-multiplier').value),
          reset_threshold: 0.5,
          take_profit: parseFloat(document.getElementById('takeProfitPct').value),
          stop_loss: parseFloat(document.getElementById('stopLossPct').value)
        };

        const results = await runBacktest(formData);
        displayBacktestResults(results);
      } catch (error) {
        console.error('Backtest error:', error);
        handleApiError(error);
      } finally {
        backtestBtn.disabled = false;
        backtestBtn.innerHTML = originalText;
      }
    });
  }
  // Live Chart Logic
  let liveChart = null;
  const loadingElement = document.getElementById('chart-loading');
  const errorElement = document.getElementById('chart-error');
  const chartCanvas = document.getElementById('priceChart');

  async function fetchAndRenderLiveChart(symbol = 'BTC/USDT', interval = '5m', limit = 50) {
    try {
      // Show loading state
      loadingElement.classList.remove('hidden');
      errorElement.classList.add('hidden');
      
      const url = `/api/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${limit}`;
      const data = await fetchData(url);
      
      if (!data || !Array.isArray(data)) {
        throw new Error('Invalid OHLCV data received');
      }

      const candleData = data.map(candle => ({
        x: new Date(candle.timestamp),
        o: candle.open,
        h: candle.high,
        l: candle.low,
        c: candle.close
      }));

      renderChart(candleData, symbol);
    } catch (error) {
      console.error('Error fetching chart data:', error);
      errorElement.textContent = 'Failed to load chart data. Please try again.';
      errorElement.classList.remove('hidden');
    } finally {
      loadingElement.classList.add('hidden');
    }
  }

  function renderChart(candleData, symbol) {
    const ctx = chartCanvas.getContext('2d');
    
    if (liveChart) {
      liveChart.destroy();
    }

    liveChart = new Chart(ctx, {
      type: 'candlestick',
      data: {
        datasets: [{
          label: symbol,
          data: candleData,
          color: {
            up: 'rgba(75, 192, 192, 1)',
            down: 'rgba(255, 99, 132, 1)',
            unchanged: 'rgba(110, 110, 110, 1)',
          },
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'minute',
              displayFormats: { minute: 'HH:mm' },
            },
            grid: { color: 'rgba(255, 255, 255, 0.1)' },
            ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.1)' },
            ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          },
        },
        plugins: {
          legend: { labels: { color: 'white' } },
          tooltip: { mode: 'index', intersect: false },
        },
      },
    });
  }

  // Portfolio data functions
  async function fetchPortfolioSummary() {
    try {
      const data = await fetchData('/api/portfolio-summary');
      if (!data) return;
      
      document.getElementById('total-balance').textContent = formatCurrency(data.total_balance);
      document.getElementById('daily-change').textContent = formatPercentage(data.daily_change / 100);
      document.getElementById('win-rate').textContent = formatPercentage(data.win_rate / 100);
    } catch (error) {
      console.error('Error fetching portfolio summary:', error);
    }
  }

  async function fetchOpenPositions() {
    const loadingEl = document.getElementById('positions-loading');
    const errorEl = document.getElementById('positions-error');
    const tableEl = document.getElementById('positions-table');
    
    try {
      loadingEl.classList.remove('hidden');
      errorEl.classList.add('hidden');
      tableEl.classList.add('hidden');
      
      const positions = await fetchData('/api/open-positions');
      if (!positions || positions.length === 0) {
        document.getElementById('open-positions').textContent = '0';
        return;
      }

      document.getElementById('open-positions').textContent = positions.length.toString();
      const tbody = document.getElementById('positions-body');
      tbody.innerHTML = '';
      
      positions.forEach(pos => {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-700';
        row.innerHTML = `
          <td class="py-3">${pos.symbol}</td>
          <td class="py-3">${pos.size}</td>
          <td class="py-3">${formatCurrency(pos.entry_price)}</td>
          <td class="py-3 ${pos.pnl >= 0 ? 'text-green-500' : 'text-red-500'}">
            ${formatCurrency(pos.pnl)} (${formatPercentage(pos.pnl_pct / 100)})
          </td>
        `;
        tbody.appendChild(row);
      });
      
      tableEl.classList.remove('hidden');
    } catch (error) {
      console.error('Error fetching positions:', error);
      errorEl.textContent = 'Failed to load positions. Please try again.';
      errorEl.classList.remove('hidden');
    } finally {
      loadingEl.classList.add('hidden');
    }
  }

  // Initial load
  fetchAndRenderLiveChart();
  setInterval(fetchAndRenderLiveChart, 30000); // Refresh every 30 seconds

  // Timeframe button handlers
  document.querySelectorAll('[data-timeframe]').forEach(btn => {
    btn.addEventListener('click', () => {
      fetchAndRenderLiveChart('BTC/USDT', btn.dataset.timeframe);
    });
  });

  // Password Reset Handlers
  const requestResetForm = document.getElementById('request-reset-form');
  if (requestResetForm) {
    requestResetForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = requestResetForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.innerHTML;
      
      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Sending...';
        
        const email = document.getElementById('reset-email').value;
        const response = await fetch('/auth/request-reset', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        showAlert(data.message, 'success');
      } catch (error) {
        showAlert('Error requesting password reset', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }

  const resetPasswordForm = document.getElementById('reset-password-form');
  if (resetPasswordForm) {
    resetPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = resetPasswordForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.innerHTML;
      
      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Updating...';
        
        const token = document.getElementById('reset-token').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        
        if (newPassword !== confirmPassword) {
          throw new Error('Passwords do not match');
        }
        
        const response = await fetch('/auth/reset-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token,
            new_password: newPassword
          })
        });
        
        const data = await response.json();
        showAlert(data.message, 'success');
        if (response.ok) {
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
        }
      } catch (error) {
        showAlert(error.message || 'Error resetting password', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }

  // Strategy form handlers
  const strategyForm = document.getElementById('strategy-form');
  if (strategyForm) {
    // Update slider value displays
    document.getElementById('risk-percent').addEventListener('input', (e) => {
      document.getElementById('risk-value').textContent = `${e.target.value}%`;
    });
    document.getElementById('take-profit').addEventListener('input', (e) => {
      document.getElementById('tp-value').textContent = `${e.target.value}%`;
    });
    document.getElementById('stop-loss').addEventListener('input', (e) => {
      document.getElementById('sl-value').textContent = `${e.target.value}%`;
    });

    // Handle form submission
    strategyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = strategyForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.innerHTML;
      const errorEl = document.getElementById('strategy-error');
      
      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Updating...';
        errorEl.classList.add('hidden');

        const response = await fetch('/api/update-strategy', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({
            strategy: strategyForm.strategy.value,
            risk_percent: parseFloat(strategyForm.risk.value),
            take_profit: parseFloat(strategyForm.take_profit.value),
            stop_loss: parseFloat(strategyForm.stop_loss.value)
          })
        });

        if (!response.ok) {
          throw new Error('Failed to update strategy');
        }

        const result = await response.json();
        console.log('Strategy updated:', result);
      } catch (error) {
        console.error('Error updating strategy:', error);
        errorEl.textContent = 'Failed to update strategy. Please try again.';
        errorEl.classList.remove('hidden');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }
});

// Check authentication status
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const authState = document.getElementById('auth-state');
    const backtestForm = document.getElementById('backtest-form');
    
    if (!token) {
        authState.classList.remove('hidden');
        document.getElementById('login-prompt').classList.remove('hidden');
        backtestForm.classList.add('hidden');
        console.log('No auth token found');
        return false;
    }

    // Check token expiration
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp < Date.now() / 1000) {
            console.log('Token expired');
            localStorage.removeItem('authToken');
            authState.classList.remove('hidden');
            document.getElementById('login-prompt').classList.remove('hidden');
            backtestForm.classList.add('hidden');
            return false;
        }
    } catch (e) {
        console.error('Invalid token:', e);
        return false;
    }

    authState.classList.add('hidden');
    return true;
    backtestForm.classList.remove('hidden');
    return true;
}

// Handle API errors
function handleApiError(error) {
    if (error.status === 401) {
        document.getElementById('auth-state').classList.remove('hidden');
        document.getElementById('auth-error').classList.remove('hidden');
        document.getElementById('login-prompt').classList.add('hidden');
        document.getElementById('backtest-form').classList.add('hidden');
    }
    console.error('API Error:', error);
}

// Display backtest results
function displayBacktestResults(results) {
  // Update metrics
  document.getElementById('return-pct').textContent = formatPercentage(results.return_pct / 100);
  document.getElementById('sharpe-ratio').textContent = results.sharpe_ratio.toFixed(2);
  document.getElementById('sortino-ratio').textContent = results.sortino_ratio.toFixed(2);
  document.getElementById('calmar-ratio').textContent = results.calmar_ratio.toFixed(2);
  document.getElementById('max-drawdown').textContent = formatPercentage(results.max_drawdown / 100);
  document.getElementById('profit-factor').textContent = results.profit_factor.toFixed(2);
  document.getElementById('volatility').textContent = formatPercentage(results.volatility / 100);
  document.getElementById('win-rate').textContent = formatPercentage(results.win_rate / 100);
  document.getElementById('avg-win').textContent = formatPercentage(results.avg_win_pct / 100);
  document.getElementById('avg-loss').textContent = formatPercentage(results.avg_loss_pct / 100);

  // Update equity curve chart
  updateBacktestChart(results.equity_curve, results.trades);
  
  // Create drawdown visualization if we have equity curve data
  if (results.equity_curve && results.equity_curve.length > 0) {
    const equityValues = results.equity_curve.map(point => point.equity);
    const timestamps = results.equity_curve.map(point => point.timestamp);
    
    // Create drawdown chart
    const drawdownResult = window.drawdownVisualization.createDrawdownChart(
      'drawdown-chart', 
      equityValues, 
      timestamps
    );
    
    // Update drawdown metrics table
    if (drawdownResult && drawdownResult.drawdownPeriods) {
      window.drawdownVisualization.updateDrawdownMetricsTable(
        'drawdown-table',
        drawdownResult.drawdownPeriods
      );
    }
  }
}

// Update backtest chart with results
function updateBacktestChart(equityCurve, trades) {
  const ctx = document.getElementById('backtest-chart').getContext('2d');
  
  // Format data for Chart.js
  const labels = equityCurve.map(point => new Date(point.timestamp));
  const equityData = equityCurve.map(point => point.equity);
  
  // Create trade markers
  const tradePoints = trades.map(trade => ({
    x: new Date(trade.exit_time || trade.entry_time),
    y: trade.exit_value || trade.entry_value,
    type: trade.type,
    pnl: trade.pnl
  }));

  if (window.backtestChart) {
    window.backtestChart.destroy();
  }

  window.backtestChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Equity Curve',
          data: equityData,
          borderColor: 'rgba(59, 130, 246, 0.8)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          tension: 0.1,
          fill: true
        },
        {
          label: 'Buy Trades',
          data: tradePoints.filter(t => t.type === 'buy'),
          backgroundColor: 'rgba(16, 185, 129, 0.8)',
          borderColor: 'rgba(16, 185, 129, 1)',
          pointRadius: 6,
          pointHoverRadius: 8,
          showLine: false
        },
        {
          label: 'Sell Trades',
          data: tradePoints.filter(t => t.type === 'sell'),
          backgroundColor: 'rgba(239, 68, 68, 0.8)',
          borderColor: 'rgba(239, 68, 68, 1)',
          pointRadius: 6,
          pointHoverRadius: 8,
          showLine: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: 'rgba(255, 255, 255, 0.8)',
            font: {
              size: 12
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              if (context.datasetIndex === 0) {
                return 'Equity: ' + formatCurrency(context.raw);
              }
              return `${context.dataset.label}: ${formatCurrency(context.raw)} (${formatPercentage(context.raw.pnl/100)})`;
            }
          }
        }
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'day',
            displayFormats: {
              day: 'MMM d'
            }
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)'
          }
        },
        y: {
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)',
            callback: function(value) {
              return formatCurrency(value);
            }
          }
        }
      }
    }
  });
}
function displayBacktestResults(results) {
  const resultsContainer = document.getElementById('backtest-results');
  if (!resultsContainer) return;
  resultsContainer.classList.remove('hidden');

  // Update key metrics
  document.getElementById('return-pct').textContent = formatPercentage(results.return_pct);
  document.getElementById('sharpe-ratio').textContent = results.sharpe_ratio.toFixed(2);
  document.getElementById('max-drawdown').textContent = formatPercentage(results.max_drawdown);
  document.getElementById('profit-factor').textContent = results.profit_factor.toFixed(2);
  document.getElementById('win-rate').textContent = formatPercentage(results.win_rate);
  document.getElementById('avg-win').textContent = formatPercentage(results.avg_win);
  document.getElementById('avg-loss').textContent = formatPercentage(results.avg_loss);

  const summary = document.getElementById('backtest-summary');
  if (summary) {
    summary.innerHTML = `
<div>Initial Capital<br><strong>${formatCurrency(results.initial_capital)}</strong></div>
<div>Final Capital<br><strong>${formatCurrency(results.final_capital)}</strong></div>
<div>Return<br><strong>${formatPercentage(results.return_pct)}</strong></div>
<div>Total Trades<br><strong>${results.total_trades}</strong></div>
<div>Win Rate<br><strong>${formatPercentage(results.win_rate)}</strong></div>
<div>Timeframe<br><strong>${results.timeframe}</strong></div>
<div>Start Date<br><strong>${results.start_date}</strong></div>
<div>End Date<br><strong>${results.end_date}</strong></div>`;
  }

  const tradesTable = document.getElementById('backtest-trades');
  if (tradesTable && results.trades && results.trades.length > 0) {
    const tbody = tradesTable.querySelector('tbody');
    tbody.innerHTML = '';
    results.trades.forEach(trade => {
      const row = document.createElement('tr');
      row.innerHTML = `
<td>${trade.trade_type.charAt(0).toUpperCase() + trade.trade_type.slice(1)}</td>
<td>${formatCurrency(trade.price)}</td>
<td>${trade.amount}</td>
<td>${trade.timestamp}</td>
<td>${formatPercentage(trade.profit_loss * 100)}</td>`;
      tbody.appendChild(row);
    });
  }

  if (results.status === 401) {
    showToast(
      'Your session has expired. <button onclick="window.location.href=\'/login\'" class="ml-2 px-2 py-1 bg-blue-600 rounded hover:bg-blue-700">Log In</button>',
      'error',
      5000
    );
    // Clear all auth state
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    document.cookie = 'access_token_cookie=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    authToken = '';
    return;
  }

  updateBacktestChart(results);
}

// Function to update the backtest chart
function updateBacktestChart(results) {
  const chartCanvas = document.getElementById('backtest-chart');
  if (!chartCanvas) return;

  let backtestChart = Chart.getChart(chartCanvas);
  if (backtestChart) backtestChart.destroy();

  const priceData = results.price_data;
  if (!priceData || !priceData.timestamps) return;

  const ctx = chartCanvas.getContext('2d');
  const candlestickData = [];
  const equityCurveData = [];
  let currentEquity = results.initial_capital;
  
  for (let i = 0; i < priceData.timestamps.length; i++) {
    candlestickData.push({
      x: new Date(priceData.timestamps[i]),
      o: priceData.open[i],
      h: priceData.high[i],
      l: priceData.low[i],
      c: priceData.close[i]
    });
    
    // Update equity curve
    const trade = results.trades.find(t =>
      new Date(t.timestamp).getTime() === new Date(priceData.timestamps[i]).getTime()
    );
    if (trade) {
      currentEquity += trade.profit_loss;
    }
    equityCurveData.push({
      x: new Date(priceData.timestamps[i]),
      y: currentEquity
    });
  }

  const upperBandData = [];
  const middleBandData = [];
  const lowerBandData = [];
  for (let i = 0; i < priceData.timestamps.length; i++) {
    if (priceData.upper_band && priceData.upper_band[i] !== null) {
      upperBandData.push({ x: new Date(priceData.timestamps[i]), y: priceData.upper_band[i] });
    }
    if (priceData.middle_band && priceData.middle_band[i] !== null) {
      middleBandData.push({ x: new Date(priceData.timestamps[i]), y: priceData.middle_band[i] });
    }
    if (priceData.lower_band && priceData.lower_band[i] !== null) {
      lowerBandData.push({ x: new Date(priceData.timestamps[i]), y: priceData.lower_band[i] });
    }
  }

  const buyMarkers = [];
  const sellMarkers = [];
  results.trades.forEach(trade => {
    const tradeTime = new Date(trade.timestamp);
    let closestIndex = 0;
    let minTimeDiff = Infinity;
    for (let i = 0; i < priceData.timestamps.length; i++) {
      const timeDiff = Math.abs(new Date(priceData.timestamps[i]) - tradeTime);
      if (timeDiff < minTimeDiff) {
        minTimeDiff = timeDiff;
        closestIndex = i;
      }
    }
    if (trade.trade_type === 'buy') {
      buyMarkers.push({ x: new Date(priceData.timestamps[closestIndex]), y: priceData.low[closestIndex] * 0.999 });
    } else {
      sellMarkers.push({ x: new Date(priceData.timestamps[closestIndex]), y: priceData.high[closestIndex] * 1.001 });
    }
  });

  backtestChart = new Chart(ctx, {
    type: 'candlestick',
    data: {
      datasets: [{
        label: results.symbol,
        data: candlestickData,
        color: {
          up: 'rgba(75, 192, 192, 1)',
          down: 'rgba(255, 99, 132, 1)',
          unchanged: 'rgba(110, 110, 110, 1)',
        },
        yAxisID: 'y'
      }, {
        label: 'Equity Curve',
        data: equityCurveData,
        type: 'line',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: 'y1'
      }, {
        label: 'Upper Band',
        data: upperBandData,
        type: 'line',
        pointRadius: 0,
        borderColor: 'rgba(255, 159, 64, 1)',
        borderWidth: 2,
        fill: false
      }, {
        label: 'Middle Band',
        data: middleBandData,
        type: 'line',
        pointRadius: 0,
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 2,
        fill: false
      }, {
        label: 'Lower Band',
        data: lowerBandData,
        type: 'line',
        pointRadius: 0,
        borderColor: 'rgba(255, 159, 64, 1)',
        borderWidth: 2,
        fill: false
      }, {
        label: 'Buy Signals',
        data: buyMarkers,
        type: 'scatter',
        pointRadius: 6,
        pointStyle: 'triangle',
        backgroundColor: 'rgba(75, 192, 192, 1)',
        borderColor: 'rgba(75, 192, 192, 1)',
        rotation: 180
      }, {
        label: 'Sell Signals',
        data: sellMarkers,
        type: 'scatter',
        pointRadius: 6,
        pointStyle: 'triangle',
        backgroundColor: 'rgba(255, 99, 132, 1)',
        borderColor: 'rgba(255, 99, 132, 1)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'minute',
            displayFormats: { minute: 'HH:mm' }
          },
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: 'rgba(255, 255, 255, 0.7)' }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          position: 'left'
        },
        y1: {
          grid: { display: false },
          ticks: {
            color: 'rgba(54, 162, 235, 1)',
            callback: function(value) {
              return formatCurrency(value);
            }
          },
          position: 'right'
        }
      },
      plugins: {
        legend: { labels: { color: 'white' } },
        tooltip: { mode: 'index', intersect: false }
      }
    }
  });
}