#!/usr/bin/env python3
"""
Text cleaning utilities for Jira data
Handles HTML, ADF format, and text normalization
"""
import re
from typing import Optional


class TextCleaner:
    """Clean and normalize text from Jira"""
    
    def __init__(self):
        """Initialize text cleaner"""
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')
    
    def clean(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Raw text
            max_length: Maximum length (truncate if longer)
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = self.html_tag_pattern.sub(' ', text)
        
        # Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        # Strip
        text = text.strip()
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def parse_adf(self, adf_content: dict) -> str:
        """
        Parse Atlassian Document Format to plain text
        
        Args:
            adf_content: ADF dictionary
            
        Returns:
            Plain text string
        """
        def extract_text(node):
            """Recursively extract text from ADF nodes"""
            if isinstance(node, str):
                return node
            
            if isinstance(node, dict):
                # Text node
                if node.get('type') == 'text':
                    return node.get('text', '')
                
                # Code block
                if node.get('type') == 'codeBlock':
                    code = extract_text(node.get('content', []))
                    return f"\n```\n{code}\n```\n"
                
                # Paragraph
                if node.get('type') == 'paragraph':
                    return extract_text(node.get('content', [])) + '\n'
                
                # Has content
                if 'content' in node:
                    return ' '.join(extract_text(child) for child in node['content'])
            
            if isinstance(node, list):
                return ' '.join(extract_text(item) for item in node)
            
            return ''
        
        try:
            text = extract_text(adf_content)
            return self.clean(text)
        except Exception:
            # Fallback: just convert to string
            return str(adf_content)
    
    def extract_code_blocks(self, text: str) -> list:
        """
        Extract code blocks from text
        
        Args:
            text: Text containing code blocks
            
        Returns:
            List of code block strings
        """
        # Match ```code``` or {code}...{code}
        patterns = [
            r'```[\s\S]*?```',
            r'\{code[:\w]*\}[\s\S]*?\{code\}'
        ]
        
        blocks = []
        for pattern in patterns:
            blocks.extend(re.findall(pattern, text))
        
        return blocks