/**
 * Token Usage Monitoring Dashboard
 * 
 * This script provides functionality for the token usage monitoring dashboard.
 * It fetches token usage data, updates dashboard metrics, creates charts,
 * displays alerts when approaching token limits, and provides optimization recommendations.
 */

// Configuration
const CONFIG = {
    tokenBudget: 76659,
    warningThreshold: 0.7,  // 70% of token budget
    dangerThreshold: 0.9,   // 90% of token budget
    refreshInterval: 60000, // Refresh data every minute
    predictionDays: 7,      // Days to predict into the future
    earlyWarningDays: 3,    // Days before predicted threshold crossing to warn
    predictionThreshold: 0.85 // 85% of budget for prediction warnings
};

// State management
let dashboardState = {
    currentTokens: 0,
    tokenHistory: [],
    compressionRatio: 0,
    processingRate: 0,
    tokenEfficiency: 0,
    recentLogs: [],
    alerts: [],
    predictions: {
        nextRun: 0,
        sevenDay: 0,
        thirtyDay: 0,
        trendingUp: false,
        predictedCrossingDate: null,
        daysUntilCrossing: null
    }
};

// Initialize charts
let historyChart = null;
let gaugeChart = null;
let predictionChart = null;

// DOM elements
const elements = {
    currentTokens: document.getElementById('currentTokens'),
    tokenTrend: document.getElementById('tokenTrend'),
    tokenProgressBar: document.getElementById('tokenProgressBar'),
    tokenBudgetText: document.getElementById('tokenBudgetText'),
    compressionRatio: document.getElementById('compressionRatio'),
    compressionTrend: document.getElementById('compressionTrend'),
    processingRate: document.getElementById('processingRate'),
    tokenEfficiency: document.getElementById('tokenEfficiency'),
    historyChart: document.getElementById('historyChart'),
    gaugeChart: document.getElementById('gaugeChart'),
    alertCard: document.getElementById('alertCard'),
    alertTitle: document.getElementById('alertTitle'),
    alertLevel: document.getElementById('alertLevel'),
    alertMessage: document.getElementById('alertMessage'),
    optimizationList: document.getElementById('optimizationList'),
    logsTableBody: document.getElementById('logsTableBody'),
    refreshBtn: document.getElementById('refreshBtn'),
    predictionChart: document.getElementById('predictionChart'),
    predictiveAlertCard: document.getElementById('predictiveAlertCard'),
    predictiveAlertTitle: document.getElementById('predictiveAlertTitle'),
    predictiveAlertLevel: document.getElementById('predictiveAlertLevel'),
    predictiveAlertMessage: document.getElementById('predictiveAlertMessage'),
    crossingDateDisplay: document.getElementById('crossingDateDisplay'),
    daysRemainingDisplay: document.getElementById('daysRemainingDisplay')
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    fetchData();
    
    // Set up refresh button
    elements.refreshBtn.addEventListener('click', fetchData);
    
    // Set up auto-refresh
    setInterval(fetchData, CONFIG.refreshInterval);
});

/**
 * Fetch token usage data from the server
 */
async function fetchData() {
    try {
        // In a real implementation, this would make an API call
        // For demo purposes, we're generating sample data
        const data = await generateSampleData();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching data:', error);
        showAlert('Data Fetch Error', 'An error occurred while fetching token usage data.', 'danger');
    }
}

/**
 * Generate sample data for demonstration
 * In a real implementation, this would be replaced with actual API calls
 */
async function generateSampleData() {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Generate random token usage (between 30% and 95% of budget)
    const currentTokens = Math.floor(Math.random() * (CONFIG.tokenBudget * 0.65) + (CONFIG.tokenBudget * 0.3));
    
    // Generate history data (30 days)
    const tokenHistory = [];
    const today = new Date();
    
    for (let i = 30; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        
        // Generate a value between 30% and current usage
        const minValue = CONFIG.tokenBudget * 0.3;
        const maxValue = currentTokens;
        const variance = (maxValue - minValue) / 2;
        let value = Math.floor(Math.random() * variance + minValue);
        
        // Ensure an upward trend
        if (i < 5) {
            // Last 5 days trending toward current value
            value = Math.floor((maxValue - value) * ((5 - i) / 5) + value);
        }
        
        tokenHistory.push({
            date: date.toISOString().split('T')[0],
            tokens: value
        });
    }
    
    // Generate sample compression ratio (between 50% and 85%)
    const compressionRatio = Math.random() * 0.35 + 0.5;
    
    // Generate sample processing rate (between 1000 and 5000 lines/second)
    const processingRate = Math.floor(Math.random() * 4000 + 1000);
    
    // Generate sample token efficiency (between 0.5 and 3 lines/token)
    const tokenEfficiency = Math.random() * 2.5 + 0.5;
    
    // Generate sample recent logs
    const recentLogs = [];
    for (let i = 0; i < 5; i++) {
        const date = new Date(today);
        date.setHours(date.getHours() - i);
        
        const logTokens = Math.floor(Math.random() * 50000 + 10000);
        const logCompression = Math.random() * 0.3 + 0.5;
        
        recentLogs.push({
            timestamp: date.toISOString(),
            logFile: `test_output_${i}.log`,
            tokens: logTokens,
            compression: logCompression
        });
    }
    
    // Determine if alerts should be shown based on token usage
    const tokenPercentage = currentTokens / CONFIG.tokenBudget;
    const alerts = [];
    
    if (tokenPercentage >= CONFIG.dangerThreshold) {
        alerts.push({
            title: 'Critical Token Usage',
            message: `Current token usage (${Math.round(tokenPercentage * 100)}%) has exceeded the danger threshold (${CONFIG.dangerThreshold * 100}%). Immediate action is required to prevent exceeding token limits.`,
            level: 'danger'
        });
    } else if (tokenPercentage >= CONFIG.warningThreshold) {
        alerts.push({
            title: 'High Token Usage',
            message: `Current token usage (${Math.round(tokenPercentage * 100)}%) has exceeded the warning threshold (${CONFIG.warningThreshold * 100}%). Consider implementing optimizations to reduce token usage.`,
            level: 'warning'
        });
    }
    
    // Generate predictive data
    const predictions = generatePredictions(tokenHistory);
    
    // Return the sample data
    return {
        currentTokens,
        tokenHistory,
        compressionRatio,
        processingRate,
        tokenEfficiency,
        recentLogs,
        alerts,
        predictions
    };
}

/**
 * Generate token usage predictions based on historical data
 * Uses linear regression to predict future token usage
 */
function generatePredictions(tokenHistory) {
    // Get the last 14 days of data for prediction
    const recentHistory = tokenHistory.slice(-14);
    
    // Calculate linear regression
    const xValues = recentHistory.map((_, index) => index);
    const yValues = recentHistory.map(entry => entry.tokens);
    
    const n = xValues.length;
    
    // Calculate means
    const meanX = xValues.reduce((sum, x) => sum + x, 0) / n;
    const meanY = yValues.reduce((sum, y) => sum + y, 0) / n;
    
    // Calculate slope and y-intercept
    let numerator = 0;
    let denominator = 0;
    
    for (let i = 0; i < n; i++) {
        numerator += (xValues[i] - meanX) * (yValues[i] - meanY);
        denominator += (xValues[i] - meanX) ** 2;
    }
    
    const slope = numerator / denominator;
    const yIntercept = meanY - slope * meanX;
    
    // Calculate next run prediction (1 day ahead)
    const nextRun = Math.round(yIntercept + slope * n);
    
    // Calculate 7 day prediction
    const sevenDay = Math.round(yIntercept + slope * (n + 7));
    
    // Calculate 30 day prediction
    const thirtyDay = Math.round(yIntercept + slope * (n + 30));
    
    // Determine if trend is increasing
    const trendingUp = slope > 0;
    
    // Calculate days until crossing prediction threshold
    let daysUntilCrossing = null;
    let predictedCrossingDate = null;
    
    if (trendingUp && nextRun < CONFIG.tokenBudget * CONFIG.predictionThreshold) {
        // Calculate how many days until we hit the prediction threshold
        const daysToThreshold = Math.ceil(
            (CONFIG.tokenBudget * CONFIG.predictionThreshold - yIntercept) / slope - n
        );
        
        if (daysToThreshold > 0 && daysToThreshold < 60) { // Only predict up to 60 days ahead
            daysUntilCrossing = daysToThreshold;
            
            const crossingDate = new Date();
            crossingDate.setDate(crossingDate.getDate() + daysToThreshold);
            predictedCrossingDate = crossingDate.toISOString().split('T')[0];
        }
    }
    
    return {
        nextRun,
        sevenDay,
        thirtyDay,
        trendingUp,
        predictedCrossingDate,
        daysUntilCrossing,
        slope,
        yIntercept
    };
}

/**
 * Update the dashboard with new data
 */
function updateDashboard(data) {
    // Update state
    dashboardState = data;
    
    // Update metric cards
    updateMetricCards();
    
    // Update charts
    updateCharts();
    
    // Update alerts
    updateAlerts();
    
    // Update predictive alerts
    updatePredictiveAlerts();
    
    // Update optimization suggestions
    updateOptimizationSuggestions();
    
    // Update recent logs table
    updateRecentLogs();
}

/**
 * Update the metric cards with current data
 */
function updateMetricCards() {
    // Format numbers
    const formatter = new Intl.NumberFormat('en-US');
    
    // Calculate token percentage
    const tokenPercentage = dashboardState.currentTokens / CONFIG.tokenBudget;
    
    // Update current tokens
    elements.currentTokens.textContent = formatter.format(dashboardState.currentTokens);
    
    // Generate random trend percentage between -5% and +15%
    const trendPercentage = (Math.random() * 20 - 5).toFixed(1);
    const trendIsPositive = parseFloat(trendPercentage) >= 0;
    
    elements.tokenTrend.textContent = `${trendIsPositive ? '+' : ''}${trendPercentage}% from last run`;
    elements.tokenTrend.className = `percentage ${trendIsPositive ? 'increase' : 'decrease'}`;
    
    // Update token progress bar
    elements.tokenProgressBar.style.width = `${tokenPercentage * 100}%`;
    
    // Update progress bar color based on thresholds
    if (tokenPercentage >= CONFIG.dangerThreshold) {
        elements.tokenProgressBar.className = 'progress-bar danger';
    } else if (tokenPercentage >= CONFIG.warningThreshold) {
        elements.tokenProgressBar.className = 'progress-bar warning';
    } else {
        elements.tokenProgressBar.className = 'progress-bar';
    }
    
    // Update token budget text
    elements.tokenBudgetText.textContent = `${formatter.format(dashboardState.currentTokens)} / ${formatter.format(CONFIG.tokenBudget)} tokens (${(tokenPercentage * 100).toFixed(1)}%)`;
    
    // Update compression ratio
    elements.compressionRatio.textContent = `${(dashboardState.compressionRatio * 100).toFixed(1)}%`;
    
    // Generate random trend percentage between -2% and +10%
    const compressionTrendPercentage = (Math.random() * 12 - 2).toFixed(1);
    const compressionTrendIsPositive = parseFloat(compressionTrendPercentage) >= 0;
    
    elements.compressionTrend.textContent = `${compressionTrendIsPositive ? '+' : ''}${compressionTrendPercentage}% from average`;
    elements.compressionTrend.className = `percentage ${compressionTrendIsPositive ? 'increase' : 'decrease'}`;
    
    // Update processing rate
    elements.processingRate.textContent = formatter.format(dashboardState.processingRate);
    
    // Update token efficiency
    elements.tokenEfficiency.textContent = dashboardState.tokenEfficiency.toFixed(2);
}

/**
 * Initialize charts
 */
function initializeCharts() {
    // Initialize token history chart
    historyChart = new Chart(elements.historyChart, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Token Usage',
                data: [],
                borderColor: '#4a8cff',
                backgroundColor: 'rgba(74, 140, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: CONFIG.tokenBudget,
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                }
            }
        }
    });
    
    // Initialize gauge chart
    gaugeChart = new Chart(elements.gaugeChart, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Available'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#4a8cff', '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            cutout: '80%',
            circumference: 180,
            rotation: 270,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        }
    });
    
    // Initialize prediction chart if element exists
    if (elements.predictionChart) {
        predictionChart = new Chart(elements.predictionChart, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Historical',
                    data: [],
                    borderColor: '#4a8cff',
                    backgroundColor: 'rgba(74, 140, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Predicted',
                    data: [],
                    borderColor: '#ff7e4a',
                    backgroundColor: 'rgba(255, 126, 74, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: CONFIG.tokenBudget,
                        grid: {
                            color: 'rgba(200, 200, 200, 0.2)'
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update charts with new data
 */
function updateCharts() {
    // Update token history chart
    if (historyChart) {
        const labels = dashboardState.tokenHistory.map(entry => entry.date);
        const data = dashboardState.tokenHistory.map(entry => entry.tokens);
        
        historyChart.data.labels = labels;
        historyChart.data.datasets[0].data = data;
        
        // Add danger threshold line
        historyChart.data.datasets = [
            {
                label: 'Token Usage',
                data: data,
                borderColor: '#4a8cff',
                backgroundColor: 'rgba(74, 140, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            },
            {
                label: 'Danger Threshold',
                data: labels.map(() => CONFIG.tokenBudget * CONFIG.dangerThreshold),
                borderColor: '#ff4a4a',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0
            },
            {
                label: 'Warning Threshold',
                data: labels.map(() => CONFIG.tokenBudget * CONFIG.warningThreshold),
                borderColor: '#ffaa4a',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0
            }
        ];
        
        historyChart.update();
    }
    
    // Update gauge chart
    if (gaugeChart) {
        const percentageUsed = dashboardState.currentTokens / CONFIG.tokenBudget * 100;
        const percentageRemaining = 100 - percentageUsed;
        
        gaugeChart.data.datasets[0].data = [percentageUsed, percentageRemaining];
        
        // Update color based on thresholds
        if (percentageUsed >= CONFIG.dangerThreshold * 100) {
            gaugeChart.data.datasets[0].backgroundColor[0] = '#ff4a4a'; // Danger color
        } else if (percentageUsed >= CONFIG.warningThreshold * 100) {
            gaugeChart.data.datasets[0].backgroundColor[0] = '#ffaa4a'; // Warning color
        } else {
            gaugeChart.data.datasets[0].backgroundColor[0] = '#4a8cff'; // Primary color
        }
        
        gaugeChart.update();
        
        // Add percentage text in the middle of the gauge
        const ctx = elements.gaugeChart.getContext('2d');
        const centerX = elements.gaugeChart.width / 2;
        const centerY = elements.gaugeChart.height / 2 + elements.gaugeChart.height * 0.1; // Adjust for semi-circle
        
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 24px Arial';
        ctx.fillStyle = '#333';
        ctx.fillText(`${Math.round(percentageUsed)}%`, centerX, centerY);
        
        ctx.font = '14px Arial';
        ctx.fillStyle = '#777';
        ctx.fillText('used', centerX, centerY + 25);
        ctx.restore();
    }
    
    // Update prediction chart
    if (predictionChart && dashboardState.predictions) {
        const historyData = dashboardState.tokenHistory.slice(-7); // Last 7 days
        const historyLabels = historyData.map(entry => entry.date);
        const historyValues = historyData.map(entry => entry.tokens);
        
        // Generate prediction labels (next 7 days)
        const predictionLabels = [];
        const today = new Date();
        
        for (let i = 1; i <= CONFIG.predictionDays; i++) {
            const futureDate = new Date(today);
            futureDate.setDate(futureDate.getDate() + i);
            predictionLabels.push(futureDate.toISOString().split('T')[0]);
        }
        
        // Generate prediction values
        const predictionValues = [];
        const {slope, yIntercept} = dashboardState.predictions;
        const n = historyData.length;
        
        for (let i = 1; i <= CONFIG.predictionDays; i++) {
            predictionValues.push(Math.round(yIntercept + slope * (n + i)));
        }
        
        // Combine labels
        const combinedLabels = [...historyLabels, ...predictionLabels];
        
        // Create datasets with null values for connecting
        const historySeries = [...historyValues, null, ...Array(CONFIG.predictionDays - 1).fill(null)];
        
        // Connect with first prediction point
        const predictionSeries = [...Array(historyLabels.length - 1).fill(null), historyValues[historyValues.length - 1], ...predictionValues];
        
        // Update chart
        predictionChart.data.labels = combinedLabels;
        predictionChart.data.datasets[0].data = historySeries;
        predictionChart.data.datasets[1].data = predictionSeries;
        
        // Add threshold lines
        predictionChart.data.datasets = [
            {
                label: 'Historical',
                data: historySeries,
                borderColor: '#4a8cff',
                backgroundColor: 'rgba(74, 140, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            },
            {
                label: 'Predicted',
                data: predictionSeries,
                borderColor: '#ff7e4a',
                backgroundColor: 'rgba(255, 126, 74, 0.1)',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: true,
                tension: 0.4
            },
            {
                label: 'Prediction Threshold',
                data: combinedLabels.map(() => CONFIG.tokenBudget * CONFIG.predictionThreshold),
                borderColor: '#ff4a4a',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0
            }
        ];
        
        predictionChart.update();
    }
}

/**
 * Update alerts based on current token usage
 */
function updateAlerts() {
    if (dashboardState.alerts && dashboardState.alerts.length > 0) {
        const alert = dashboardState.alerts[0]; // Show the first alert
        
        elements.alertTitle.textContent = alert.title;
        elements.alertMessage.textContent = alert.message;
        elements.alertLevel.textContent = alert.level === 'danger' ? 'Critical' : 'Warning';
        elements.alertLevel.className = `alert-level ${alert.level}`;
        elements.alertCard.style.display = 'block';
    } else {
        elements.alertCard.style.display = 'none';
    }
}

/**
 * Update predictive alerts based on token usage trends
 */
function updatePredictiveAlerts() {
    // Check if elements exist and predictions are available
    if (!elements.predictiveAlertCard || !dashboardState.predictions) {
        return;
    }
    
    const { predictions } = dashboardState;
    const { nextRun, sevenDay, thirtyDay, trendingUp, predictedCrossingDate, daysUntilCrossing } = predictions;
    
    // Default to hidden
    elements.predictiveAlertCard.style.display = 'none';
    
    // Show predictive alert if trending toward threshold
    if (trendingUp && daysUntilCrossing !== null) {
        // Determine alert level
        let level = 'info';
        let title = 'Token Usage Trending Up';
        let message = '';
        
        if (daysUntilCrossing <= CONFIG.earlyWarningDays) {
            level = 'danger';
            title = 'Critical: Imminent Token Limit';
            message = `Token usage is projected to reach ${Math.round(CONFIG.predictionThreshold * 100)}% of budget in ${daysUntilCrossing} day${daysUntilCrossing !== 1 ? 's' : ''}! Immediate action is recommended.`;
        } else if (daysUntilCrossing <= CONFIG.earlyWarningDays * 2) {
            level = 'warning';
            title = 'Warning: Approaching Token Limit';
            message = `Token usage is projected to reach ${Math.round(CONFIG.predictionThreshold * 100)}% of budget by ${predictedCrossingDate} (${daysUntilCrossing} days from now). Consider implementing optimizations.`;
        } else {
            message = `If current trends continue, token usage will reach ${Math.round(CONFIG.predictionThreshold * 100)}% of budget by ${predictedCrossingDate} (${daysUntilCrossing} days from now).`;
        }
        
        // Update predictive alert card
        elements.predictiveAlertTitle.textContent = title;
        elements.predictiveAlertMessage.textContent = message;
        elements.predictiveAlertLevel.textContent = level === 'danger' ? 'Critical' : level === 'warning' ? 'Warning' : 'Info';
        elements.predictiveAlertLevel.className = `alert-level ${level}`;
        elements.predictiveAlertCard.style.display = 'block';
        
        // Update crossing date display if element exists
        if (elements.crossingDateDisplay) {
            elements.crossingDateDisplay.textContent = predictedCrossingDate || 'N/A';
        }
        
        // Update days remaining display if element exists
        if (elements.daysRemainingDisplay) {
            elements.daysRemainingDisplay.textContent = daysUntilCrossing !== null ? daysUntilCrossing : 'N/A';
        }
    } else if (trendingUp && nextRun > CONFIG.tokenBudget * CONFIG.warningThreshold) {
        // Show warning for next run
        elements.predictiveAlertTitle.textContent = 'Next Run Warning';
        elements.predictiveAlertMessage.textContent = `The next run is predicted to use ${Math.round(nextRun / CONFIG.tokenBudget * 100)}% of token budget, which exceeds the warning threshold.`;
        elements.predictiveAlertLevel.textContent = 'Warning';
        elements.predictiveAlertLevel.className = 'alert-level warning';
        elements.predictiveAlertCard.style.display = 'block';
    } else if (trendingUp && sevenDay > CONFIG.tokenBudget * CONFIG.warningThreshold) {
        // Show info for 7-day prediction
        elements.predictiveAlertTitle.textContent = 'Token Usage Trending Up';
        elements.predictiveAlertMessage.textContent = `Token usage is trending upward and projected to reach ${Math.round(sevenDay / CONFIG.tokenBudget * 100)}% of budget within 7 days.`;
        elements.predictiveAlertLevel.textContent = 'Info';
        elements.predictiveAlertLevel.className = 'alert-level info';
        elements.predictiveAlertCard.style.display = 'block';
    }
    
    // If trending downward, show positive message
    if (!trendingUp && elements.predictionTrendStatus) {
        elements.predictionTrendStatus.textContent = 'Token usage is trending downward - good job!';
        elements.predictionTrendStatus.className = 'trend-status positive';
    } else if (elements.predictionTrendStatus) {
        elements.predictionTrendStatus.textContent = 'Token usage is trending upward - monitor closely';
        elements.predictionTrendStatus.className = 'trend-status negative';
    }
}

/**
 * Show an alert message
 */
function showAlert(title, message, level) {
    elements.alertTitle.textContent = title;
    elements.alertMessage.textContent = message;
    elements.alertLevel.textContent = level === 'danger' ? 'Critical' : 'Warning';
    elements.alertLevel.className = `alert-level ${level}`;
    elements.alertCard.style.display = 'block';
}

/**
 * Update optimization suggestions based on token usage
 */
function updateOptimizationSuggestions() {
    // Clear existing suggestions
    elements.optimizationList.innerHTML = '';
    
    // Default optimizations
    const optimizations = [
        {
            title: 'Increase Compression Ratio',
            description: 'Adjust log processing algorithms to achieve higher compression by focusing on the most relevant information.'
        },
        {
            title: 'Optimize Memory Integration',
            description: 'Store error type summaries rather than full traces to reduce memory token usage.'
        },
        {
            title: 'Implement Token Budgeting',
            description: 'Assign token budgets to different components to ensure balanced token usage.'
        }
    ];
    
    // Add context-specific optimizations based on token usage
    const tokenPercentage = dashboardState.currentTokens / CONFIG.tokenBudget;
    
    if (tokenPercentage >= CONFIG.dangerThreshold) {
        optimizations.unshift({
            title: 'Urgent: Reduce Log Verbosity',
            description: 'Immediately reduce log verbosity to critical errors only to prevent exceeding token limits.'
        });
    }
    
    if (tokenPercentage >= CONFIG.warningThreshold) {
        optimizations.unshift({
            title: 'Increase Chunk Size',
            description: 'Increasing the chunk size will process more lines at once, improving efficiency and reducing overhead.'
        });
    }
    
    if (dashboardState.compressionRatio < 0.6) {
        optimizations.push({
            title: 'Enhance Deduplication',
            description: 'Current compression ratio is below target. Implement advanced deduplication across sessions for better results.'
        });
    }
    
    // Add predictive-based optimizations
    if (dashboardState.predictions && dashboardState.predictions.trendingUp) {
        const { daysUntilCrossing } = dashboardState.predictions;
        
        if (daysUntilCrossing !== null && daysUntilCrossing <= CONFIG.earlyWarningDays * 2) {
            optimizations.unshift({
                title: 'Predictive: Optimize Growth Trend',
                description: `Based on current trend, token usage will reach threshold in ${daysUntilCrossing} days. Implement token reduction strategies now.`
            });
            
            // Add specific strategies for imminent issues
            if (daysUntilCrossing <= CONFIG.earlyWarningDays) {
                optimizations.unshift({
                    title: 'Immediate: Implement Rate Limiting',
                    description: 'Temporarily reduce processing frequency or implement stricter filtering to address imminent threshold crossing.'
                });
            }
        }
    }
    
    // Add optimizations to the list
    optimizations.forEach(opt => {
        const li = document.createElement('li');
        li.className = 'optimization-item';
        
        const title = document.createElement('h4');
        title.textContent = opt.title;
        
        const desc = document.createElement('p');
        desc.textContent = opt.description;
        
        li.appendChild(title);
        li.appendChild(desc);
        elements.optimizationList.appendChild(li);
    });
}

/**
 * Update recent logs table
 */
function updateRecentLogs() {
    // Clear existing log entries
    elements.logsTableBody.innerHTML = '';
    
    // Add log entries
    dashboardState.recentLogs.forEach(log => {
        const row = document.createElement('tr');
        
        // Format date
        const date = new Date(log.timestamp);
        const formattedDate = date.toLocaleString();
        
        // Create cells
        const timestampCell = document.createElement('td');
        timestampCell.textContent = formattedDate;
        
        const logFileCell = document.createElement('td');
        logFileCell.textContent = log.logFile;
        
        const tokensCell = document.createElement('td');
        tokensCell.className = 'token-count';
        tokensCell.textContent = new Intl.NumberFormat('en-US').format(log.tokens);
        
        const compressionCell = document.createElement('td');
        compressionCell.textContent = `${(log.compression * 100).toFixed(1)}%`;
        
        // Add cells to row
        row.appendChild(timestampCell);
        row.appendChild(logFileCell);
        row.appendChild(tokensCell);
        row.appendChild(compressionCell);
        
        // Add row to table
        elements.logsTableBody.appendChild(row);
    });
}