#!/usr/bin/env python3
"""
Enhanced Jira API client with retry logic and error handling
"""
import requests
import time
from typing import Dict, List, Optional
from src.scraper.rate_limiter import RateLimiter


class JiraClient:
    """Enhanced Jira API client"""
    
    def __init__(
        self,
        base_url: str,
        rate_limiter: RateLimiter,
        retry_attempts: int = 3,
        backoff_factor: int = 2
    ):
        """
        Initialize Jira client
        
        Args:
            base_url: Jira server URL
            rate_limiter: Rate limiter instance
            retry_attempts: Number of retries on failure
            backoff_factor: Exponential backoff multiplier
        """
        self.base_url = base_url.rstrip('/')
        self.rate_limiter = rate_limiter
        self.retry_attempts = retry_attempts
        self.backoff_factor = backoff_factor
        
        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'JiraLLMScraper/1.0'
        })
    
    def search_issues(
        self,
        jql: str,
        fields: List[str],
        start_at: int = 0,
        max_results: int = 100,
        expand: Optional[List[str]] = None
    ) -> Dict:
        """
        Search issues using JQL with retry logic
        
        Args:
            jql: JQL query string
            fields: List of fields to return
            start_at: Pagination offset
            max_results: Results per page
            expand: Additional data to expand
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If all retries fail
        """
        url = f"{self.base_url}/rest/api/2/search"
        params = {
            'jql': jql,
            'fields': ','.join(fields),
            'startAt': start_at,
            'maxResults': max_results
        }
        
        if expand:
            params['expand'] = ','.join(expand)
        
        # Retry loop
        for attempt in range(self.retry_attempts):
            try:
                # Wait for rate limit
                self.rate_limiter.wait_if_needed()
                
                # Make request
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"⚠️  Rate limited by server. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                # Handle server errors (5xx)
                if 500 <= response.status_code < 600:
                    wait_time = self.backoff_factor ** attempt
                    print(f"⚠️  Server error {response.status_code}. Retry {attempt+1}/{self.retry_attempts} in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Success!
                return response.json()
                
            except requests.exceptions.Timeout:
                wait_time = self.backoff_factor ** attempt
                print(f"⏱️  Timeout. Retry {attempt+1}/{self.retry_attempts} in {wait_time}s")
                time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_attempts - 1:
                    raise Exception(f"Failed after {self.retry_attempts} attempts: {e}")
                wait_time = self.backoff_factor ** attempt
                print(f"❌ Request failed: {e}. Retry {attempt+1}/{self.retry_attempts} in {wait_time}s")
                time.sleep(wait_time)
        
        raise Exception(f"Failed to fetch issues after {self.retry_attempts} attempts")
    
    def get_issue(self, issue_key: str, fields: List[str]) -> Optional[Dict]:
        """
        Get a single issue by key
        
        Args:
            issue_key: Issue key (e.g., 'KAFKA-12345')
            fields: Fields to return
            
        Returns:
            Issue dictionary or None if not found
        """
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        params = {'fields': ','.join(fields)}
        
        try:
            self.rate_limiter.wait_if_needed()
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Failed to fetch {issue_key}: {e}")
            return None