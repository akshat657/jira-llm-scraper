#!/usr/bin/env python3
"""
Minimal Jira Scraper - Apache Jira to JSONL
Author: akshat657
Date: 2025-11-01

LEARNING NOTES:
- Uses Apache Jira REST API (public, no auth needed)
- Fetches issues using JQL (Jira Query Language)
- Transforms nested JSON to flat structure
- Writes JSONL format (one JSON per line)
"""
import requests
import jsonlines
import yaml
from typing import Dict, List


class SimpleJiraScraper:
    """Simple scraper for Apache Jira public issues"""
    
    def __init__(self, base_url: str):
        """
        Initialize the scraper
        
        Args:
            base_url: Jira server URL (e.g., https://issues.apache.org/jira)
        """
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        
        # Create a session (reuses connection for multiple requests = faster!)
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
    
    def fetch_issues(self, project: str, max_results: int = 10) -> List[Dict]:
        """
        Fetch issues from Apache Jira project
        
        Args:
            project: Project key (e.g., 'KAFKA', 'SPARK')
            max_results: Number of issues to fetch
            
        Returns:
            List of issue dictionaries (raw Jira format)
        """
        # API endpoint for searching issues
        url = f"{self.base_url}/rest/api/2/search"
        
        # JQL = Jira Query Language (like SQL for Jira)
        # This query says: "Get all issues from KAFKA project, newest first"
        params = {
            'jql': f'project = {project} ORDER BY created DESC',
            'maxResults': max_results,
            'fields': 'key,summary,description,status,created,updated,issuetype,priority,reporter'
        }
        
        print(f"🔍 Fetching {max_results} issues from {project}...")
        print(f"   URL: {url}")
        
        try:
            # Make the API request
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()  # Raise error if status code is bad
            
            # Parse JSON response
            data = response.json()
            issues = data.get('issues', [])  # Get 'issues' array, or [] if missing
            total = data.get('total', 0)
            
            print(f"✅ Found {len(issues)} issues (Total available: {total:,})")
            
            return issues
            
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout - Apache Jira might be slow")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching issues: {e}")
            return []
    
    def transform_to_jsonl(self, raw_issues: List[Dict]) -> List[Dict]:
        """
        Convert raw Jira format to clean JSONL format
        
        Jira's format is NESTED (fields inside fields inside fields...)
        We want FLAT (simple key-value pairs)
        
        Args:
            raw_issues: List of raw Jira issue objects
            
        Returns:
            List of cleaned/flattened dictionaries
        """
        transformed = []
        
        for issue in raw_issues:
            # Jira puts all the good stuff in 'fields'
            fields = issue.get('fields', {})
            
            # Extract description safely
            # Sometimes it's a string, sometimes a dict (ADF format), sometimes None
            description = fields.get('description', '')
            if isinstance(description, dict):
                # Jira's new format: Atlassian Document Format (complex!)
                # For now, just convert to string (we'll improve this later)
                description = str(description)
            
            # Build clean structure
            clean_issue = {
                'issue_id': issue.get('key'),  # e.g., "KAFKA-12345"
                'title': fields.get('summary', ''),  # Issue title
                'description': description if description else '',
                'status': fields.get('status', {}).get('name', 'Unknown'),  # Open, Resolved, etc.
                'type': fields.get('issuetype', {}).get('name', 'Unknown'),  # Bug, Feature, etc.
                'priority': fields.get('priority', {}).get('name', 'None'),  # Major, Minor, etc.
                'created': fields.get('created'),  # ISO 8601 timestamp
                'updated': fields.get('updated'),
                'reporter': fields.get('reporter', {}).get('displayName', 'Unknown')
            }
            
            transformed.append(clean_issue)
        
        return transformed
    
    def save_to_file(self, data: List[Dict], filename: str):
        """
        Save data to JSONL file
        
        JSONL = JSON Lines format
        Each line is a complete JSON object
        
        Example:
        {"issue_id": "KAFKA-1", "title": "Fix bug"}
        {"issue_id": "KAFKA-2", "title": "Add feature"}
        
        Why JSONL? Easy to stream (process one line at a time)
        Perfect for big datasets!
        """
        print(f"💾 Saving {len(data)} issues to {filename}...")
        
        with jsonlines.open(filename, mode='w') as writer:
            for item in data:
                writer.write(item)  # Writes one line per item
        
        print(f"✅ Saved successfully!")
        print(f"   File: {filename}")
        print(f"   Size: {len(data)} lines")


def main():
    """Main execution function - orchestrates everything"""
    print("=" * 60)
    print("🚀 Apache Jira Scraper - Minimal Prototype")
    print("=" * 60)
    print()
    
    # Load configuration from YAML file
    try:
        with open('config.yaml') as f:
            config = yaml.safe_load(f)  # Parse YAML to Python dict
    except FileNotFoundError:
        print("❌ config.yaml not found!")
        return
    
    # Initialize scraper
    scraper = SimpleJiraScraper(config['jira']['base_url'])
    
    # Step 1: Fetch raw issues from Jira
    raw_issues = scraper.fetch_issues(
        project=config['jira']['project'],
        max_results=config['jira']['max_issues']
    )
    
    if not raw_issues:
        print("⚠️  No issues found or error occurred!")
        return
    
    # Step 2: Transform to clean format
    print()
    print("🔄 Transforming data to JSONL format...")
    transformed = scraper.transform_to_jsonl(raw_issues)
    
    # Step 3: Save to file
    print()
    scraper.save_to_file(transformed, config['output']['file'])
    
    # Summary
    print()
    print("=" * 60)
    print("🎉 Scraping Complete!")
    print("=" * 60)
    print(f"Project: {config['jira']['project']}")
    print(f"Issues: {len(transformed)}")
    print(f"Output: {config['output']['file']}")
    print()
    print("💡 Next: Check the output file with:")
    print(f"   cat {config['output']['file']}")


if __name__ == "__main__":
    main()