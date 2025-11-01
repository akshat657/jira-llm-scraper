#!/usr/bin/env python3
"""
Rate limiter using token bucket algorithm
Ensures we don't exceed API rate limits
"""
import time
from threading import Lock
from collections import deque


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm
    
    Example:
        limiter = RateLimiter(requests_per_minute=60)
        limiter.wait_if_needed()  # Blocks if rate limit exceeded
    """
    
    def __init__(self, requests_per_minute: int):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests
        self.last_request_time = 0
        self.lock = Lock()
        self.request_times = deque()  # Track request timestamps
    
    def wait_if_needed(self):
        """
        Block if we're exceeding rate limit
        
        This method is thread-safe and ensures we never exceed
        the configured requests_per_minute.
        """
        with self.lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            cutoff = now - 60
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
            
            # If at limit, wait until oldest request expires
            if len(self.request_times) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0]) + 0.1  # +0.1s buffer
                if sleep_time > 0:
                    print(f"⏳ Rate limit reached. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    now = time.time()
            
            # Ensure minimum interval between consecutive requests
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                time.sleep(wait_time)
                now = time.time()
            
            # Record this request
            self.request_times.append(now)
            self.last_request_time = now
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics"""
        with self.lock:
            now = time.time()
            cutoff = now - 60
            
            # Count requests in last minute
            recent_requests = sum(1 for t in self.request_times if t > cutoff)
            
            return {
                'requests_last_minute': recent_requests,
                'limit': self.requests_per_minute,
                'utilization': f"{(recent_requests / self.requests_per_minute) * 100:.1f}%"
            }