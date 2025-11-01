#!/usr/bin/env python3
"""
Main entry point for production Jira scraper
Author: akshat657
Date: 2025-11-01

Usage:
    python main.py                    # Run full scraper
    python main.py --reset KAFKA      # Reset checkpoint for KAFKA
    python main.py --stats            # Show statistics
"""
import yaml
import jsonlines
import argparse
from pathlib import Path
from datetime import datetime

from src.scraper.jira_client import JiraClient
from src.scraper.fetcher import JiraFetcher
from src.scraper.checkpoint import CheckpointManager
from src.scraper.rate_limiter import RateLimiter
from src.transformer.formatter import JiraToJSONL
from src.utils.logger import setup_logger


def load_config(config_path: str = 'config/config.yaml') -> dict:
    """Load configuration file with UTF-8 encoding"""
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def show_statistics(checkpoint_mgr: CheckpointManager, projects: list):
    """Display scraping statistics"""
    print("\n" + "=" * 70)
    print("📊 SCRAPING STATISTICS")
    print("=" * 70)
    
    for project_config in projects:
        project = project_config['name']
        stats = checkpoint_mgr.get_statistics(project)
        checkpoint = checkpoint_mgr.get_checkpoint(project)
        
        print(f"\n{project}:")
        if stats:
            print(f"  Status:       {checkpoint['status'] if checkpoint else 'Not started'}")
            print(f"  Issues:       {stats['total_issues']:,}")
            print(f"  Comments:     {stats['total_comments']:,}")
            print(f"  Duration:     {stats['duration_seconds']:.1f}s")
            print(f"  Speed:        {stats['total_issues'] / max(stats['duration_seconds'], 1):.1f} issues/sec")
        elif checkpoint:
            print(f"  Status:       {checkpoint['status']}")
            print(f"  Progress:     {checkpoint['total_scraped']} issues")
        else:
            print(f"  Status:       Not started")
    
    print("\n" + "=" * 70 + "\n")


def main():
    """Main execution function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Jira LLM Scraper')
    parser.add_argument('--reset', type=str, help='Reset checkpoint for project')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Setup logger
    logger = setup_logger(config['logging'])
    
    logger.info("=" * 70)
    logger.info("🚀 JIRA LLM SCRAPER - Production Version")
    logger.info("=" * 70)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Initialize components
    rate_limiter = RateLimiter(config['scraping']['rate_limit']['requests_per_minute'])
    
    jira_client = JiraClient(
        config['jira']['base_url'],
        rate_limiter,
        retry_attempts=config['scraping']['rate_limit']['retry_attempts'],
        backoff_factor=config['scraping']['rate_limit']['backoff_factor']
    )
    
    checkpoint_mgr = CheckpointManager(config['checkpointing']['db_path'])
    
    # Handle --stats flag
    if args.stats:
        show_statistics(checkpoint_mgr, config['jira']['projects'])
        return
    
    # Handle --reset flag
    if args.reset:
        logger.info(f"🔄 Resetting checkpoint for {args.reset}")
        checkpoint_mgr.reset_project(args.reset)
        logger.info(f"✅ Reset complete")
        return
    
    # Initialize fetcher and transformer
    fetcher = JiraFetcher(jira_client, checkpoint_mgr, config, logger)
    transformer = JiraToJSONL(config, logger)
    
    # Create output directory
    output_dir = Path(config['output']['directory'])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each project
    total_issues = 0
    total_start = datetime.now()
    
    for project_config in config['jira']['projects']:
        project_name = project_config['name']
        max_issues = project_config['max_issues']
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"📦 Processing Project: {project_name}")
        logger.info(f"   Max Issues: {max_issues:,}")
        logger.info("=" * 70)
        
        # Check if already completed - SKIP WITHOUT OPENING FILE
        checkpoint = checkpoint_mgr.get_checkpoint(project_name)
        if checkpoint and checkpoint['status'] == 'completed':
            logger.info(f"✅ {project_name} already completed. Skipping.")
            continue  # ← THIS IS THE FIX! Skip to next project without opening file
        
        # Output file
        output_file = output_dir / f"{project_name.lower()}_issues.jsonl"
        
        # Determine mode (append if resuming, write if new)
        mode = 'a' if checkpoint and checkpoint['status'] == 'in_progress' else 'w'
        
        # Scrape and transform
        project_issues = 0
        try:
            with jsonlines.open(output_file, mode=mode) as writer:
                for raw_issue in fetcher.fetch_project(project_name, max_issues):
                    try:
                        # Transform
                        transformed = transformer.transform(raw_issue)
                        
                        # Write to JSONL
                        writer.write(transformed)
                        
                        project_issues += 1
                        total_issues += 1
                        
                        # Progress update every 100 issues
                        if project_issues % 100 == 0:
                            logger.info(f"   Progress: {project_issues} issues processed")
                    
                    except Exception as e:
                        issue_key = raw_issue.get('key', 'unknown')
                        logger.error(f"❌ Transform error for {issue_key}: {e}")
                        checkpoint_mgr.log_error(project_name, issue_key, str(e))
            
            logger.info(f"✅ {project_name} complete: {project_issues} issues → {output_file}")
        
        except Exception as e:
            logger.error(f"❌ Project {project_name} failed: {e}")
            logger.error(f"   Progress saved. Run again to resume.")
    
    # Summary
    total_duration = (datetime.now() - total_start).total_seconds()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("🎉 SCRAPING COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"Total Issues:  {total_issues:,}")
    logger.info(f"Total Time:    {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    logger.info(f"Speed:         {total_issues / max(total_duration, 1):.1f} issues/sec")
    logger.info(f"Output:        {output_dir}")
    logger.info("")
    logger.info("💡 View statistics with: python main.py --stats")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()