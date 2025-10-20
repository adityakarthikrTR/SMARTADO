"""
AI Analyzer using LiteLLM

Generates summaries and technical solutions for Azure DevOps work items.
"""

import os
from typing import Dict, List
from litellm import completion
import json


class WorkItemAnalyzer:
    """AI-powered analyzer for Azure DevOps work items"""

    def __init__(self, api_base: str, api_key: str, model: str = "gpt-4"):
        """
        Initialize the AI analyzer.

        Args:
            api_base: LiteLLM API base URL
            api_key: LiteLLM API key
            model: Model to use (default: gpt-4)
        """
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

        # Set environment variables for LiteLLM
        os.environ['LITELLM_API_BASE'] = api_base
        os.environ['LITELLM_API_KEY'] = api_key

    def generate_summary(self, work_item: Dict, hierarchy: Dict) -> str:
        """
        Generate an AI summary of a work item and its hierarchy.

        Args:
            work_item: Main work item data
            hierarchy: Hierarchical structure (parents, children, related)

        Returns:
            str: AI-generated summary
        """
        # Prepare context for the AI
        context = self._prepare_context(work_item, hierarchy)

        system_prompt = """You are an Azure DevOps expert analyzing work items.
Your task is to provide a clear, concise summary of the work item and its relationships.

Focus on:
1. What is the main objective/goal?
2. Current state and progress
3. Key dependencies (parent/child relationships)
4. Important details from description and acceptance criteria
5. Any risks or blockers mentioned

Format your response in clear sections with bullet points."""

        user_prompt = f"""Analyze this Azure DevOps work item and provide a comprehensive summary:

{context}

Provide a summary that helps the team quickly understand what this work item is about and its current status."""

        try:
            response = completion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}\n\nPlease check your LiteLLM connection and VPN status."

    def generate_solution(self, work_item: Dict, hierarchy: Dict) -> str:
        """
        Generate technical solution/implementation guidance for a work item.

        Args:
            work_item: Main work item data
            hierarchy: Hierarchical structure

        Returns:
            str: AI-generated technical solution
        """
        context = self._prepare_context(work_item, hierarchy)

        work_item_type = work_item.get('fields', {}).get('System.WorkItemType', 'Unknown')

        # Customize prompt based on work item type
        if work_item_type == 'Epic':
            focus = "high-level architecture and implementation strategy across features"
        elif work_item_type == 'User Story':
            focus = "detailed implementation approach, code structure, and testing strategy"
        elif work_item_type == 'Task':
            focus = "specific implementation steps and code examples"
        elif work_item_type == 'Bug':
            focus = "root cause analysis and fix implementation"
        else:
            focus = "implementation approach and technical considerations"

        system_prompt = f"""You are a senior software engineer providing technical implementation guidance.
Your task is to suggest a practical solution for the work item, focusing on {focus}.

Provide:
1. **Technical Approach**: High-level solution strategy
2. **Implementation Steps**: Detailed steps to implement
3. **Code Considerations**: Key technical decisions and patterns
4. **Testing Strategy**: How to test/validate the solution
5. **Potential Challenges**: Risks and how to mitigate them

Be specific, practical, and actionable. Use clear formatting with sections and bullet points."""

        user_prompt = f"""Provide a technical solution for this work item:

{context}

Generate a detailed implementation plan that a developer can follow."""

        try:
            response = completion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )

            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating solution: {str(e)}\n\nPlease check your LiteLLM connection and VPN status."

    def generate_user_story_solutions(self, user_stories: List[Dict]) -> Dict[int, str]:
        """
        Generate solutions for multiple user stories.

        Args:
            user_stories: List of user story work items

        Returns:
            dict: Map of work item ID to solution
        """
        solutions = {}

        for story in user_stories:
            work_item_id = story.get('id')
            solution = self.generate_solution(story, {'main': story, 'parents': [], 'children': [], 'related': []})
            solutions[work_item_id] = solution

        return solutions

    def _prepare_context(self, work_item: Dict, hierarchy: Dict) -> str:
        """
        Prepare context string from work item and hierarchy.

        Args:
            work_item: Main work item
            hierarchy: Hierarchy data

        Returns:
            str: Formatted context for AI
        """
        fields = work_item.get('fields', {})

        context_parts = []

        # Main work item info
        context_parts.append(f"**Work Item ID**: {work_item.get('id')}")
        context_parts.append(f"**Type**: {fields.get('System.WorkItemType', 'Unknown')}")
        context_parts.append(f"**Title**: {fields.get('System.Title', 'Untitled')}")
        context_parts.append(f"**State**: {fields.get('System.State', 'Unknown')}")

        # Description
        description = fields.get('System.Description', '')
        if description:
            # Strip HTML tags for cleaner context
            import re
            clean_description = re.sub(r'<[^>]+>', '', description)
            context_parts.append(f"\n**Description**:\n{clean_description[:1000]}")

        # Acceptance Criteria
        acceptance_criteria = (fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '') or
                               fields.get('System.AcceptanceCriteria', ''))
        if acceptance_criteria:
            clean_ac = re.sub(r'<[^>]+>', '', acceptance_criteria)
            context_parts.append(f"\n**Acceptance Criteria**:\n{clean_ac[:1000]}")

        # Parent work items
        if hierarchy.get('parents'):
            context_parts.append("\n**Parent Work Items**:")
            for parent in hierarchy['parents'][:3]:  # Limit to 3
                parent_data = parent.get('data', {})
                parent_fields = parent_data.get('fields', {})
                context_parts.append(f"  - [{parent_data.get('id')}] {parent_fields.get('System.Title', 'Untitled')}")

        # Child work items
        if hierarchy.get('children'):
            context_parts.append("\n**Child Work Items**:")
            for child in hierarchy['children'][:5]:  # Limit to 5
                child_data = child.get('data', {})
                child_fields = child_data.get('fields', {})
                context_parts.append(f"  - [{child_data.get('id')}] {child_fields.get('System.WorkItemType', 'Unknown')}: {child_fields.get('System.Title', 'Untitled')}")

        # Tags
        tags = fields.get('System.Tags', '')
        if tags:
            context_parts.append(f"\n**Tags**: {tags}")

        return "\n".join(context_parts)


# Test the analyzer
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize analyzer
    analyzer = WorkItemAnalyzer(
        api_base=os.getenv('LITELLM_API_BASE'),
        api_key=os.getenv('LITELLM_API_KEY'),
        model=os.getenv('LITELLM_MODEL', 'gpt-4')
    )

    # Test with sample work item
    sample_work_item = {
        'id': 12345,
        'fields': {
            'System.WorkItemType': 'User Story',
            'System.Title': 'Implement user authentication',
            'System.State': 'Active',
            'System.Description': 'As a user, I want to log in securely so that I can access my account.',
            'Microsoft.VSTS.Common.AcceptanceCriteria': '- User can log in with email and password\n- Password is encrypted\n- Session is maintained'
        }
    }

    sample_hierarchy = {
        'main': sample_work_item,
        'parents': [],
        'children': [],
        'related': []
    }

    print("Generating summary...")
    summary = analyzer.generate_summary(sample_work_item, sample_hierarchy)
    print(summary)

    print("\n" + "="*60 + "\n")

    print("Generating solution...")
    solution = analyzer.generate_solution(sample_work_item, sample_hierarchy)
    print(solution)
