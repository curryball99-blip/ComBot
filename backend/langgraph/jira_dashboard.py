from typing import Dict, List
from .jira_service import JiraService
import logging

logger = logging.getLogger(__name__)

class JiraDashboard:
    """Comprehensive JIRA dashboard data provider"""
    
    def __init__(self, jira_service: JiraService):
        self.jira = jira_service
    
    async def get_filter_options(self) -> Dict:
        """Get all filter options for dropdowns"""
        if not self.jira.is_available():
            return {"error": "JIRA not available"}
        
        try:
            base_jql = 'project = "MBSL3" AND component NOT IN (NGAGE,nGage,Ngage,CPaaS,ECP,LEAP,Leap,"LEAP App","LEAP Platform") ORDER BY updated DESC'
            tickets = await self.jira.search_tickets(custom_jql=base_jql, max_results=1000)
            
            statuses = set()
            priorities = set()
            assignees = set()
            components = set()
            
            for ticket in tickets:
                # Use formatted ticket data from JiraService
                if ticket.get('status'):
                    statuses.add(ticket['status'])
                
                if ticket.get('priority'):
                    priorities.add(ticket['priority'])
                
                if ticket.get('assignee') and ticket['assignee'] != 'Unassigned':
                    assignees.add(ticket['assignee'])
                
                for comp in ticket.get('component', []):
                    components.add(comp)
            
            return {
                'statuses': sorted(list(statuses)),
                'priorities': sorted(list(priorities)),
                'assignees': sorted(list(assignees)),
                'components': sorted(list(components))
            }
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {'statuses': [], 'priorities': [], 'assignees': [], 'components': []}
    
    async def get_dashboard_data(self, project_filter: str = 'ALL', date_range: str = '7d', custom_jql: str = None) -> Dict:
        """Get comprehensive JIRA-like dashboard data"""
        if not self.jira.is_available():
            return {"error": "JIRA not available"}
        
        try:
            # Base JQL with new filter
            base_jql_default = 'project = "MBSL3" AND component NOT IN (NGAGE,nGage,Ngage,CPaaS,ECP,LEAP,Leap,"LEAP App","LEAP Platform")'
            if custom_jql and custom_jql.strip():
                base_jql = custom_jql.strip()
            else:
                base_jql = base_jql_default
            
            # Date range mapping
            date_map = {'7d': '-7d', '30d': '-30d', '90d': '-90d'}
            date_jql = date_map.get(date_range, '-7d')
            
            # Get all tickets (unfiltered by date for overall totals)
            all_tickets = await self.jira.search_tickets(custom_jql=f'{base_jql} ORDER BY updated DESC', max_results=1000)
            if custom_jql:
                recent_clause = f'({base_jql}) AND updated >= {date_jql} ORDER BY updated DESC'
            else:
                recent_clause = f'{base_jql_default} AND updated >= {date_jql} ORDER BY updated DESC'
            recent_tickets = await self.jira.search_tickets(custom_jql=recent_clause, max_results=100)
            
            # Filter tickets for selected period (updated >= date_jql)
            period_clause = f'{base_jql} AND updated >= {date_jql} ORDER BY updated DESC'
            period_tickets = await self.jira.search_tickets(custom_jql=period_clause, max_results=1000)

            # Initialize counters (period-based to ensure dashboard reacts to date range)
            overall_total = len(all_tickets)
            total_tickets = len(period_tickets)
            status_counts = {}
            priority_counts = {}
            assignee_counts = {}
            type_counts = {}
            component_counts = {}
            
            # Active vs Resolved
            active_statuses = ['Open', 'In Progress', 'To Do', 'In Review', 'Testing']
            resolved_statuses = ['Done', 'Closed', 'Resolved']
            active_count = 0
            resolved_count = 0
            
            for ticket in period_tickets:
                # Use formatted ticket data from JiraService
                status = ticket.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if status in active_statuses:
                    active_count += 1
                elif status in resolved_statuses:
                    resolved_count += 1
                
                priority = ticket.get('priority', 'Unknown')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                assignee_name = ticket.get('assignee', 'Unassigned')
                assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1
                
                issue_type = ticket.get('issueType', 'Unknown')
                type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
                
                components = ticket.get('component', [])
                if components:
                    for comp_name in components:
                        component_counts[comp_name] = component_counts.get(comp_name, 0) + 1
                else:
                    component_counts['No Component'] = component_counts.get('No Component', 0) + 1
            
            # Calculate percentages
            active_percentage = (active_count / total_tickets * 100) if total_tickets > 0 else 0
            resolved_percentage = (resolved_count / total_tickets * 100) if total_tickets > 0 else 0
            
            return {
                "summary": {
                    "total_tickets": total_tickets,
                    "period_total": total_tickets,
                    "overall_total": overall_total,
                    "active_tickets": active_count,
                    "resolved_tickets": resolved_count,
                    "recent_updates": len(recent_tickets),
                    "active_percentage": round(active_percentage, 1),
                    "resolved_percentage": round(resolved_percentage, 1)
                },
                "status_distribution": dict(sorted(status_counts.items(), key=lambda x: x[1], reverse=True)),
                "priority_distribution": dict(sorted(priority_counts.items(), key=lambda x: x[1], reverse=True)),
                "assignee_distribution": dict(sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:15]),
                "type_distribution": dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)),
                "component_distribution": dict(sorted(component_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "recent_tickets": recent_tickets[:15]
            }
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return {"error": str(e)}