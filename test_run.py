#!/usr/bin/env python3
"""
Test script to verify Apache Jira API accessibility
"""
import requests
import sys


def test_jira_connection():
    """Test basic connection to Apache Jira"""
    url = "https://issues.apache.org/jira/rest/api/2/serverInfo"
    
    print("🧪 Testing Apache Jira Connection")
    print("=" * 50)
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("✅ Connection Successful!")
        print()
        print("Server Information:")
        print(f"  Title:   {data.get('serverTitle', 'N/A')}")
        print(f"  Version: {data.get('version', 'N/A')}")
        print(f"  Build:   {data.get('buildNumber', 'N/A')}")
        print()
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Connection timeout!")
        print("   Apache Jira might be down or slow")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_project_access(project="KAFKA"):
    """Test if we can access a specific project"""
    url = "https://issues.apache.org/jira/rest/api/2/search"
    params = {
        'jql': f'project = {project}',
        'maxResults': 1
    }
    
    print(f"🧪 Testing Project Access: {project}")
    print("=" * 50)
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        total = data.get('total', 0)
        
        print(f"✅ Project '{project}' is accessible!")
        print(f"   Total issues: {total:,}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Cannot access project '{project}': {e}")
        return False


def main():
    """Run all tests"""
    print()
    print("🔬 Apache Jira API Test Suite")
    print("=" * 50)
    print()
    
    # Test 1: Basic connection
    test1 = test_jira_connection()
    
    if not test1:
        print("\n⚠️  Fix connection issues before proceeding")
        sys.exit(1)
    
    # Test 2: Project access
    test2 = test_project_access("KAFKA")
    
    # Results
    print("=" * 50)
    print("📊 Test Results:")
    print(f"  Connection:      {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Project Access:  {'✅ PASS' if test2 else '❌ FAIL'}")
    print("=" * 50)
    print()
    
    if test1 and test2:
        print("✨ All tests passed! Ready to run:")
        print("   python scraper.py")
    else:
        print("⚠️  Some tests failed - check errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()