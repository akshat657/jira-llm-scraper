#!/usr/bin/env python3
"""
Main fetcher - orchestrates scraping of multiple projects
Handles pagination, checkpointing, and error recovery
"""
from typing import Dict, List, Generator
from datetime import datetime
import logging
from src.scraper.jira_client import JiraClient
from src.scraper.checkpoint import CheckpointManager


class JiraFetcher:
    """Multi-project Jira scraper with fault tolerance"""
    
    def __init__(
        self,
        jira_client: JiraClient,
        checkpoint_manager: CheckpointManager,
        config: dict,
        logger: logging.Logger
    ):
        """
        Initialize fetcher
        
        Args:
            jira_client: Jira API client
            checkpoint_manager: Checkpoint manager
            config: Configuration dictionary
            logger: Logger instance
        """
        self.client = jira_client
        self.checkpoint = checkpoint_manager
        self.config = config
        self.logger = logger
    
    def fetch_project(
        self,
        project_key: str,
        max_issues: int
    ) -> Generator[Dict, None, None]:
        """
        Fetch all issues for a project with resumable progress
        
        Args:
            project_key: Project key (e.g., 'KAFKA')
            max_issues: Maximum issues to fetch
            
        Yields:
            Individual issues with metadata and comments
        """
        # Check for existing checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint(project_key)
        
        if checkpoint_data and checkpoint_data['status'] == 'completed':
            self.logger.info(f"✅ {project_key} already completed. Skipping.")
            return
        
        start_index = checkpoint_data['last_index'] + 1 if checkpoint_data else 0
        total_scraped = checkpoint_data['total_scraped'] if checkpoint_data else 0
        
        self.logger.info(f"🚀 Starting {project_key} from index {start_index}")
        
        # Build JQL query
        jql = f"project = {project_key} ORDER BY created DESC"
        
        batch_size = self.config['scraping']['batch_size']
        fields = self.config['jira']['fields']
        fetch_comments = self.config['scraping']['features']['fetch_comments']
        
        start_time = datetime.now()
        current_index = start_index
        total_comments = 0
        
        # Pagination loop
        while current_index < max_issues:
            try:
                # Calculate how many to fetch in this batch
                remaining = max_issues - current_index
                batch_max = min(batch_size, remaining)
                
                self.logger.info(f"📥 Fetching batch: {current_index}-{current_index+batch_max} of {max_issues}")
                
                # Fetch batch
                result = self.client.search_issues(
                    jql=jql,
                    fields=fields,
                    start_at=current_index,
                    max_results=batch_max
                )
                
                issues = result.get('issues', [])
                total_available = result.get('total', 0)
                
                if not issues:
                    self.logger.info(f"✅ No more issues. Completed {project_key}.")
                    break
                
                self.logger.info(f"✅ Fetched {len(issues)} issues (Total in project: {total_available:,})")
                
                # Process each issue
                for i, issue in enumerate(issues):
                    try:
                        issue_key = issue['key']
                        
                        # Fetch comments if enabled
                        if fetch_comments:
                            comments = self._fetch_comments(issue)
                            issue['all_comments'] = comments
                            total_comments += len(comments)
                        else:
                            issue['all_comments'] = []
                        
                        # Yield issue
                        yield issue
                        
                        total_scraped += 1
                        
                        # Checkpoint every N issues
                        checkpoint_freq = self.config['checkpointing']['checkpoint_every']
                        if total_scraped % checkpoint_freq == 0:
                            self.checkpoint.save_checkpoint(
                                project_key,
                                issue_key,
                                current_index + i + 1,
                                total_scraped
                            )
                            self.logger.info(f"💾 Checkpoint saved: {total_scraped} issues")
                    
                    except Exception as e:
                        self.logger.error(f"❌ Error processing {issue.get('key', 'unknown')}: {e}")
                        self.checkpoint.log_error(project_key, issue.get('key', 'unknown'), str(e))
                        continue
                
                # Move to next batch
                current_index += len(issues)
                
                # Check if we've reached max_issues
                if total_scraped >= max_issues:
                    self.logger.info(f"✅ Reached max_issues limit: {max_issues}")
                    break
            
            except Exception as e:
                self.logger.error(f"❌ Batch fetch failed at index {current_index}: {e}")
                # Save checkpoint before potentially crashing
                self.checkpoint.save_checkpoint(
                    project_key,
                    "ERROR",
                    current_index,
                    total_scraped
                )
                raise
        
        # Mark complete and save statistics
        end_time = datetime.now()
        self.checkpoint.mark_complete(project_key)
        self.checkpoint.save_statistics(
            project_key,
            total_scraped,
            total_comments,
            start_time,
            end_time
        )
        
        duration = (end_time - start_time).total_seconds()
        self.logger.info(f"🎉 Completed {project_key}: {total_scraped} issues, {total_comments} comments in {duration:.1f}s")
    
    def _fetch_comments(self, issue: Dict) -> List[Dict]:
        """
        Extract comments from issue
        
        Args:
            issue: Issue dictionary
            
        Returns:
            List of comment dictionaries
        """
        try:
            # Comments are in fields.comment.comments
            comments_data = issue.get('fields', {}).get('comment', {})
            comments = comments_data.get('comments', [])
            
            max_comments = self.config['scraping']['features'].get('max_comments', 50)
            
            # Return simplified comment structure
            return [
                {
                    'author': c.get('author', {}).get('displayName', 'Unknown'),
                    'created': c.get('created'),
                    'body': c.get('body', '')
                }
                for c in comments[:max_comments]
            ]
        
        except Exception as e:
            self.logger.warning(f"Failed to extract comments: {e}")
            return []