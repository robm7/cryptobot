import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function ReconciliationChart({ data }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!data || data.length === 0) return;

    // Process data for chart
    const chartData = data.map(report => ({
      date: new Date(report.timestamp),
      totalOrders: report.result.total_orders,
      mismatchedOrders: report.result.mismatched_orders,
      mismatchRate: report.result.mismatch_percentage
    })).sort((a, b) => a.date - b.date);

    // Clear previous chart
    d3.select(chartRef.current).selectAll('*').remove();

    // Set dimensions
    const margin = { top: 20, right: 80, bottom: 30, left: 50 };
    const width = chartRef.current.clientWidth - margin.left - margin.right;
    const height = chartRef.current.clientHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(chartRef.current)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Set scales
    const x = d3.scaleTime()
      .domain(d3.extent(chartData, d => d.date))
      .range([0, width]);

    const yOrders = d3.scaleLinear()
      .domain([0, d3.max(chartData, d => d.totalOrders) * 1.1])
      .nice()
      .range([height, 0]);

    const yRate = d3.scaleLinear()
      .domain([0, d3.max(chartData, d => d.mismatchRate) * 1.5 || 0.05])
      .nice()
      .range([height, 0]);

    // Add axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat('%m/%d %H:%M')));

    svg.append('g')
      .call(d3.axisLeft(yOrders))
      .append('text')
      .attr('fill', '#000')
      .attr('transform', 'rotate(-90)')
      .attr('y', -40)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .text('Order Count');

    svg.append('g')
      .attr('transform', `translate(${width}, 0)`)
      .call(d3.axisRight(yRate).tickFormat(d => (d * 100).toFixed(1) + '%'))
      .append('text')
      .attr('fill', '#000')
      .attr('transform', 'rotate(-90)')
      .attr('y', 40)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .text('Mismatch Rate');

    // Add total orders line
    const totalOrdersLine = d3.line()
      .x(d => x(d.date))
      .y(d => yOrders(d.totalOrders));

    svg.append('path')
      .datum(chartData)
      .attr('fill', 'none')
      .attr('stroke', 'steelblue')
      .attr('stroke-width', 2)
      .attr('d', totalOrdersLine);

    // Add mismatched orders line
    const mismatchedOrdersLine = d3.line()
      .x(d => x(d.date))
      .y(d => yOrders(d.mismatchedOrders));

    svg.append('path')
      .datum(chartData)
      .attr('fill', 'none')
      .attr('stroke', 'orange')
      .attr('stroke-width', 2)
      .attr('d', mismatchedOrdersLine);

    // Add mismatch rate line
    const mismatchRateLine = d3.line()
      .x(d => x(d.date))
      .y(d => yRate(d.mismatchRate));

    svg.append('path')
      .datum(chartData)
      .attr('fill', 'none')
      .attr('stroke', 'red')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5')
      .attr('d', mismatchRateLine);

    // Add legend
    const legend = svg.append('g')
      .attr('font-family', 'sans-serif')
      .attr('font-size', 10)
      .attr('text-anchor', 'end')
      .selectAll('g')
      .data([
        { label: 'Total Orders', color: 'steelblue' },
        { label: 'Mismatched Orders', color: 'orange' },
        { label: 'Mismatch Rate', color: 'red', dashed: true }
      ])
      .enter().append('g')
      .attr('transform', (d, i) => `translate(${width},${i * 20})`);

    legend.append('rect')
      .attr('x', -17)
      .attr('width', 15)
      .attr('height', 2)
      .attr('fill', d => d.color)
      .attr('stroke-dasharray', d => d.dashed ? '5,5' : '0');

    legend.append('text')
      .attr('x', -20)
      .attr('y', 3)
      .text(d => d.label);

    // Add threshold line for alert (1% mismatch rate)
    svg.append('line')
      .attr('x1', 0)
      .attr('y1', yRate(0.01))
      .attr('x2', width)
      .attr('y2', yRate(0.01))
      .attr('stroke', 'red')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3');

    svg.append('text')
      .attr('x', width - 5)
      .attr('y', yRate(0.01) - 5)
      .attr('text-anchor', 'end')
      .attr('font-size', '10px')
      .attr('fill', 'red')
      .text('Alert Threshold (1%)');

    // Add data points
    svg.selectAll('.total-dot')
      .data(chartData)
      .enter().append('circle')
      .attr('class', 'total-dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => yOrders(d.totalOrders))
      .attr('r', 4)
      .attr('fill', 'steelblue');

    svg.selectAll('.mismatch-dot')
      .data(chartData)
      .enter().append('circle')
      .attr('class', 'mismatch-dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => yOrders(d.mismatchedOrders))
      .attr('r', 4)
      .attr('fill', 'orange');

    svg.selectAll('.rate-dot')
      .data(chartData)
      .enter().append('circle')
      .attr('class', 'rate-dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => yRate(d.mismatchRate))
      .attr('r', 4)
      .attr('fill', 'red');

    // Add tooltips
    const tooltip = d3.select(chartRef.current)
      .append('div')
      .attr('class', 'tooltip')
      .style('position', 'absolute')
      .style('background-color', 'white')
      .style('border', '1px solid #ddd')
      .style('border-radius', '4px')
      .style('padding', '8px')
      .style('pointer-events', 'none')
      .style('opacity', 0);

    const formatTime = d3.timeFormat('%Y-%m-%d %H:%M');
    
    svg.selectAll('circle')
      .on('mouseover', function(event, d) {
        d3.select(this).attr('r', 6);
        tooltip.transition().duration(200).style('opacity', 0.9);
        tooltip.html(`
          <div>
            <strong>Date:</strong> ${formatTime(d.date)}<br/>
            <strong>Total Orders:</strong> ${d.totalOrders}<br/>
            <strong>Mismatched Orders:</strong> ${d.mismatchedOrders}<br/>
            <strong>Mismatch Rate:</strong> ${(d.mismatchRate * 100).toFixed(2)}%
          </div>
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px');
      })
      .on('mouseout', function() {
        d3.select(this).attr('r', 4);
        tooltip.transition().duration(500).style('opacity', 0);
      });

  }, [data]);

  return <div ref={chartRef} className="w-full h-full" />;
}