/**
 * Drawdown Visualization Component
 * 
 * This module provides functionality to visualize drawdown periods
 * for better strategy evaluation.
 */

/**
 * Creates a drawdown chart to visualize periods of drawdown in a strategy
 * @param {string} canvasId - The ID of the canvas element to render the chart
 * @param {Array} equityCurve - Array of equity values over time
 * @param {Array} timestamps - Array of timestamps corresponding to equity values
 */
function createDrawdownChart(canvasId, equityCurve, timestamps) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Calculate drawdown series
    const drawdowns = [];
    let peak = equityCurve[0];
    
    for (let i = 0; i < equityCurve.length; i++) {
        peak = Math.max(peak, equityCurve[i]);
        const drawdown = (equityCurve[i] / peak - 1) * 100; // Convert to percentage
        drawdowns.push({
            x: new Date(timestamps[i]),
            y: drawdown
        });
    }
    
    // Find drawdown periods (consecutive negative drawdowns)
    const drawdownPeriods = [];
    let inDrawdown = false;
    let periodStart = null;
    let maxDrawdown = 0;
    let maxDrawdownDate = null;
    
    for (let i = 0; i < drawdowns.length; i++) {
        if (drawdowns[i].y < -1) { // Consider drawdowns greater than 1%
            if (!inDrawdown) {
                inDrawdown = true;
                periodStart = drawdowns[i].x;
                maxDrawdown = drawdowns[i].y;
                maxDrawdownDate = drawdowns[i].x;
            } else if (drawdowns[i].y < maxDrawdown) {
                maxDrawdown = drawdowns[i].y;
                maxDrawdownDate = drawdowns[i].x;
            }
        } else if (inDrawdown) {
            inDrawdown = false;
            drawdownPeriods.push({
                start: periodStart,
                end: drawdowns[i-1].x,
                maxDrawdown: maxDrawdown,
                maxDrawdownDate: maxDrawdownDate
            });
        }
    }
    
    // If still in drawdown at the end of the data
    if (inDrawdown) {
        drawdownPeriods.push({
            start: periodStart,
            end: drawdowns[drawdowns.length-1].x,
            maxDrawdown: maxDrawdown,
            maxDrawdownDate: maxDrawdownDate
        });
    }
    
    // Create chart
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Drawdown',
                data: drawdowns,
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                fill: true,
                pointRadius: 0,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
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
                            return value.toFixed(2) + '%';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Drawdown: ' + context.parsed.y.toFixed(2) + '%';
                        }
                    }
                },
                annotation: {
                    annotations: drawdownPeriods.map((period, index) => ({
                        type: 'box',
                        xMin: period.start,
                        xMax: period.end,
                        yMin: 'min',
                        yMax: 'max',
                        backgroundColor: 'rgba(255, 0, 0, 0.1)',
                        borderColor: 'rgba(255, 0, 0, 0.5)',
                        borderWidth: 1,
                        label: {
                            enabled: true,
                            content: period.maxDrawdown.toFixed(2) + '%',
                            position: 'center'
                        }
                    }))
                }
            }
        }
    });
    
    return {
        chart: chart,
        drawdownPeriods: drawdownPeriods
    };
}

/**
 * Updates the drawdown metrics table with detailed information
 * @param {string} tableId - The ID of the table element to update
 * @param {Array} drawdownPeriods - Array of drawdown period objects
 */
function updateDrawdownMetricsTable(tableId, drawdownPeriods) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody') || table;
    tbody.innerHTML = '';
    
    // Sort drawdown periods by severity (max drawdown)
    const sortedPeriods = [...drawdownPeriods].sort((a, b) => a.maxDrawdown - b.maxDrawdown);
    
    sortedPeriods.forEach((period, index) => {
        const row = document.createElement('tr');
        row.className = index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-700';
        
        const duration = Math.ceil((period.end - period.start) / (1000 * 60 * 60 * 24)); // days
        
        row.innerHTML = `
            <td class="px-4 py-2">${index + 1}</td>
            <td class="px-4 py-2">${period.start.toLocaleDateString()}</td>
            <td class="px-4 py-2">${period.end.toLocaleDateString()}</td>
            <td class="px-4 py-2">${duration} days</td>
            <td class="px-4 py-2 text-red-500">${period.maxDrawdown.toFixed(2)}%</td>
            <td class="px-4 py-2">${period.maxDrawdownDate.toLocaleDateString()}</td>
        `;
        
        tbody.appendChild(row);
    });
}

// Export functions for use in main.js
window.drawdownVisualization = {
    createDrawdownChart,
    updateDrawdownMetricsTable
};