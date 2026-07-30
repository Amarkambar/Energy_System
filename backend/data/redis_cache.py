"""
Redis Cache Wrapper for Energy Diagnostics

This module provides a Redis-based caching layer that:
- Stores ML predictions, forecasts, and alerts in Redis
- Provides sub-millisecond cache reads (vs. Parquet I/O)
- Persists across backend restarts
- Supports multiple backend instances with shared cache
- Falls back to disk cache if Redis is unavailable

Usage:
    from data.redis_cache import RedisCache
    
    cache = RedisCache()
    cache.set_pipeline_data(df, predictions, forecast, models, alerts, recs)
    data = cache.get_pipeline_data()
"""

import os
import json
import pickle
import logging
from typing import Dict, Any, Optional
from datetime import timedelta

import redis
import pandas as pd

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis-based cache for ML pipeline results with disk fallback"""
    
    def __init__(self, redis_url: str = None, ttl_hours: int = 24):
        """
        Initialize Redis cache connection
        
        Args:
            redis_url: Redis connection URL (default: from REDIS_URL env var)
            ttl_hours: Time-to-live for cached data in hours (default: 24)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = timedelta(hours=ttl_hours)
        self.redis_client = None
        self.enabled = False
        
        # Cache key prefixes
        self.PREFIX = "energy_diagnostics:"
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle serialization manually
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"✅ Redis cache connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️  Redis unavailable ({e}). Falling back to disk cache.")
            self.enabled = False
    
    def _make_key(self, key: str) -> str:
        """Generate namespaced cache key"""
        return f"{self.PREFIX}{key}"
    
    def set_dataframe(self, key: str, df: pd.DataFrame, ttl: timedelta = None) -> bool:
        """
        Store DataFrame in Redis as parquet bytes
        
        Args:
            key: Cache key
            df: DataFrame to cache
            ttl: Time-to-live (default: self.ttl)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or df is None or df.empty:
            return False
        
        try:
            # Serialize DataFrame to parquet bytes
            parquet_bytes = df.to_parquet(index=False, compression='snappy')
            cache_key = self._make_key(key)
            self.redis_client.setex(
                cache_key,
                time=ttl or self.ttl,
                value=parquet_bytes
            )
            logger.debug(f"📦 Cached DataFrame '{key}' ({len(df)} rows, {len(parquet_bytes)} bytes)")
            return True
        except Exception as e:
            logger.warning(f"Failed to cache DataFrame '{key}': {e}")
            return False
    
    def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """
        Retrieve DataFrame from Redis
        
        Args:
            key: Cache key
        
        Returns:
            DataFrame if found, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._make_key(key)
            parquet_bytes = self.redis_client.get(cache_key)
            
            if parquet_bytes is None:
                logger.debug(f"❌ Cache miss: '{key}'")
                return None
            
            # Deserialize parquet bytes to DataFrame
            import io
            df = pd.read_parquet(io.BytesIO(parquet_bytes))
            logger.debug(f"✅ Cache hit: '{key}' ({len(df)} rows)")
            return df
        except Exception as e:
            logger.warning(f"Failed to retrieve DataFrame '{key}': {e}")
            return None
    
    def set_json(self, key: str, data: Dict[str, Any], ttl: timedelta = None) -> bool:
        """
        Store JSON-serializable data in Redis
        
        Args:
            key: Cache key
            data: Dictionary to cache
            ttl: Time-to-live (default: self.ttl)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or data is None:
            return False
        
        try:
            cache_key = self._make_key(key)
            json_str = json.dumps(data, default=str)  # default=str handles datetime
            self.redis_client.setex(
                cache_key,
                time=ttl or self.ttl,
                value=json_str
            )
            logger.debug(f"📦 Cached JSON '{key}' ({len(json_str)} bytes)")
            return True
        except Exception as e:
            logger.warning(f"Failed to cache JSON '{key}': {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data from Redis
        
        Args:
            key: Cache key
        
        Returns:
            Dictionary if found, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._make_key(key)
            json_str = self.redis_client.get(cache_key)
            
            if json_str is None:
                logger.debug(f"❌ Cache miss: '{key}'")
                return None
            
            data = json.loads(json_str)
            logger.debug(f"✅ Cache hit: '{key}'")
            return data
        except Exception as e:
            logger.warning(f"Failed to retrieve JSON '{key}': {e}")
            return None
    
    def set_pickle(self, key: str, obj: Any, ttl: timedelta = None) -> bool:
        """
        Store Python object in Redis using pickle
        
        Args:
            key: Cache key
            obj: Object to cache (must be picklable)
            ttl: Time-to-live (default: self.ttl)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or obj is None:
            return False
        
        try:
            cache_key = self._make_key(key)
            pickle_bytes = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
            self.redis_client.setex(
                cache_key,
                time=ttl or self.ttl,
                value=pickle_bytes
            )
            logger.debug(f"📦 Cached pickle '{key}' ({len(pickle_bytes)} bytes)")
            return True
        except Exception as e:
            logger.warning(f"Failed to cache pickle '{key}': {e}")
            return False
    
    def get_pickle(self, key: str) -> Optional[Any]:
        """
        Retrieve pickled object from Redis
        
        Args:
            key: Cache key
        
        Returns:
            Object if found, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._make_key(key)
            pickle_bytes = self.redis_client.get(cache_key)
            
            if pickle_bytes is None:
                logger.debug(f"❌ Cache miss: '{key}'")
                return None
            
            obj = pickle.loads(pickle_bytes)
            logger.debug(f"✅ Cache hit: '{key}'")
            return obj
        except Exception as e:
            logger.warning(f"Failed to retrieve pickle '{key}': {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._make_key(key)
            self.redis_client.delete(cache_key)
            logger.debug(f"🗑️  Deleted cache key: '{key}'")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete '{key}': {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cache entries with energy_diagnostics prefix"""
        if not self.enabled:
            return False
        
        try:
            pattern = f"{self.PREFIX}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🗑️  Cleared {len(keys)} cache entries")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False, "error": "Redis not connected"}
        
        try:
            info = self.redis_client.info("stats")
            memory = self.redis_client.info("memory")
            
            # Count our keys
            pattern = f"{self.PREFIX}*"
            our_keys = len(self.redis_client.keys(pattern))
            
            return {
                "enabled": True,
                "url": self.redis_url,
                "keys_cached": our_keys,
                "total_commands": info.get("total_commands_processed", 0),
                "cache_hits": info.get("keyspace_hits", 0),
                "cache_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "memory_used_mb": round(memory.get("used_memory", 0) / 1024 / 1024, 2),
                "memory_peak_mb": round(memory.get("used_memory_peak", 0) / 1024 / 1024, 2),
            }
        except Exception as e:
            return {"enabled": False, "error": str(e)}
    
    @staticmethod
    def _calculate_hit_rate(info: Dict) -> float:
        """Calculate cache hit rate percentage"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)
    
    # ── High-level pipeline cache methods ──
    
    def set_pipeline_data(
        self,
        df: pd.DataFrame = None,
        predictions: pd.DataFrame = None,
        forecast: pd.DataFrame = None,
        models: Dict = None,
        alerts: pd.DataFrame = None,
        recommendations: Dict = None,
        alert_summary: Dict = None,
        metadata: Dict = None
    ) -> bool:
        """
        Store complete pipeline results in Redis
        
        Args:
            df: Main dataset
            predictions: Model predictions
            forecast: Forecast data
            models: Trained model objects (dict)
            alerts: Alert logs
            recommendations: Recommendations
            alert_summary: Alert summary counts
            metadata: Pipeline metadata
        
        Returns:
            True if all successful, False otherwise
        """
        success = True
        
        if df is not None:
            success &= self.set_dataframe("pipeline_df", df)
        
        if predictions is not None:
            success &= self.set_dataframe("pipeline_pred", predictions)
        
        if forecast is not None:
            success &= self.set_dataframe("pipeline_forecast", forecast)
        
        if models is not None:
            success &= self.set_pickle("pipeline_models", models)
        
        if alerts is not None:
            success &= self.set_dataframe("pipeline_alerts", alerts)
        
        if recommendations is not None:
            success &= self.set_json("pipeline_recs", recommendations)
        
        if alert_summary is not None:
            success &= self.set_json("pipeline_alert_summary", alert_summary)
        
        # Always update metadata
        meta = metadata or {}
        meta["ready"] = True
        success &= self.set_json("pipeline_meta", meta)
        
        return success
    
    def get_pipeline_data(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete pipeline results from Redis
        
        Returns:
            Dictionary with all cached data, or None if metadata missing
        """
        # Check if pipeline is ready
        meta = self.get_json("pipeline_meta")
        if meta is None or not meta.get("ready"):
            return None
        
        return {
            "df": self.get_dataframe("pipeline_df"),
            "predictions": self.get_dataframe("pipeline_pred"),
            "forecast": self.get_dataframe("pipeline_forecast"),
            "models": self.get_pickle("pipeline_models"),
            "alerts": self.get_dataframe("pipeline_alerts"),
            "recommendations": self.get_json("pipeline_recs"),
            "alert_summary": self.get_json("pipeline_alert_summary"),
            "metadata": meta
        }
    
    def clear_pipeline(self) -> bool:
        """Clear all pipeline cache entries"""
        keys_to_delete = [
            "pipeline_df",
            "pipeline_pred",
            "pipeline_forecast",
            "pipeline_models",
            "pipeline_alerts",
            "pipeline_recs",
            "pipeline_alert_summary",
            "pipeline_meta"
        ]
        
        for key in keys_to_delete:
            self.delete(key)
        
        logger.info("🗑️  Cleared pipeline cache")
        return True


# ── Global cache instance ──
_redis_cache = None

def get_redis_cache() -> RedisCache:
    """Get or create global Redis cache instance"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
