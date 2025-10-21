"""
Azure DevOps API Client

Fetches work items, relations, and metadata from Azure DevOps REST API.
"""

import os
import requests
import base64
from typing import Dict, List, Optional
from urllib.parse import quote
import streamlit as st


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps REST API"""

    def __init__(self, organization: str, project: str, pat: str):
        """
        Initialize Azure DevOps client.

        Args:
            organization: Azure DevOps organization name
            project: Project name
            pat: Personal Access Token
        """
        self.organization = organization
        self.project = project
        self.pat = pat
        # URL encode the project name to handle spaces
        encoded_project = quote(project, safe='')
        self.base_url = f"https://dev.azure.com/{organization}/{encoded_project}/_apis"

        # Create authorization header
        auth_string = f":{pat}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }

    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_work_item(_self, work_item_id: int) -> Optional[Dict]:
        """
        Fetch a single work item by ID.

        Args:
            work_item_id: Work item ID

        Returns:
            dict: Work item details or None if not found
        """
        url = f"{_self.base_url}/wit/workitems/{work_item_id}"
        params = {
            "api-version": "7.0",
            "$expand": "all"  # Include all fields and relations
        }

        try:
            response = requests.get(url, headers=_self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            st.error(f"Error fetching work item {work_item_id}: {str(e)}")
            return None

    @st.cache_data(ttl=300)
    def get_work_item_relations(_self, work_item_id: int) -> List[Dict]:
        """
        Fetch all related work items (parent, children, related).

        Args:
            work_item_id: Work item ID

        Returns:
            list: List of related work items
        """
        work_item = _self.get_work_item(work_item_id)
        if not work_item or 'relations' not in work_item:
            return []

        related_items = []
        relations = work_item.get('relations', [])

        for relation in relations:
            rel_type = relation.get('rel', '')
            if 'workitems' in relation.get('url', '').lower():
                # Extract work item ID from URL
                related_id = int(relation['url'].split('/')[-1])
                related_item = _self.get_work_item(related_id)

                if related_item:
                    related_items.append({
                        'id': related_id,
                        'relation_type': rel_type,
                        'data': related_item
                    })

        return related_items

    def get_work_item_hierarchy(self, work_item_id: int) -> Dict:
        """
        Get full hierarchy of a work item (parents, children, related).

        Args:
            work_item_id: Root work item ID

        Returns:
            dict: Hierarchical structure of work items
        """
        main_item = self.get_work_item(work_item_id)
        if not main_item:
            return None

        relations = self.get_work_item_relations(work_item_id)

        # Categorize relations
        parents = []
        children = []
        related = []

        for rel_item in relations:
            rel_type = rel_item['relation_type']
            if 'parent' in rel_type.lower():
                parents.append(rel_item)
            elif 'child' in rel_type.lower():
                children.append(rel_item)
            else:
                related.append(rel_item)

        return {
            'main': main_item,
            'parents': parents,
            'children': children,
            'related': related
        }

    def get_work_item_type(self, work_item: Dict) -> str:
        """Extract work item type (Epic, User Story, Task, Bug, etc.)"""
        if not work_item:
            return "Unknown"
        return work_item.get('fields', {}).get('System.WorkItemType', 'Unknown')

    def get_work_item_title(self, work_item: Dict) -> str:
        """Extract work item title"""
        if not work_item:
            return "Unknown"
        return work_item.get('fields', {}).get('System.Title', 'Untitled')

    def get_work_item_state(self, work_item: Dict) -> str:
        """Extract work item state (New, Active, Closed, etc.)"""
        if not work_item:
            return "Unknown"
        return work_item.get('fields', {}).get('System.State', 'Unknown')

    def get_work_item_description(self, work_item: Dict) -> str:
        """Extract work item description"""
        if not work_item:
            return ""
        return work_item.get('fields', {}).get('System.Description', '')

    def get_work_item_acceptance_criteria(self, work_item: Dict) -> str:
        """Extract acceptance criteria (if available)"""
        if not work_item:
            return ""
        # Try different possible field names
        fields = work_item.get('fields', {})
        return (fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '') or
                fields.get('System.AcceptanceCriteria', ''))

    def get_work_item_assigned_to(self, work_item: Dict) -> str:
        """Extract assigned user"""
        if not work_item:
            return "Unassigned"
        assigned = work_item.get('fields', {}).get('System.AssignedTo', {})
        if isinstance(assigned, dict):
            return assigned.get('displayName', 'Unassigned')
        return str(assigned) if assigned else "Unassigned"

    def get_work_item_tags(self, work_item: Dict) -> List[str]:
        """Extract tags"""
        if not work_item:
            return []
        tags = work_item.get('fields', {}).get('System.Tags', '')
        return [t.strip() for t in tags.split(';') if t.strip()] if tags else []

    @st.cache_data(ttl=300)
    def get_work_item_comments(_self, work_item_id: int) -> List[Dict]:
        """Fetch comments for a work item"""
        url = f"{_self.base_url}/wit/workitems/{work_item_id}/comments"
        params = {"api-version": "7.0"}

        try:
            response = requests.get(url, headers=_self.headers, params=params)
            response.raise_for_status()
            comments_data = response.json()
            return comments_data.get('comments', [])
        except Exception as e:
            st.warning(f"Could not fetch comments: {str(e)}")
            return []

    def get_resolved_solution(self, work_item: Dict) -> str:
        """
        For closed work items, extract the actual solution from comments or resolution fields.
        """
        if not work_item:
            return ""

        fields = work_item.get('fields', {})
        solution_parts = []

        # Check common resolution fields
        resolution = fields.get('Microsoft.VSTS.Common.ResolvedReason', '')
        if resolution:
            solution_parts.append(f"**Resolution Reason:** {resolution}")

        resolved_by = fields.get('Microsoft.VSTS.Common.ResolvedBy', {})
        if isinstance(resolved_by, dict):
            solution_parts.append(f"**Resolved By:** {resolved_by.get('displayName', 'Unknown')}")

        closed_date = fields.get('Microsoft.VSTS.Common.ClosedDate', '')
        if closed_date:
            solution_parts.append(f"**Closed Date:** {closed_date[:10]}")

        # Get comments to find solution details
        work_item_id = work_item.get('id')
        comments = self.get_work_item_comments(work_item_id)

        if comments:
            solution_parts.append("\n**Implementation Notes from Comments:**\n")
            # Get last 3 comments which usually contain closure info
            for comment in comments[-3:]:
                text = comment.get('text', '')
                if text:
                    solution_parts.append(f"- {text[:200]}...")  # Limit length

        # Check for any "Done" or "Completed" related fields
        completion_comments = fields.get('System.History', '')
        if completion_comments:
            solution_parts.append(f"\n**Completion History:** {completion_comments[:300]}...")

        return "\n".join(solution_parts) if solution_parts else "No detailed solution information available in ADO."

    def format_work_item_summary(self, work_item: Dict) -> Dict:
        """Format work item into a clean summary dictionary"""
        if not work_item:
            return {}

        return {
            'id': work_item.get('id'),
            'type': self.get_work_item_type(work_item),
            'title': self.get_work_item_title(work_item),
            'state': self.get_work_item_state(work_item),
            'description': self.get_work_item_description(work_item),
            'acceptance_criteria': self.get_work_item_acceptance_criteria(work_item),
            'assigned_to': self.get_work_item_assigned_to(work_item),
            'tags': self.get_work_item_tags(work_item),
            'url': work_item.get('_links', {}).get('html', {}).get('href', '')
        }

    @st.cache_data(ttl=300)
    def get_team_iterations(_self, team: str = None) -> List[Dict]:
        """
        Fetch all iterations/sprints for a team.

        Args:
            team: Team name (optional, uses project name if not provided)

        Returns:
            list: List of iterations with id, name, path, start/end dates
        """
        if not team:
            team = _self.project

        url = f"https://dev.azure.com/{_self.organization}/{quote(_self.project, safe='')}/_apis/work/teamsettings/iterations"
        params = {
            "api-version": "7.0",
            "$timeframe": "current"
        }

        try:
            response = requests.get(url, headers=_self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            st.warning(f"Could not fetch iterations: {str(e)}")
            return []

    @st.cache_data(ttl=300)
    def get_all_iterations(_self, team: str = None) -> List[Dict]:
        """
        Fetch ALL iterations (past, current, future) for a team.

        Args:
            team: Team name (optional, uses project name if not provided)

        Returns:
            list: List of all iterations
        """
        if not team:
            team = _self.project

        url = f"https://dev.azure.com/{_self.organization}/{quote(_self.project, safe='')}/_apis/work/teamsettings/iterations"
        params = {"api-version": "7.0"}

        try:
            response = requests.get(url, headers=_self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            st.warning(f"Could not fetch iterations: {str(e)}")
            return []

    @st.cache_data(ttl=120)
    def query_work_items_by_wiql(_self, wiql_query: str) -> List[Dict]:
        """
        Execute a WIQL query and return full work item details.

        Args:
            wiql_query: WIQL query string

        Returns:
            list: List of work items
        """
        # Execute WIQL query
        url = f"{_self.base_url}/wit/wiql"
        params = {"api-version": "7.0"}
        body = {"query": wiql_query}

        try:
            response = requests.post(url, headers=_self.headers, params=params, json=body)
            response.raise_for_status()
            query_result = response.json()

            # Extract work item IDs
            work_items = query_result.get('workItems', [])
            if not work_items:
                return []

            work_item_ids = [str(wi['id']) for wi in work_items]

            # Fetch full work item details (batch request)
            if work_item_ids:
                ids_param = ','.join(work_item_ids[:200])  # ADO limits to 200 per request
                details_url = f"https://dev.azure.com/{_self.organization}/_apis/wit/workitems"
                details_params = {
                    "ids": ids_param,
                    "$expand": "all",
                    "api-version": "7.0"
                }

                details_response = requests.get(details_url, headers=_self.headers, params=details_params)
                details_response.raise_for_status()
                details_data = details_response.json()

                return details_data.get('value', [])

            return []

        except Exception as e:
            st.error(f"Error executing WIQL query: {str(e)}")
            return []

    def get_sprint_work_items(self, iteration_path: str) -> List[Dict]:
        """
        Get all work items for a specific sprint/iteration.

        Args:
            iteration_path: Full iteration path (e.g., "ProjectName\\2025\\Sprint 1")

        Returns:
            list: List of work items in the sprint
        """
        wiql_query = f"""
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
               [System.AssignedTo], [Microsoft.VSTS.Scheduling.StoryPoints]
        FROM WorkItems
        WHERE [System.IterationPath] = '{iteration_path}'
        AND [System.TeamProject] = '{self.project}'
        ORDER BY [System.WorkItemType], [System.State]
        """

        return self.query_work_items_by_wiql(wiql_query)


# Test the client
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize client
    client = AzureDevOpsClient(
        organization=os.getenv('ADO_ORGANIZATION'),
        project=os.getenv('ADO_PROJECT'),
        pat=os.getenv('ADO_PAT')
    )

    # Test with a work item ID
    test_id = 12345  # Replace with actual work item ID
    print(f"Fetching work item {test_id}...")

    work_item = client.get_work_item(test_id)
    if work_item:
        print(f"\nWork Item Found:")
        summary = client.format_work_item_summary(work_item)
        for key, value in summary.items():
            print(f"  {key}: {value}")

        print(f"\nFetching hierarchy...")
        hierarchy = client.get_work_item_hierarchy(test_id)
        print(f"  Parents: {len(hierarchy['parents'])}")
        print(f"  Children: {len(hierarchy['children'])}")
        print(f"  Related: {len(hierarchy['related'])}")
    else:
        print("Work item not found or access denied")
