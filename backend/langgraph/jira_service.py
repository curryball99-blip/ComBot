import os
import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from .mcp_jira_client import MCPJiraClient

logger = logging.getLogger(__name__)

JQL_QUERY = 'project = "MBSL3" AND component NOT IN (NGAGE,nGage,Ngage,CPaaS,ECP,LEAP,Leap,"LEAP App","LEAP Platform") ORDER BY updated DESC'

class JiraService:
    """JIRA service for chatbot integration"""
    
    def __init__(self):
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_username = os.getenv('JIRA_USERNAME') 
        self.jira_token = os.getenv('JIRA_API_TOKEN')
        
        if not all([self.jira_url, self.jira_username, self.jira_token]):
            logger.warning("JIRA credentials not configured")
            self.client = None
        else:
            self.client = MCPJiraClient(self.jira_url, self.jira_username, self.jira_token)
    
    def is_available(self) -> bool:
        """Check if JIRA service is available"""
        return self.client is not None
    
    async def search_tickets(self, query: str = None, max_results: int = 1000, custom_jql: str = None, 
                           assignee: str = None, status: str = None, priority: str = None) -> List[Dict]:
        """Search JIRA tickets with filters"""
        if not self.client:
            return []
        
        try:
            if custom_jql:
                jql = custom_jql
            elif query:
                if re.match(r'^[A-Z]+-\d+$', query.upper()):
                    jql = f'key = "{query.upper()}"'
                elif query.upper() in ['MBSL3', 'UNO']:
                    jql = f'project = "{query.upper()}" ORDER BY updated DESC'
                else:
                    jql = f'(summary ~ "{query}" OR description ~ "{query}") AND {JQL_QUERY}'
            else:
                jql = JQL_QUERY
            
            # Add filters
            filters = []
            if assignee:
                filters.append(f'assignee = "{assignee}"')
            if status:
                filters.append(f'status = "{status}"')
            if priority:
                filters.append(f'priority = "{priority}"')
            
            if filters and not custom_jql:
                base_jql = jql.replace(' ORDER BY updated DESC', '')
                jql = f'{base_jql} AND {" AND ".join(filters)} ORDER BY updated DESC'
            
            issues = self.client.search_issues(jql, max_results)
            if not issues:
                logger.info(f"JIRA search returned 0 issues for JQL: {jql}")
                return []
            safe_issues = []
            for issue in issues:
                if not isinstance(issue, dict) or 'key' not in issue:
                    logger.warning(f"Skipping malformed JIRA issue object: {issue}")
                    continue
                try:
                    safe_issues.append(self._format_issue(issue))
                except Exception as fe:
                    logger.warning(f"Failed to format issue {issue.get('key','?')}: {fe}")
            return safe_issues
        except Exception as e:
            logger.error(f"JIRA search error: {e}")
            return []
    
    async def get_ticket_details(self, ticket_key: str) -> Optional[Dict]:
        """Get detailed ticket information"""
        if not self.client:
            return None
        
        try:
            issue = self.client.get_issue(ticket_key)
            return self._format_issue_detailed(issue)
        except Exception as e:
            logger.error(f"JIRA get ticket error: {e}")
            return None
    
    async def create_ticket(self, project_key: str, summary: str, 
                           description: str, issue_type: str = 'Task') -> Optional[Dict]:
        """Create new JIRA ticket"""
        if not self.client:
            return None
        
        try:
            result = self.client.create_issue(project_key, summary, description, issue_type)
            return {
                'key': result['key'],
                'url': f"{self.jira_url}/browse/{result['key']}",
                'created': True
            }
        except Exception as e:
            logger.error(f"JIRA create ticket error: {e}")
            return None
    
    async def add_comment_to_ticket(self, ticket_key: str, comment: str) -> bool:
        """Add comment to existing ticket"""
        if not self.client:
            return False
        
        try:
            self.client.add_comment(ticket_key, comment)
            return True
        except Exception as e:
            logger.error(f"JIRA add comment error: {e}")
            return False
    
    async def get_projects(self) -> List[Dict]:
        """Get available JIRA projects"""
        if not self.client:
            return []
        
        try:
            projects = self.client.get_projects()
            return [{'key': p['key'], 'name': p['name']} for p in projects]
        except Exception as e:
            logger.error(f"JIRA get projects error: {e}")
            return []
    
    async def get_historical_tickets(self, issue_type: str = None, component: str = None, limit: int = 100) -> List[Dict]:
        """Get historical closed tickets for analysis"""
        if not self.client:
            return []
        
        try:
            jql = 'project = "MBSL3" AND status IN (Done, Closed, Resolved) AND component NOT IN (NGAGE,nGage,Ngage,CPaaS,ECP,LEAP,Leap,"LEAP App","LEAP Platform")'
            
            if issue_type:
                jql += f' AND issuetype = "{issue_type}"'
            if component:
                jql += f' AND component = "{component}"'
                
            jql += ' ORDER BY resolved DESC'
            
            issues = self.client.search_issues(jql, limit)
            return [self._format_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Error getting historical tickets: {e}")
            return []
    
    def analyze_effort_estimation(self, current_ticket: Dict, historical_tickets: List[Dict]) -> List[Dict]:
        """Analyze effort based on historical similar tickets"""
        try:
            current_fields = current_ticket.get('fields', {})
            current_type = current_fields.get('issuetype', {}).get('name')
            current_summary = current_fields.get('summary', '').lower()
            
            similar_tickets = []
            for ticket in historical_tickets:
                fields = ticket.get('fields', {})
                if fields.get('issuetype', {}).get('name') == current_type:
                    summary = fields.get('summary', '').lower()
                    common_words = set(current_summary.split()) & set(summary.split())
                    if len(common_words) >= 2:
                        similar_tickets.append({
                            'key': ticket.get('key'),
                            'summary': fields.get('summary'),
                            'created': fields.get('created'),
                            'resolved': fields.get('resolutiondate'),
                            'similarity_score': len(common_words)
                        })
            
            similar_tickets.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_tickets[:5]
        except Exception as e:
            logger.error(f"Error analyzing effort: {e}")
            return []
    
    def get_recommendations(self, ticket: Dict, similar_tickets: List[Dict]) -> List[Dict]:
        """Generate recommendations based on historical data"""
        try:
            recommendations = []
            
            if similar_tickets:
                recommendations.append({
                    'type': 'historical_reference',
                    'title': 'Similar Resolved Tickets',
                    'items': [f"{t['key']}: {t['summary'][:60]}..." for t in similar_tickets[:3]]
                })
            
            issue_type = ticket.get('fields', {}).get('issuetype', {}).get('name')
            if issue_type == 'Bug':
                recommendations.append({
                    'type': 'best_practice',
                    'title': 'Bug Resolution Best Practices',
                    'items': [
                        'Reproduce the issue in test environment',
                        'Check recent code changes in affected area',
                        'Review similar past bugs for patterns',
                        'Add unit tests to prevent regression'
                    ]
                })
            elif issue_type == 'Story':
                recommendations.append({
                    'type': 'best_practice',
                    'title': 'Story Implementation Guidelines',
                    'items': [
                        'Break down into smaller tasks',
                        'Define clear acceptance criteria',
                        'Consider impact on existing features',
                        'Plan for testing and documentation'
                    ]
                })
            
            return recommendations
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _format_issue(self, issue: Dict) -> Dict:
        """Format JIRA issue for API response"""
        fields = issue.get('fields', {})
        return {
            'key': issue['key'],
            'summary': fields.get('summary', ''),
            'status': fields.get('status', {}).get('name', ''),
            'priority': fields.get('priority', {}).get('name', ''),
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            'reporter': fields.get('reporter', {}).get('displayName', ''),
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'issueType': fields.get('issuetype', {}).get('name', ''),
            'component': [c.get('name') for c in fields.get('components', [])],
            'labels': fields.get('labels', []),
            'url': f"{self.jira_url}/browse/{issue['key']}"
        }
    
    def _format_issue_detailed(self, issue: Dict) -> Dict:
        """Format detailed JIRA issue"""
        fields = issue.get('fields', {})
        description = ''
        
        # Extract description text from Atlassian Document Format
        if fields.get('description') and fields['description'].get('content'):
            for content in fields['description']['content']:
                if content.get('content'):
                    for text_content in content['content']:
                        if text_content.get('text'):
                            description += text_content['text'] + ' '
        
        return {
            'key': issue['key'],
            'summary': fields.get('summary', ''),
            'description': description.strip(),
            'status': fields.get('status', {}).get('name', ''),
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'url': f"{self.jira_url}/browse/{issue['key']}"
        }
    
    async def health_check(self) -> bool:
        """Check JIRA service health"""
        if not self.client:
            logger.warning("JIRA client not configured")
            return False
        try:
            return self.client.health_check()
        except Exception as e:
            logger.error(f"JIRA health check failed: {e}")
            return False