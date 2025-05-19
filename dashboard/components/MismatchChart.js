import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function MismatchChart({ data }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!data || data.length === 0) return;

    // Process data for chart
    const chartData = data.map(report => ({
      date: new Date(report.timestamp),
      matched: report.result.matched_orders,
      missing: report.result.missing_orders || 0,
      extra: report.result.extra_orders || 0,
      other: (report.result.mismatched_orders || 0) - 
             ((report.result.missing_orders || 0) + (report.result.extra_orders || 0))
    })).sort((a, b) => a.date - b.date);

    // Clear previous chart
    d3.select(chartRef.current).selectAll('*').remove();

    // Set dimensions
    const margin = { top: 20, right: 30, bottom: 40, left: 50 };
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
    const x = d3.scaleBand()
      .domain(chartData.map(d => d.date))
      .range([0, width])
      .padding(0.1);

    const y = d3.scaleLinear()
      .domain([0, d3.max(chartData, d => d.matched + d.missing + d.extra + d.other) * 1.1])
      .nice()
      .range([height, 0]);

    // Add axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).tickFormat(d3.timeFormat('%m/%d %H:%M')))
      .selectAll('text')
      .attr('transform', 'rotate(-45)')
      .style('text-anchor', 'end');

    svg.append('g')
      .call(d3.axisLeft(y));

    // Define colors
    const colors = {
      matched: '#4CAF50',  // Green
      missing: '#F44336',  // Red
      extra: '#FF9800',    // Orange
      other: '#9C27B0'     // Purple
    };

    // Create stacked data
    const keys = ['matched', 'missing', 'extra', 'other'];
    const stackedData = d3.stack()
      .keys(keys)(chartData);

    // Add bars
    svg.append('g')
      .selectAll('g')
      .data(stackedData)
      .enter().append('g')
      .attr('fill', d => colors[d.key])
      .selectAll('rect')
      .data(d => d)
      .enter().append('rect')
      .attr('x', d => x(d.data.date))
      .attr('y', d => y(d[1]))
      .attr('height', d => y(d[0]) - y(d[1]))
      .attr('width', x.bandwidth());

    // Add legend
    const legend = svg.append('g')
      .attr('font-family', 'sans-serif')
      .attr('font-size', 10)
      .attr('text-anchor', 'end')
      .selectAll('g')
      .data([
        { key: 'matched', label: 'Matched Orders', color: colors.matched },
        { key: 'missing', label: 'Missing Orders', color: colors.missing },
        { key: 'extra', label: 'Extra Orders', color: colors.extra },
        { key: 'other', label: 'Other Mismatches', color: colors.other }
      ])
      .enter().append('g')
      .attr('transform', (d, i) => `translate(${width},${i * 20})`);

    legend.append('rect')
      .attr('x', -17)
      .attr('width', 15)
      .attr('height', 15)
      .attr('fill', d => d.color);

    legend.append('text')
      .attr('x', -20)
      .attr('y', 9.5)
      .text(d => d.label);

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
    
    svg.selectAll('rect')
      .on('mouseover', function(event, d) {
        const key = d3.select(this.parentNode).datum().key;
        const value = d.data[key];
        const total = d.data.matched + d.data.missing + d.data.extra + d.data.other;
        const percentage = (value / total * 100).toFixed(1);
        
        d3.select(this).attr('opacity', 0.8);
        tooltip.transition().duration(200).style('opacity', 0.9);
        tooltip.html(`
          <div>
            <strong>Date:</strong> ${formatTime(d.data.date)}<br/>
            <strong>${key.charAt(0).toUpperCase() + key.slice(1)} Orders:</strong> ${value}<br/>
            <strong>Percentage:</strong> ${percentage}%<br/>
            <strong>Total Orders:</strong> ${total}
          </div>
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px');
      })
      .on('mouseout', function() {
        d3.select(this).attr('opacity', 1);
        tooltip.transition().duration(500).style('opacity', 0);
      });

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .style('font-size', '14px')
      .style('font-weight', 'bold')
      .text('Order Reconciliation Breakdown');

  }, [data]);

  return <div ref={chartRef} className="w-full h-full" />;
}