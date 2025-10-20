"""
Interactive Chatbot for Azure DevOps Work Items

Allows users to ask follow-up questions about work items and their solutions.
"""

import os
from litellm import completion
from typing import List, Dict


class WorkItemChatbot:
    """Interactive chatbot for work item discussions"""

    def __init__(self, api_base: str, api_key: str, model: str = "gpt-4"):
        """
        Initialize the chatbot.

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

    def chat(self, work_item: Dict, solution: str, chat_history: List[Dict], user_message: str) -> str:
        """
        Process a chat message in the context of a work item.

        Args:
            work_item: The work item data
            solution: The generated solution for the work item
            chat_history: Previous chat messages
            user_message: New user message

        Returns:
            str: AI response
        """
        # Build context
        context = self._build_context(work_item, solution)

        # Create system prompt
        system_prompt = f"""You are an AI assistant helping a developer understand and implement an Azure DevOps work item.

CONTEXT:
{context}

Your role:
- Answer questions about the work item and its implementation
- Clarify technical details from the solution
- Provide code examples when requested
- Suggest best practices and alternatives
- Help troubleshoot implementation issues

Be conversational, helpful, and technically accurate. Keep responses concise but thorough."""

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history (limit to last 10 messages for context)
        for msg in chat_history[-10:]:
            messages.append(msg)

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        try:
            # Use LiteLLM with custom endpoint
            response = completion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                custom_llm_provider="openai"  # LiteLLM proxy acts as OpenAI-compatible endpoint
            )

            return response.choices[0].message.content

        except Exception as e:
            error_msg = str(e)
            return f"❌ **Chatbot Error:**\n\n{error_msg}\n\n**Troubleshooting:**\n- Ensure you're connected to Thomson Reuters VPN\n- Check if LiteLLM endpoint is accessible: {self.api_base}\n- Verify API key in .env file\n- Try refreshing the page"

    def _build_context(self, work_item: Dict, solution: str) -> str:
        """Build context from work item and solution"""
        fields = work_item.get('fields', {})

        context_parts = []

        # Work item details
        context_parts.append(f"Work Item ID: {work_item.get('id')}")
        context_parts.append(f"Type: {fields.get('System.WorkItemType', 'Unknown')}")
        context_parts.append(f"Title: {fields.get('System.Title', 'Untitled')}")
        context_parts.append(f"State: {fields.get('System.State', 'Unknown')}")

        # Description
        description = fields.get('System.Description', '')
        if description:
            import re
            clean_desc = re.sub(r'<[^>]+>', '', description)
            context_parts.append(f"\nDescription: {clean_desc[:500]}")

        # Acceptance Criteria
        ac = fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '') or fields.get('System.AcceptanceCriteria', '')
        if ac:
            clean_ac = re.sub(r'<[^>]+>', '', ac)
            context_parts.append(f"\nAcceptance Criteria: {clean_ac[:500]}")

        # Add the generated solution
        context_parts.append(f"\n--- GENERATED SOLUTION ---\n{solution[:2000]}")

        return "\n".join(context_parts)


# Test the chatbot
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    chatbot = WorkItemChatbot(
        api_base=os.getenv('LITELLM_API_BASE'),
        api_key=os.getenv('LITELLM_API_KEY'),
        model=os.getenv('LITELLM_MODEL', 'gpt-4')
    )

    # Sample work item
    sample_work_item = {
        'id': 12345,
        'fields': {
            'System.WorkItemType': 'User Story',
            'System.Title': 'Implement user authentication',
            'System.State': 'Active',
            'System.Description': 'Add login functionality',
        }
    }

    sample_solution = "Use OAuth 2.0 for authentication. Implement JWT tokens..."

    chat_history = []

    print("Chatbot Test - Type 'quit' to exit\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break

        response = chatbot.chat(sample_work_item, sample_solution, chat_history, user_input)
        print(f"\nAI: {response}\n")

        # Update history
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": response})
