import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function Chart({ data }) {
  const chartRef = useRef(null);

  useEffect(() => {
    const drawChart = () => {
      if (!data || data.length === 0 || !chartRef.current) return;

      // Clear previous chart
      d3.select(chartRef.current).selectAll('*').remove();

      // Set dimensions
      const margin = { top: 20, right: 30, bottom: 30, left: 40 };
      // Ensure clientWidth is positive and fallback if not rendered yet
      const clientWidth = chartRef.current.clientWidth > 0 ? chartRef.current.clientWidth : 600; // Default width
      const clientHeight = chartRef.current.clientHeight > 0 ? chartRef.current.clientHeight : 300; // Default height

      const width = clientWidth - margin.left - margin.right;
      const height = clientHeight - margin.top - margin.bottom;
      
      // Ensure width and height are not negative
      if (width <= 0 || height <= 0) return;


      // Create SVG
      const svg = d3.select(chartRef.current)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      // Set scales
      const x = d3.scaleTime()
        .domain(d3.extent(data, d => new Date(d.timestamp)))
        .range([0, width]);

      const y = d3.scaleLinear()
        .domain([
          d3.min(data, d => Math.min(d.low, d.close)), // Ensure domain covers both low and close
          d3.max(data, d => Math.max(d.high, d.close)) // Ensure domain covers both high and close
        ])
        .nice()
        .range([height, 0]);

      // Add axes
      svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(Math.max(width / 100, 2))); // Adjust number of ticks based on width

      svg.append('g')
        .call(d3.axisLeft(y).ticks(Math.max(height / 50, 2))); // Adjust number of ticks based on height

      // Add line
      const line = d3.line()
        .x(d => x(new Date(d.timestamp)))
        .y(d => y(d.close));

      svg.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', 'steelblue')
        .attr('stroke-width', 1.5)
        .attr('d', line);

      // Add area
      const area = d3.area()
        .x(d => x(new Date(d.timestamp)))
        .y0(y(d3.min(data, d => d.low))) // Use the y scale's min for y0 for better visual
        .y1(d => y(d.close));

      svg.append('path')
        .datum(data)
        .attr('fill', 'rgba(70, 130, 180, 0.2)')
        .attr('d', area);
    };

    drawChart(); // Initial draw

    // Redraw chart on window resize
    const handleResize = () => {
      drawChart();
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  return <div ref={chartRef} className="w-full h-full" />;
}