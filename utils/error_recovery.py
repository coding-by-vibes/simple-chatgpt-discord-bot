"""
Error Recovery and Resilience Module
This module provides functionality for handling errors gracefully and implementing recovery strategies.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import asyncio
from functools import wraps

class RecoveryStrategy(Enum):
    """Enum for different recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    DEGRADED = "degraded"

class ErrorRecovery:
    def __init__(self, settings_dir: str):
        """Initialize the error recovery system.
        
        Args:
            settings_dir: Directory for storing recovery settings
        """
        self.settings_dir = settings_dir
        self.logger = logging.getLogger(__name__)
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60  # seconds
        self.circuit_breaker_reset_timeout = 300  # seconds
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.max_retry_delay = 10  # seconds
        
        # Fallback settings
        self.fallback_timeout = 5  # seconds
        
        # Initialize circuit breaker state
        self.circuit_breaker_state = {
            "failures": 0,
            "last_failure_time": 0,
            "is_open": False
        }
        
        # Initialize recovery history
        self.recovery_history = []
    
    def retry(self, max_retries: Optional[int] = None, 
              initial_delay: Optional[float] = None,
              max_delay: Optional[float] = None):
        """Decorator for implementing retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                retries = max_retries or self.max_retries
                delay = initial_delay or self.retry_delay
                max_delay_time = max_delay or self.max_retry_delay
                
                last_exception = None
                for attempt in range(retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < retries - 1:
                            wait_time = min(delay * (2 ** attempt), max_delay_time)
                            self.logger.warning(
                                f"Attempt {attempt + 1}/{retries} failed: {str(e)}. "
                                f"Retrying in {wait_time} seconds..."
                            )
                            await asyncio.sleep(wait_time)
                
                self.logger.error(f"All {retries} attempts failed. Last error: {str(last_exception)}")
                raise last_exception
            
            return wrapper
        return decorator
    
    def circuit_breaker(self, threshold: Optional[int] = None,
                       timeout: Optional[int] = None,
                       reset_timeout: Optional[int] = None):
        """Decorator for implementing circuit breaker pattern.
        
        Args:
            threshold: Number of failures before opening circuit
            timeout: Time in seconds before attempting to close circuit
            reset_timeout: Time in seconds before resetting failure count
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                current_time = time.time()
                
                # Check if circuit is open
                if self.circuit_breaker_state["is_open"]:
                    if current_time - self.circuit_breaker_state["last_failure_time"] >= (timeout or self.circuit_breaker_timeout):
                        # Try to close circuit
                        self.circuit_breaker_state["is_open"] = False
                        self.circuit_breaker_state["failures"] = 0
                    else:
                        raise Exception("Circuit breaker is open")
                
                # Check if we should reset failure count
                if current_time - self.circuit_breaker_state["last_failure_time"] >= (reset_timeout or self.circuit_breaker_reset_timeout):
                    self.circuit_breaker_state["failures"] = 0
                
                try:
                    result = await func(*args, **kwargs)
                    # Reset failure count on success
                    self.circuit_breaker_state["failures"] = 0
                    return result
                except Exception as e:
                    # Increment failure count
                    self.circuit_breaker_state["failures"] += 1
                    self.circuit_breaker_state["last_failure_time"] = current_time
                    
                    # Check if we should open circuit
                    if self.circuit_breaker_state["failures"] >= (threshold or self.circuit_breaker_threshold):
                        self.circuit_breaker_state["is_open"] = True
                        self.logger.error("Circuit breaker opened due to too many failures")
                    
                    raise e
            
            return wrapper
        return decorator
    
    def fallback(self, fallback_func: Callable, timeout: Optional[float] = None):
        """Decorator for implementing fallback pattern.
        
        Args:
            fallback_func: Function to call if main function fails
            timeout: Maximum time to wait for main function
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    if timeout:
                        # Run with timeout
                        return await asyncio.wait_for(func(*args, **kwargs), timeout)
                    return await func(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(f"Main function failed: {str(e)}. Using fallback...")
                    return await fallback_func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def degraded(self, degraded_func: Callable):
        """Decorator for implementing degraded service pattern.
        
        Args:
            degraded_func: Function to call in degraded mode
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(f"Service degraded: {str(e)}. Using degraded function...")
                    return await degraded_func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_recovery_history(self) -> List[Dict[str, Any]]:
        """Get the history of recovery attempts.
        
        Returns:
            List of recovery attempt records
        """
        return self.recovery_history
    
    def clear_recovery_history(self):
        """Clear the recovery history."""
        self.recovery_history = []
    
    def get_circuit_breaker_state(self) -> Dict[str, Any]:
        """Get the current state of the circuit breaker.
        
        Returns:
            Current circuit breaker state
        """
        return self.circuit_breaker_state.copy()
    
    def reset_circuit_breaker(self):
        """Reset the circuit breaker state."""
        self.circuit_breaker_state = {
            "failures": 0,
            "last_failure_time": 0,
            "is_open": False
        } 