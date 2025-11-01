#!/usr/bin/env python3
"""
Transform Jira issues to JSONL format for LLM training
"""
from typing import Dict, List
import logging
from src.transformer.cleaner import TextCleaner


class JiraToJSONL:
    """Transform Jira format to clean JSONL"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        """
        Initialize transformer
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.cleaner = TextCleaner()
    
    def transform(self, raw_issue: Dict) -> Dict:
        """
        Transform raw Jira issue to clean JSONL format
        
        Args:
            raw_issue: Raw issue from Jira API
            
        Returns:
            Cleaned and structured dictionary
        """
        fields = raw_issue.get('fields', {})
        
        # Extract and clean description
        description = self._extract_text(
            fields.get('description'),
            self.config['transformer']['cleaning']['max_description_length']
        )
        
        # Extract comments
        comments = self._extract_comments(raw_issue.get('all_comments', []))
        
        # Extract metadata
        metadata = self._extract_metadata(fields)
        
        # Build output structure
        output = {
            'issue_id': raw_issue['key'],
            'project': raw_issue['key'].split('-')[0],
            'url': f"{self.config['jira']['base_url']}/browse/{raw_issue['key']}",
            
            'metadata': metadata,
            
            'content': {
                'title': fields.get('summary', ''),
                'description': description,
                'comments': comments,
                'comment_count': len(comments)
            }
        }
        
        # Add LLM training tasks if enabled
        if self.config['transformer']['enabled']:
            output['training_tasks'] = self._generate_tasks(output)
        
        return output
    
    def _extract_text(self, content, max_length: int) -> str:
        """Extract plain text from various Jira formats"""
        if not content:
            return ""
        
        # String (HTML or plain text)
        if isinstance(content, str):
            if self.config['transformer']['cleaning']['remove_html']:
                return self.cleaner.clean(content, max_length)
            return content[:max_length] if max_length else content
        
        # ADF (Atlassian Document Format)
        if isinstance(content, dict):
            return self.cleaner.parse_adf(content)
        
        return ""
    
    def _extract_comments(self, raw_comments: List[Dict]) -> List[Dict]:
        """Extract and clean comments"""
        comments = []
        max_length = self.config['transformer']['cleaning']['max_comment_length']
        
        for comment in raw_comments:
            body = self._extract_text(comment.get('body', ''), max_length)
            
            if body:  # Only include non-empty comments
                comments.append({
                    'author': comment.get('author', 'Unknown'),
                    'created': comment.get('created'),
                    'body': body
                })
        
        return comments
    
    def _extract_metadata(self, fields: Dict) -> Dict:
        """Extract metadata fields"""
        return {
            'status': fields.get('status', {}).get('name', 'Unknown'),
            'priority': fields.get('priority', {}).get('name', 'None'),
            'type': fields.get('issuetype', {}).get('name', 'Unknown'),
            'created': fields.get('created'),
            'updated': fields.get('updated'),
            'resolved': fields.get('resolved'),
            'labels': fields.get('labels', []),
            'components': [c.get('name') for c in fields.get('components', [])],
            'assignee': self._get_user_name(fields.get('assignee')),
            'reporter': self._get_user_name(fields.get('reporter'))
        }
    
    def _get_user_name(self, user_obj) -> str:
        """Safely extract username, returning 'Unknown' when missing"""
        if not user_obj:
            return 'Unknown'
        return user_obj.get('displayName') or user_obj.get('name') or 'Unknown'
    
    def _generate_tasks(self, issue_data: Dict) -> List[Dict]:
        """Generate LLM training tasks from issue"""
        tasks = []
        
        content = issue_data['content']
        metadata = issue_data['metadata']
        
        # Task 1: Summarization
        if content['description']:
            tasks.append({
                'task_type': 'summarization',
                'instruction': 'Summarize the following software issue in one sentence:',
                'input': f"Title: {content['title']}\n\nDescription: {content['description'][:500]}",
                'output': content['title']
            })
        
        # Task 2: Classification
        tasks.append({
            'task_type': 'classification',
            'instruction': 'Classify this issue type (bug, feature, improvement, task):',
            'input': f"{content['title']}\n\n{content['description'][:300]}",
            'output': metadata['type'].lower()
        })
        
        # Task 3: Q&A from comments
        if content['comments']:
            first_comment = content['comments'][0]
            tasks.append({
                'task_type': 'qa',
                'instruction': 'Based on the issue, answer the following:',
                'input': f"Issue: {content['title']}\n\nQuestion: {first_comment['body'][:200]}",
                'output': content['description'][:300] if content['description'] else "See issue description."
            })
        
        # Task 4: Code extraction
        code_blocks = self.cleaner.extract_code_blocks(content['description'])
        if code_blocks:
            tasks.append({
                'task_type': 'code_extraction',
                'instruction': 'Extract code snippets from this issue:',
                'input': content['description'][:800],
                'output': '\n\n'.join(code_blocks[:3])  # Max 3 code blocks
            })
        
        return tasks