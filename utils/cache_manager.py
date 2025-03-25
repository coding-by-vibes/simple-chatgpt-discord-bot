from typing import Any, Dict, Optional, List, Union
from datetime import datetime, timedelta
import threading
import logging
import json
import os
from collections import OrderedDict
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    key: str
    value: Any
    expiry: datetime
    cache_type: str  # 'memory' or 'disk'
    size_bytes: int = 0

class CacheManager:
    def __init__(self, settings_dir: str, max_memory_size: int = 100 * 1024 * 1024):  # 100MB default
        """Initialize the cache manager.
        
        Args:
            settings_dir: Directory to store cache data
            max_memory_size: Maximum size of memory cache in bytes
        """
        self.settings_dir = settings_dir
        self.cache_dir = os.path.join(settings_dir, "cache")
        self.max_memory_size = max_memory_size
        self.current_memory_size = 0
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize memory cache as LRU cache
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Thread lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_size": 0,
            "disk_size": 0
        }
    
    def _get_cache_key(self, namespace: str, key: str) -> str:
        """Generate a unique cache key."""
        return f"{namespace}:{key}"
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return len(json.dumps(value).encode('utf-8'))
        except:
            return len(str(value).encode('utf-8'))
    
    def _evict_lru_items(self, required_space: int):
        """Evict least recently used items to free up space."""
        with self.lock:
            while (self.current_memory_size + required_space > self.max_memory_size 
                   and self.memory_cache):
                _, entry = self.memory_cache.popitem(last=False)  # Remove oldest item
                self.current_memory_size -= entry.size_bytes
                self.stats["evictions"] += 1
    
    def set(self, namespace: str, key: str, value: Any, ttl: int, 
            cache_type: str = 'memory') -> bool:
        """Set a value in the cache.
        
        Args:
            namespace: Namespace for the cache key
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            cache_type: Type of cache ('memory' or 'disk')
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = self._get_cache_key(namespace, key)
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        size_bytes = self._estimate_size(value)
        
        try:
            if cache_type == 'memory':
                with self.lock:
                    # Check if we need to evict items
                    if size_bytes > self.max_memory_size:
                        self.logger.warning(f"Value too large for memory cache: {size_bytes} bytes")
                        return False
                    
                    self._evict_lru_items(size_bytes)
                    
                    # Add to memory cache
                    entry = CacheEntry(cache_key, value, expiry, cache_type, size_bytes)
                    self.memory_cache[cache_key] = entry
                    self.current_memory_size += size_bytes
                    
                    # Move to end (most recently used)
                    self.memory_cache.move_to_end(cache_key)
            
            elif cache_type == 'disk':
                # Save to disk cache
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
                cache_data = {
                    "value": value,
                    "expiry": expiry.isoformat(),
                    "cache_type": cache_type,
                    "size_bytes": size_bytes
                }
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting cache value: {e}")
            return False
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            namespace: Namespace for the cache key
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value if found and not expired, None otherwise
        """
        cache_key = self._get_cache_key(namespace, key)
        now = datetime.utcnow()
        
        try:
            # Check memory cache first
            with self.lock:
                if cache_key in self.memory_cache:
                    entry = self.memory_cache[cache_key]
                    if entry.expiry > now:
                        # Move to end (most recently used)
                        self.memory_cache.move_to_end(cache_key)
                        self.stats["hits"] += 1
                        return entry.value
                    else:
                        # Remove expired entry
                        del self.memory_cache[cache_key]
                        self.current_memory_size -= entry.size_bytes
            
            # Check disk cache
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    expiry = datetime.fromisoformat(cache_data["expiry"])
                    
                    if expiry > now:
                        self.stats["hits"] += 1
                        return cache_data["value"]
                    else:
                        # Remove expired file
                        os.remove(cache_file)
            
            self.stats["misses"] += 1
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting cache value: {e}")
            self.stats["misses"] += 1
            return None
    
    def delete(self, namespace: str, key: str) -> bool:
        """Delete a value from the cache.
        
        Args:
            namespace: Namespace for the cache key
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = self._get_cache_key(namespace, key)
        
        try:
            deleted = False
            
            # Remove from memory cache
            with self.lock:
                if cache_key in self.memory_cache:
                    entry = self.memory_cache.pop(cache_key)
                    self.current_memory_size -= entry.size_bytes
                    deleted = True
            
            # Remove from disk cache
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                deleted = True
            
            return deleted
        
        except Exception as e:
            self.logger.error(f"Error deleting cache value: {e}")
            return False
    
    def clear(self, namespace: Optional[str] = None):
        """Clear the cache.
        
        Args:
            namespace: Optional namespace to clear. If None, clears all cache.
        """
        try:
            with self.lock:
                if namespace:
                    # Clear specific namespace
                    prefix = f"{namespace}:"
                    # Clear memory cache
                    keys_to_remove = [k for k in self.memory_cache.keys() if k.startswith(prefix)]
                    for key in keys_to_remove:
                        entry = self.memory_cache.pop(key)
                        self.current_memory_size -= entry.size_bytes
                    
                    # Clear disk cache
                    for filename in os.listdir(self.cache_dir):
                        if filename.startswith(prefix):
                            os.remove(os.path.join(self.cache_dir, filename))
                else:
                    # Clear all cache
                    self.memory_cache.clear()
                    self.current_memory_size = 0
                    for filename in os.listdir(self.cache_dir):
                        if filename.endswith('.json'):
                            os.remove(os.path.join(self.cache_dir, filename))
        
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict containing cache statistics
        """
        with self.lock:
            stats = self.stats.copy()
            stats["memory_size"] = self.current_memory_size
            stats["memory_items"] = len(self.memory_cache)
            stats["disk_items"] = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
            return stats
    
    def cleanup_expired(self):
        """Remove all expired cache entries."""
        now = datetime.utcnow()
        
        try:
            # Clean memory cache
            with self.lock:
                expired_keys = [
                    k for k, v in self.memory_cache.items() 
                    if v.expiry <= now
                ]
                for key in expired_keys:
                    entry = self.memory_cache.pop(key)
                    self.current_memory_size -= entry.size_bytes
            
            # Clean disk cache
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        cache_data = json.load(f)
                        expiry = datetime.fromisoformat(cache_data["expiry"])
                        if expiry <= now:
                            os.remove(filepath)
                except:
                    # Remove corrupted cache files
                    os.remove(filepath)
        
        except Exception as e:
            self.logger.error(f"Error cleaning up expired cache entries: {e}") 