"""
Azure DevOps URL Parser

Parses various Azure DevOps URLs to extract organization, project, and work item IDs.
Supports: Work Items, Epics, User Stories, Tasks, Bugs, Features, Queries, Boards, etc.
"""

import re
from urllib.parse import urlparse, parse_qs, unquote


def parse_ado_url(url):
    """
    Parse an Azure DevOps URL and extract relevant information.

    Args:
        url (str): Azure DevOps URL

    Returns:
        dict: Parsed information including type, organization, project, work item ID, etc.
              Returns None if URL is not a valid ADO URL
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # Check if it's an Azure DevOps URL
    if 'dev.azure.com' not in url and 'visualstudio.com' not in url:
        return None

    parsed = urlparse(url)
    path = parsed.path
    query_params = parse_qs(parsed.query)

    result = {
        'url': url,
        'organization': None,
        'project': None,
        'work_item_id': None,
        'type': None
    }

    # Extract organization and project from URL
    # Format: https://dev.azure.com/{organization}/{project}/...
    if 'dev.azure.com' in url:
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) >= 2:
            result['organization'] = path_parts[0]
            result['project'] = unquote(path_parts[1])

    # Pattern 1: Direct work item link
    # https://dev.azure.com/{org}/{project}/_workitems/edit/{id}
    work_item_match = re.search(r'/_workitems/edit/(\d+)', path)
    if work_item_match:
        result['work_item_id'] = int(work_item_match.group(1))
        result['type'] = 'work_item'
        return result

    # Pattern 2: Work item in query parameter
    # https://dev.azure.com/{org}/{project}/_boards/board/...?workitem={id}
    if 'workitem' in query_params:
        result['work_item_id'] = int(query_params['workitem'][0])
        result['type'] = 'work_item'
        return result

    # Pattern 3: Query with specific work item selected
    # https://dev.azure.com/{org}/{project}/_queries/query/{queryid}/?_a=query&witd={id}
    if 'witd' in query_params:
        result['work_item_id'] = int(query_params['witd'][0])
        result['type'] = 'work_item'
        return result

    # Pattern 4: Backlog item
    # https://dev.azure.com/{org}/{project}/_backlogs/backlog/.../Stories/?workitem={id}
    if '_backlogs' in path or '_boards' in path:
        if 'workitem' in query_params:
            result['work_item_id'] = int(query_params['workitem'][0])
            result['type'] = 'work_item'
            return result
        result['type'] = 'backlog_view'
        return result

    # Pattern 5: Query view (no specific work item)
    # https://dev.azure.com/{org}/{project}/_queries/query/{queryid}/
    if '_queries' in path:
        query_id_match = re.search(r'/_queries/query(?:-edit)?/([a-f0-9-]+)', path)
        if query_id_match:
            result['query_id'] = query_id_match.group(1)
            result['type'] = 'query'
            return result

    # Pattern 6: Sprint/Iteration view
    if '_sprints' in path:
        result['type'] = 'sprint_view'
        return result

    # Default: Generic ADO URL
    result['type'] = 'ado_page'
    return result


def extract_work_item_id(url):
    """
    Quick helper to extract just the work item ID from a URL.

    Args:
        url (str): Azure DevOps URL

    Returns:
        int: Work item ID or None if not found
    """
    parsed = parse_ado_url(url)
    if parsed:
        return parsed.get('work_item_id')
    return None


def is_valid_ado_url(url):
    """
    Check if a URL is a valid Azure DevOps URL.

    Args:
        url (str): URL to check

    Returns:
        bool: True if valid ADO URL, False otherwise
    """
    return parse_ado_url(url) is not None


# Test the parser
if __name__ == "__main__":
    # Test URLs
    test_urls = [
        "https://dev.azure.com/TR-Legal-Cobalt/Legal%20Cobalt%20Backlog/_workitems/edit/12345",
        "https://dev.azure.com/TR-Legal-Cobalt/Legal%20Cobalt%20Backlog/_queries/query-edit/d1fd165c-1e4c-4642-a10b-61b402c60da4/",
        "https://dev.azure.com/TR-Legal-Cobalt/Legal%20Cobalt%20Backlog/_boards/board/t/Stories/?workitem=67890",
        "https://dev.azure.com/MyOrg/MyProject/_backlogs/backlog/Stories?workitem=111",
    ]

    print("Testing ADO URL Parser\n" + "="*60)
    for url in test_urls:
        print(f"\nURL: {url}")
        result = parse_ado_url(url)
        if result:
            print(f"  Organization: {result['organization']}")
            print(f"  Project: {result['project']}")
            print(f"  Type: {result['type']}")
            print(f"  Work Item ID: {result['work_item_id']}")
        else:
            print("  Invalid ADO URL")
