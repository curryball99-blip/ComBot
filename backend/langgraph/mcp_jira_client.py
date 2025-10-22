import asyncio
import json
import base64
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MCPJiraClient:
    """Minimal MCP JIRA client using requests (same as your working code)"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to JIRA API (sync, same as your working code)"""
        url = f"{self.base_url}/rest/api/3/{endpoint}"
        
        kwargs = {
            'headers': self.headers,
            'auth': self.auth,
            'timeout': 180
        }
        
        if data and method in ['POST', 'PUT']:
            kwargs['json'] = data
        
        response = requests.request(method, url, **kwargs)
        
        if response.status_code >= 400:
            error_msg = f"JIRA API error {response.status_code}: {response.text}"
            if response.status_code == 410:
                error_msg += " - API endpoint deprecated, check migration guide"
            elif response.status_code == 401:
                error_msg += " - Authentication failed, check credentials"
            elif response.status_code == 403:
                error_msg += " - Permission denied, check user permissions"
            elif response.status_code == 404:
                error_msg += " - Resource not found, check URL/endpoint"
            logger.error(f"URL: {url}, Status: {response.status_code}")
            raise Exception(error_msg)
        
        return response.json()
    
    def search_issues(self, jql: str, max_results: int = 5000) -> List[Dict]:
        """Search JIRA issues using JQL"""
        import urllib.parse
        
        # Use the new /search/jql endpoint as per Atlassian migration guide
        fields = 'summary,status,assignee,created,updated,description,issuetype,priority,reporter,components,labels'
        encoded_jql = urllib.parse.quote(jql)
        endpoint = f'search/jql?jql={encoded_jql}&maxResults={max_results}&fields={fields}'
        
        result = self._request('GET', endpoint)
        return result.get('issues', [])
    
    def get_issue(self, issue_key: str) -> Dict:
        """Get specific JIRA issue"""
        return self._request('GET', f'issue/{issue_key}')
    
    def create_issue(self, project_key: str, summary: str, description: str, 
                    issue_type: str = 'Task') -> Dict:
        """Create new JIRA issue"""
        data = {
            'fields': {
                'project': {'key': project_key},
                'summary': summary,
                'description': {
                    'type': 'doc',
                    'version': 1,
                    'content': [{
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': description}]
                    }]
                },
                'issuetype': {'name': issue_type}
            }
        }
        return self._request('POST', 'issue', data)
    
    def add_comment(self, issue_key: str, comment: str) -> Dict:
        """Add comment to JIRA issue"""
        data = {
            'body': {
                'type': 'doc',
                'version': 1,
                'content': [{
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': comment}]
                }]
            }
        }
        return self._request('POST', f'issue/{issue_key}/comment', data)
    
    def get_projects(self) -> List[Dict]:
        """Get available projects"""
        return self._request('GET', 'project')
    
    def health_check(self) -> bool:
        """Check JIRA connection"""
        try:
            self._request('GET', 'myself')
            return True
        except:
            return False