#!/usr/bin/env python3
"""
Quick script to view scraped results
"""
import jsonlines

def view_results(filename='kafka_sample.jsonl'):
    """Display scraped issues in a nice format"""
    print("=" * 70)
    print("📊 Scraped Jira Issues Summary")
    print("=" * 70)
    print()
    
    issues = []
    with jsonlines.open(filename) as reader:
        for issue in reader:
            issues.append(issue)
    
    print(f"Total Issues: {len(issues)}")
    print()
    
    # Group by type
    types = {}
    for issue in issues:
        issue_type = issue['type']
        types[issue_type] = types.get(issue_type, 0) + 1
    
    print("Issues by Type:")
    for issue_type, count in types.items():
        print(f"  {issue_type}: {count}")
    print()
    
    # Group by status
    statuses = {}
    for issue in issues:
        status = issue['status']
        statuses[status] = statuses.get(status, 0) + 1
    
    print("Issues by Status:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")
    print()
    
    # Show first 3 issues
    print("First 3 Issues:")
    print("-" * 70)
    for i, issue in enumerate(issues[:3], 1):
        print(f"\n{i}. {issue['issue_id']}: {issue['title']}")
        print(f"   Type: {issue['type']} | Status: {issue['status']} | Priority: {issue['priority']}")
        print(f"   Created: {issue['created'][:10]}")
        desc = issue['description'][:100] + "..." if len(issue['description']) > 100 else issue['description']
        print(f"   Description: {desc}")

if __name__ == "__main__":
    view_results()