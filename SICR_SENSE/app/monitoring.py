from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry
import json
import logging
import os
import time
import threading
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
import asyncio

# Create custom registry
registry = CollectorRegistry()

# Setup logger
logger = logging.getLogger(__name__)

# ==============================
# Prometheus Metrics
# ==============================

PREDICTION_COUNTER = Counter(
    'ifrs9_predictions_total',
    'Total predictions by risk tier and migration status',
    ['risk_tier', 'predicted_migration', 'model_version'],
    registry=registry
)

LATENCY_HISTOGRAM = Histogram(
    'ifrs9_prediction_latency_seconds',
    'Prediction request latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

MODEL_VERSION_GAUGE = Gauge(
    'ifrs9_model_version',
    'Current model version',
    ['version'],
    registry=registry
)

DAILY_PREDICTIONS = Gauge(
    'ifrs9_daily_predictions',
    'Predictions made today',
    registry=registry
)

ACTIVE_WEBSOCKETS = Gauge(
    'ifrs9_active_websockets',
    'Number of active WebSocket connections',
    registry=registry
)

ACTIVE_USERS = Gauge(
    'ifrs9_active_users',
    'Number of active users',
    registry=registry
)

ERROR_COUNTER = Counter(
    'ifrs9_errors_total',
    'Total errors by type',
    ['error_type', 'endpoint'],
    registry=registry
)

PREDICTION_CONFIDENCE = Histogram(
    'ifrs9_prediction_confidence',
    'Prediction confidence scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

API_REQUEST_DURATION = Summary(
    'ifrs9_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    registry=registry
)

CACHE_HIT_RATIO = Gauge(
    'ifrs9_cache_hit_ratio',
    'Prediction cache hit ratio',
    registry=registry
)

SYSTEM_MEMORY_USAGE = Gauge(
    'ifrs9_system_memory_usage_bytes',
    'System memory usage',
    registry=registry
)

SYSTEM_CPU_USAGE = Gauge(
    'ifrs9_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

# ==============================
# Metrics Manager
# ==============================

class MetricsManager:
    """Enhanced metrics and audit logging with real-time analytics"""
    
    def __init__(self):
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Daily counters
        self.daily_counter = 0
        self.daily_date = date.today()
        self.start_time = datetime.utcnow()
        
        # Real-time metrics storage
        self.recent_predictions = deque(maxlen=1000)
        self.recent_latencies = deque(maxlen=1000)
        self.recent_errors = deque(maxlen=100)
        self.hourly_stats = defaultdict(lambda: {"count": 0, "latency_sum": 0.0, "errors": 0})
        
        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Active users tracking
        self.active_users = set()
        self.active_connections = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Setup loggers
        self._setup_loggers()
        
        # Start background tasks
        self._start_background_tasks()
        
        # Initialize Prometheus metrics with default values
        self._initialize_metrics()
        
        logger.info("MetricsManager initialized")
    
    def _initialize_metrics(self):
        """Initialize Prometheus metrics with default values"""
        try:
            DAILY_PREDICTIONS.set(0)
            ACTIVE_WEBSOCKETS.set(0)
            ACTIVE_USERS.set(0)
            CACHE_HIT_RATIO.set(0)
            SYSTEM_MEMORY_USAGE.set(0)
            SYSTEM_CPU_USAGE.set(0)
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {e}")
    
    def _setup_loggers(self):
        """Setup structured logging"""
        # Audit logger
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        
        audit_handler = logging.FileHandler(f"{self.log_dir}/prediction_audit_log.jsonl")
        audit_handler.setFormatter(logging.Formatter('%(message)s'))
        self.audit_logger.addHandler(audit_handler)
        
        # Performance logger
        self.perf_logger = logging.getLogger("performance")
        self.perf_logger.setLevel(logging.INFO)
        
        perf_handler = logging.FileHandler(f"{self.log_dir}/performance.log")
        perf_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.perf_logger.addHandler(perf_handler)
        
        # Error logger
        self.error_logger = logging.getLogger("errors")
        self.error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.FileHandler(f"{self.log_dir}/errors.log")
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Run hourly stats reset in background thread
        thread = threading.Thread(target=self._hourly_reset_loop, daemon=True)
        thread.start()
        
        # Run system metrics update in background thread
        metrics_thread = threading.Thread(target=self._system_metrics_loop, daemon=True)
        metrics_thread.start()
    
    def _hourly_reset_loop(self):
        """Hourly statistics reset loop"""
        while True:
            now = datetime.utcnow()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            time_to_wait = (next_hour - now).total_seconds()
            
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            
            with self._lock:
                # Archive current hour stats
                current_hour = now.strftime("%Y-%m-%d %H:00")
                stats = self.hourly_stats.get(current_hour, {"count": 0, "latency_sum": 0.0, "errors": 0})
                
                if stats["count"] > 0:
                    self.perf_logger.info(
                        f"Hourly stats - {current_hour}: "
                        f"predictions={stats['count']}, "
                        f"avg_latency={stats['latency_sum']/max(1, stats['count']):.3f}s, "
                        f"errors={stats['errors']}"
                    )
                
                # Reset for new hour
                new_hour = next_hour.strftime("%Y-%m-%d %H:00")
                self.hourly_stats[new_hour] = {"count": 0, "latency_sum": 0.0, "errors": 0}
    
    def _system_metrics_loop(self):
        """System metrics update loop"""
        while True:
            try:
                self.update_system_metrics()
            except Exception as e:
                logger.error(f"Failed to update system metrics: {e}")
            time.sleep(30)  # Update every 30 seconds
    
    def log_prediction(self, input_data: Dict, prediction: Dict, latency: float):
        """Log prediction with full context and metrics"""
        with self._lock:
            # Create audit record
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": round(latency * 1000, 2),
                "input": self._sanitize_input(input_data),
                "output": prediction,
                "cached": prediction.get("cached", False),
                "simulation": prediction.get("simulation", False)
            }
            
            # Write to audit log
            self.audit_logger.info(json.dumps(audit_record))
            
            # Update daily counter
            today = date.today()
            if today != self.daily_date:
                self.daily_counter = 0
                self.daily_date = today
            
            self.daily_counter += 1
            DAILY_PREDICTIONS.set(self.daily_counter)
            
            # Update recent predictions
            self.recent_predictions.append({
                "timestamp": audit_record["timestamp"],
                "risk_tier": prediction.get("risk_tier", "Unknown"),
                "probability": prediction.get("migration_probability", 0),
                "latency": latency,
                "cached": prediction.get("cached", False)
            })
            
            # Update recent latencies
            self.recent_latencies.append(latency)
            
            # Update cache metrics
            if prediction.get("cached"):
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            
            # Update cache hit ratio
            total_cache_requests = self.cache_hits + self.cache_misses
            if total_cache_requests > 0:
                CACHE_HIT_RATIO.set(self.cache_hits / total_cache_requests)
            
            # Update hourly stats
            current_hour = datetime.utcnow().strftime("%Y-%m-%d %H:00")
            if current_hour not in self.hourly_stats:
                self.hourly_stats[current_hour] = {"count": 0, "latency_sum": 0.0, "errors": 0}
            self.hourly_stats[current_hour]["count"] += 1
            self.hourly_stats[current_hour]["latency_sum"] += latency
            
            # Log performance
            if latency > 1.0:
                self.perf_logger.warning(
                    f"High latency prediction: {latency:.3f}s for loan {input_data.get('loan_id', 'unknown')}"
                )
    
    def _sanitize_input(self, input_data: Dict) -> Dict:
        """Sanitize input data for logging (remove sensitive info if needed)"""
        sanitized = input_data.copy()
        # Remove any sensitive fields if necessary
        sensitive_fields = ['ssn', 'tax_id', 'account_number']
        for field in sensitive_fields:
            sanitized.pop(field, None)
        return sanitized
    
    def record_metrics(self, risk_tier: str, predicted_migration: int, model_version: str = "3.0.0"):
        """Record Prometheus metrics"""
        PREDICTION_COUNTER.labels(
            risk_tier=risk_tier,
            predicted_migration=str(predicted_migration),
            model_version=model_version
        ).inc()
        
        MODEL_VERSION_GAUGE.labels(version=model_version).set(1)
    
    def record_error(self, error_type: str, endpoint: str = "unknown"):
        """Record error metrics"""
        with self._lock:
            ERROR_COUNTER.labels(
                error_type=error_type,
                endpoint=endpoint
            ).inc()
            
            self.recent_errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": error_type,
                "endpoint": endpoint
            })
            
            # Update hourly error stats
            current_hour = datetime.utcnow().strftime("%Y-%m-%d %H:00")
            if current_hour not in self.hourly_stats:
                self.hourly_stats[current_hour] = {"count": 0, "latency_sum": 0.0, "errors": 0}
            self.hourly_stats[current_hour]["errors"] += 1
            
            self.error_logger.error(f"Error recorded: {error_type} at {endpoint}")
    
    def record_confidence(self, confidence: float):
        """Record prediction confidence score"""
        PREDICTION_CONFIDENCE.observe(confidence)
    
    def record_api_request(self, method: str, endpoint: str, duration: float):
        """Record API request duration"""
        API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.used)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def update_active_connections(self, count: int):
        """Update active WebSocket connections count"""
        with self._lock:
            self.active_connections = count
            ACTIVE_WEBSOCKETS.set(count)
    
    def update_active_users(self, count: int):
        """Update active users count"""
        with self._lock:
            ACTIVE_USERS.set(count)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        with self._lock:
            # Calculate average latency
            avg_latency = 0
            p95_latency = 0
            p99_latency = 0
            
            if self.recent_latencies:
                sorted_latencies = sorted(self.recent_latencies)
                avg_latency = sum(sorted_latencies) / len(sorted_latencies)
                
                if len(sorted_latencies) > 1:
                    p95_index = int(len(sorted_latencies) * 0.95)
                    p99_index = int(len(sorted_latencies) * 0.99)
                    p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]
                    p99_latency = sorted_latencies[min(p99_index, len(sorted_latencies) - 1)]
            
            # Calculate error rate
            recent_preds = list(self.recent_predictions)
            error_rate = 0
            if recent_preds:
                errors = sum(1 for p in recent_preds if p.get("risk_tier") == "Unknown")
                error_rate = (errors / len(recent_preds)) * 100
            
            # Calculate cache hit ratio
            total_cache = self.cache_hits + self.cache_misses
            cache_hit_ratio = (self.cache_hits / total_cache * 100) if total_cache > 0 else 0
            
            # Get risk distribution
            risk_distribution = defaultdict(int)
            for pred in recent_preds[-100:]:  # Last 100 predictions
                risk_distribution[pred.get("risk_tier", "Unknown")] += 1
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "daily_predictions": self.daily_counter,
                "total_predictions": len(self.recent_predictions),
                "active_users": len(self.active_users),
                "active_connections": self.active_connections,
                "latency": {
                    "average_ms": round(avg_latency * 1000, 2),
                    "p95_ms": round(p95_latency * 1000, 2),
                    "p99_ms": round(p99_latency * 1000, 2)
                },
                "error_rate": round(error_rate, 2),
                "cache_hit_ratio": round(cache_hit_ratio, 2),
                "recent_predictions": list(self.recent_predictions)[-20:],  # Last 20
                "risk_distribution": dict(risk_distribution),
                "uptime_hours": round(
                    (datetime.utcnow() - self.start_time).total_seconds() / 3600, 2
                )
            }
    
    def get_empty_stats(self) -> Dict[str, Any]:
        """Get empty stats for when no data is available"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "daily_predictions": 0,
            "total_predictions": 0,
            "active_users": 0,
            "active_connections": 0,
            "latency": {"average_ms": 0, "p95_ms": 0, "p99_ms": 0},
            "error_rate": 0,
            "cache_hit_ratio": 0,
            "recent_predictions": [],
            "risk_distribution": {},
            "uptime_hours": 0
        }
    
    def get_prediction_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get prediction trends for specified time period"""
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=hours)
            
            recent = [
                p for p in self.recent_predictions
                if datetime.fromisoformat(p["timestamp"]) >= cutoff
            ]
            
            if not recent:
                return {"trends": [], "summary": {}}
            
            # Group by hour
            hourly_trends = defaultdict(lambda: {"count": 0, "avg_probability": 0})
            for pred in recent:
                hour = datetime.fromisoformat(pred["timestamp"]).strftime("%Y-%m-%d %H:00")
                hourly_trends[hour]["count"] += 1
                hourly_trends[hour]["avg_probability"] += pred.get("probability", 0)
            
            # Calculate averages
            for hour in hourly_trends:
                if hourly_trends[hour]["count"] > 0:
                    hourly_trends[hour]["avg_probability"] /= hourly_trends[hour]["count"]
            
            # Calculate risk distribution
            risk_tiers = defaultdict(int)
            for pred in recent:
                risk_tiers[pred.get("risk_tier", "Unknown")] += 1
            
            return {
                "trends": [
                    {"hour": hour, **stats}
                    for hour, stats in sorted(hourly_trends.items())
                ],
                "summary": {
                    "total_predictions": len(recent),
                    "avg_probability": sum(p.get("probability", 0) for p in recent) / len(recent) if recent else 0,
                    "risk_tiers": dict(risk_tiers)
                }
            }
    
    async def cleanup_old_records(self):
        """Clean up old records to manage storage"""
        try:
            # Clean up old log files
            log_files = [
                f for f in os.listdir(self.log_dir)
                if f.endswith('.log') or f.endswith('.jsonl')
            ]
            
            for log_file in log_files:
                file_path = os.path.join(self.log_dir, log_file)
                file_age = time.time() - os.path.getmtime(file_path)
                
                # Archive files older than 30 days
                if file_age > 30 * 24 * 3600:
                    archive_dir = os.path.join(self.log_dir, "archive")
                    os.makedirs(archive_dir, exist_ok=True)
                    
                    archive_path = os.path.join(
                        archive_dir,
                        f"{datetime.utcnow().strftime('%Y%m%d')}_{log_file}"
                    )
                    
                    os.rename(file_path, archive_path)
                    logger.info(f"Archived log file: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
    
    def reset_daily_counter(self):
        """Reset daily counter (called at midnight)"""
        with self._lock:
            self.daily_counter = 0
            self.daily_date = date.today()
            DAILY_PREDICTIONS.set(0)

# Global instance
metrics_manager = MetricsManager()