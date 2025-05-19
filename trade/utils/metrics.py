"""
Metrics Collector Utility

This module provides functionality for collecting and reporting metrics
from the trading system, including risk metrics.
"""
from typing import Dict, List, Optional, Any, Union, Callable
import logging
import time
from datetime import datetime
import json
import os
import asyncio
from decimal import Decimal

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Metrics collector for trading systems.
    
    Collects various metrics and can export them to different backends.
    """
    
    def __init__(self, export_interval_seconds: int = 60):
        """
        Initialize the metrics collector.
        
        Args:
            export_interval_seconds: How often to export metrics (in seconds)
        """
        # Metrics storage
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        
        # Metric metadata
        self.metric_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Export settings
        self.export_interval = export_interval_seconds
        self.export_task = None
        self.exporting = False
        
        # Export handlers
        self.export_handlers: Dict[str, Callable] = {
            "log": self._export_to_log,
            "file": self._export_to_file,
            # Additional handlers can be added (Prometheus, InfluxDB, etc.)
        }
        
        # Active export methods
        self.active_exporters = ["log"]
        
        # Check if metrics directory exists
        metrics_dir = os.path.join(os.getcwd(), "metrics")
        if os.path.exists(metrics_dir) and os.path.isdir(metrics_dir):
            self.active_exporters.append("file")
            self.metrics_dir = metrics_dir
        else:
            self.metrics_dir = None
        
        logger.info(f"Metrics collector initialized with export interval: {export_interval_seconds}s")
    
    async def start_exporting(self):
        """Start the background task for exporting metrics"""
        if self.export_task is None:
            self.exporting = True
            self.export_task = asyncio.create_task(self._export_loop())
            logger.info("Metrics exporting started")
    
    async def stop_exporting(self):
        """Stop the background task for exporting metrics"""
        if self.export_task is not None:
            self.exporting = False
            self.export_task.cancel()
            try:
                await self.export_task
            except asyncio.CancelledError:
                pass
            self.export_task = None
            logger.info("Metrics exporting stopped")
    
    async def _export_loop(self):
        """Background task that periodically exports metrics"""
        while self.exporting:
            try:
                self.export_metrics()
                await asyncio.sleep(self.export_interval)
            except Exception as e:
                logger.error(f"Error in metrics export loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Sleep on error to avoid tight loop
    
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """
        Record a counter metric (cumulative).
        
        Args:
            name: Metric name
            value: Value to add to counter
            tags: Optional tags for the metric
        """
        if name not in self.counters:
            self.counters[name] = 0.0
            self._register_metric(name, "counter", tags)
        
        self.counters[name] += value
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a gauge metric (point-in-time value).
        
        Args:
            name: Metric name
            value: Current value
            tags: Optional tags for the metric
        """
        self.gauges[name] = value
        
        if name not in self.metric_metadata:
            self._register_metric(name, "gauge", tags)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a histogram metric (distribution of values).
        
        Args:
            name: Metric name
            value: Value to add to histogram
            tags: Optional tags for the metric
        """
        if name not in self.histograms:
            self.histograms[name] = []
            self._register_metric(name, "histogram", tags)
        
        self.histograms[name].append(value)
        
        # Limit histogram size to prevent memory issues
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]
    
    def _register_metric(self, name: str, metric_type: str, tags: Optional[Dict[str, str]] = None):
        """Register metadata for a metric"""
        self.metric_metadata[name] = {
            "type": metric_type,
            "created_at": datetime.now().isoformat(),
            "tags": tags or {}
        }
    
    def export_metrics(self, exporters: Optional[List[str]] = None):
        """
        Export metrics to configured backends.
        
        Args:
            exporters: Optional list of exporters to use (overrides defaults)
        """
        # Determine which exporters to use
        export_methods = exporters if exporters is not None else self.active_exporters
        
        # Export through each method
        for method in export_methods:
            if method in self.export_handlers:
                try:
                    self.export_handlers[method]()
                except Exception as e:
                    logger.error(f"Error exporting metrics via {method}: {e}")
    
    def _export_to_log(self):
        """Export metrics to log"""
        logger.info(f"METRICS EXPORT - Counters: {len(self.counters)}, Gauges: {len(self.gauges)}, Histograms: {len(self.histograms)}")
        
        # Log some key metrics if they exist
        key_metrics = [
            "risk.portfolio.exposure",
            "risk.portfolio.drawdown",
            "trades.count.total",
            "trades.pnl.total"
        ]
        
        for metric in key_metrics:
            if metric in self.gauges:
                logger.info(f"METRIC: {metric} = {self.gauges[metric]}")
            elif metric in self.counters:
                logger.info(f"METRIC: {metric} = {self.counters[metric]}")
    
    def _export_to_file(self):
        """Export metrics to file"""
        if not self.metrics_dir:
            return
        
        # Create filename based on date
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{date_str}_metrics_{timestamp}.json"
        filepath = os.path.join(self.metrics_dir, filename)
        
        # Prepare metrics data
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": {
                name: self._calculate_histogram_stats(values)
                for name, values in self.histograms.items()
            },
            "metadata": self.metric_metadata
        }
        
        # Write metrics to file
        try:
            with open(filepath, "w") as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing metrics to file: {e}")
    
    def _calculate_histogram_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistics for histogram values"""
        if not values:
            return {"count": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "median": sorted_values[count // 2],
            "p95": sorted_values[int(count * 0.95)] if count >= 20 else sorted_values[-1]
        }
    
    def add_exporter(self, name: str, handler: Callable):
        """
        Add a new metrics exporter.
        
        Args:
            name: Exporter name
            handler: Function to handle the export
        """
        self.export_handlers[name] = handler
        self.active_exporters.append(name)
        logger.info(f"Added metrics exporter: {name}")
    
    def remove_exporter(self, name: str):
        """
        Remove a metrics exporter.
        
        Args:
            name: Exporter name to remove
        """
        if name in self.active_exporters:
            self.active_exporters.remove(name)
            logger.info(f"Removed metrics exporter: {name}")
    
    def reset_counters(self):
        """Reset all counter metrics to zero"""
        self.counters = {name: 0.0 for name in self.counters}
        logger.info("All counter metrics reset")
    
    def reset_all(self):
        """Reset all metrics"""
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
        self.metric_metadata = {}
        logger.info("All metrics reset")