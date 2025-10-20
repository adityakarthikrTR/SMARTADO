"""
SmartADO - AI-Powered Azure DevOps Work Item Analyzer

A Streamlit web application that analyzes Azure DevOps work items and provides
AI-generated summaries and technical solutions using LiteLLM.
"""

import streamlit as st
import os
from dotenv import load_dotenv
from ado_parser import parse_ado_url
from ado_client import AzureDevOpsClient
from ai_analyzer import WorkItemAnalyzer
from chatbot import WorkItemChatbot
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="SmartADO - AI Work Item Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ADO-like styling
st.markdown("""
<style>
    /* Azure DevOps color scheme */
    :root {
        --ado-blue: #0078d4;
        --ado-dark-blue: #106ebe;
        --ado-light-gray: #f3f2f1;
        --ado-border: #e1dfdd;
    }

    /* Main container */
    .main {
        background-color: #ffffff;
    }

    /* Work item card */
    .work-item-card {
        background-color: white;
        border: 1px solid var(--ado-border);
        border-radius: 4px;
        padding: 16px;
        margin: 10px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Work item type badge */
    .wi-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    }

    .wi-epic { background-color: #ff6b00; color: white; }
    .wi-feature { background-color: #773b93; color: white; }
    .wi-story { background-color: #009ccc; color: white; }
    .wi-task { background-color: #f2cb1d; color: black; }
    .wi-bug { background-color: #cc293d; color: white; }

    /* State badge */
    .state-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }

    .state-new { background-color: #e1dfdd; color: #323130; }
    .state-active { background-color: #0078d4; color: white; }
    .state-resolved { background-color: #498205; color: white; }
    .state-closed { background-color: #8a8886; color: white; }

    /* Title styling */
    .wi-title {
        font-size: 20px;
        font-weight: 600;
        color: #323130;
        margin: 8px 0;
    }

    /* Section headers */
    .section-header {
        background-color: var(--ado-light-gray);
        padding: 8px 12px;
        border-left: 3px solid var(--ado-blue);
        font-weight: 600;
        margin: 16px 0 8px 0;
    }

    /* AI output containers */
    .ai-summary {
        background-color: #fff4ce;
        border-left: 4px solid #f2cb1d;
        padding: 16px;
        margin: 10px 0;
        border-radius: 4px;
    }

    .ai-solution {
        background-color: #e6f4ff;
        border-left: 4px solid #0078d4;
        padding: 16px;
        margin: 10px 0;
        border-radius: 4px;
    }

    /* Hierarchy list */
    .hierarchy-item {
        padding: 8px;
        margin: 4px 0;
        border-left: 2px solid var(--ado-border);
        padding-left: 12px;
    }
</style>
""", unsafe_allow_html=True)


def initialize_clients():
    """Initialize Azure DevOps and AI clients"""
    if 'ado_client' not in st.session_state:
        st.session_state.ado_client = AzureDevOpsClient(
            organization=os.getenv('ADO_ORGANIZATION'),
            project=os.getenv('ADO_PROJECT'),
            pat=os.getenv('ADO_PAT')
        )

    if 'ai_analyzer' not in st.session_state:
        st.session_state.ai_analyzer = WorkItemAnalyzer(
            api_base=os.getenv('LITELLM_API_BASE'),
            api_key=os.getenv('LITELLM_API_KEY'),
            model=os.getenv('LITELLM_MODEL', 'gpt-4')
        )

    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = WorkItemChatbot(
            api_base=os.getenv('LITELLM_API_BASE'),
            api_key=os.getenv('LITELLM_API_KEY'),
            model=os.getenv('LITELLM_MODEL', 'gpt-4')
        )


def get_badge_class(work_item_type: str) -> str:
    """Get CSS class for work item type badge"""
    type_lower = work_item_type.lower()
    if 'epic' in type_lower:
        return 'wi-epic'
    elif 'feature' in type_lower:
        return 'wi-feature'
    elif 'story' in type_lower or 'user story' in type_lower:
        return 'wi-story'
    elif 'task' in type_lower:
        return 'wi-task'
    elif 'bug' in type_lower:
        return 'wi-bug'
    else:
        return 'wi-task'


def get_state_badge_class(state: str) -> str:
    """Get CSS class for state badge"""
    state_lower = state.lower()
    if 'new' in state_lower:
        return 'state-new'
    elif 'active' in state_lower:
        return 'state-active'
    elif 'resolved' in state_lower or 'done' in state_lower:
        return 'state-resolved'
    elif 'closed' in state_lower:
        return 'state-closed'
    else:
        return 'state-new'


def render_work_item_card(work_item: dict, show_details: bool = True):
    """Render a work item in ADO-style card"""
    fields = work_item.get('fields', {})
    wi_id = work_item.get('id')
    wi_type = fields.get('System.WorkItemType', 'Unknown')
    wi_title = fields.get('System.Title', 'Untitled')
    wi_state = fields.get('System.State', 'Unknown')
    wi_assigned = fields.get('System.AssignedTo', {})

    assigned_name = wi_assigned.get('displayName', 'Unassigned') if isinstance(wi_assigned, dict) else str(wi_assigned)

    # Create card HTML
    type_badge_class = get_badge_class(wi_type)
    state_badge_class = get_state_badge_class(wi_state)

    card_html = f"""
    <div class="work-item-card">
        <div>
            <span class="wi-badge {type_badge_class}">{wi_type}</span>
            <span class="state-badge {state_badge_class}">{wi_state}</span>
            <span style="color: #605e5c; font-size: 14px;">#{wi_id}</span>
        </div>
        <div class="wi-title">{wi_title}</div>
        <div style="color: #605e5c; font-size: 14px; margin-top: 4px;">
            👤 {assigned_name}
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    if show_details:
        # Description
        description = fields.get('System.Description', '')
        if description:
            with st.expander("📝 Description", expanded=False):
                st.markdown(description, unsafe_allow_html=True)

        # Acceptance Criteria
        ac = fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '') or fields.get('System.AcceptanceCriteria', '')
        if ac:
            with st.expander("✅ Acceptance Criteria", expanded=False):
                st.markdown(ac, unsafe_allow_html=True)

        # Tags
        tags = fields.get('System.Tags', '')
        if tags:
            st.markdown(f"**🏷️ Tags**: {tags}")


def collect_all_work_items(hierarchy):
    """Collect all work items from hierarchy (epics, stories, tasks)"""
    all_items = []

    # Add main item
    main_item = hierarchy['main']
    all_items.append(main_item)

    # Add parents
    for parent in hierarchy.get('parents', []):
        all_items.append(parent['data'])

    # Add children
    for child in hierarchy.get('children', []):
        all_items.append(child['data'])

    # Add related
    for related in hierarchy.get('related', []):
        all_items.append(related['data'])

    return all_items


def main():
    """Main application"""

    # Header
    st.title("🎯 SmartADO")
    st.markdown("**AI-Powered Azure DevOps Work Item Analyzer**")
    st.markdown("---")

    # Initialize clients
    try:
        initialize_clients()
    except Exception as e:
        st.error(f"⚠️ Configuration Error: {str(e)}")
        st.info("Please configure your `.env` file with Azure DevOps and LiteLLM credentials.")
        return

    # Initialize session state for selected work item
    if 'selected_work_item_id' not in st.session_state:
        st.session_state.selected_work_item_id = None

    # Initialize chat history per work item
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = {}

    # Initialize current solution
    if 'current_solution' not in st.session_state:
        st.session_state.current_solution = None

    # Initialize solution cache for all work items
    if 'solution_cache' not in st.session_state:
        st.session_state.solution_cache = {}  # Dictionary to cache solutions by work item ID

    # Sidebar
    with st.sidebar:
        st.header("📋 Configuration")
        st.markdown(f"**Organization**: {os.getenv('ADO_ORGANIZATION')}")
        st.markdown(f"**Project**: {os.getenv('ADO_PROJECT')}")
        st.markdown(f"**AI Model**: {os.getenv('LITELLM_MODEL', 'gpt-4')}")

        st.markdown("---")
        st.header("ℹ️ How to Use")
        st.markdown("""
        1. Paste an Azure DevOps work item URL
        2. Click **Analyze Work Item**
        3. View work item details and hierarchy
        4. Get AI-generated summary
        5. **Click on any Epic/Story** to see its solution
        """)

        st.markdown("---")
        st.markdown("**Supported Work Items**")
        st.markdown("- 📦 Epics")
        st.markdown("- 🎨 Features")
        st.markdown("- 📖 User Stories")
        st.markdown("- ✅ Tasks")
        st.markdown("- 🐛 Bugs")

    # Main input
    ado_url = st.text_input(
        "🔗 Paste Azure DevOps URL",
        placeholder="https://dev.azure.com/TR-Legal-Cobalt/Legal%20Cobalt%20Backlog/_workitems/edit/12345",
        help="Enter any Azure DevOps work item URL (Epic, User Story, Task, Bug, etc.)"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_button = st.button("🔍 Analyze Work Item", type="primary")

    # Initialize hierarchy storage
    if 'current_hierarchy' not in st.session_state:
        st.session_state.current_hierarchy = None

    if analyze_button and ado_url:
        # Parse URL
        parsed = parse_ado_url(ado_url)

        if not parsed or not parsed.get('work_item_id'):
            st.error("❌ Invalid Azure DevOps URL. Please provide a valid work item URL.")
            return

        work_item_id = parsed['work_item_id']

        with st.spinner(f"🔄 Fetching work item #{work_item_id}..."):
            # Fetch work item
            hierarchy = st.session_state.ado_client.get_work_item_hierarchy(work_item_id)

            if not hierarchy or not hierarchy.get('main'):
                st.error(f"❌ Work item #{work_item_id} not found or access denied.")
                st.info("Please check:\n- Work item ID is correct\n- You have access to this work item\n- Your Azure DevOps PAT is valid")
                return

        # Store in session state
        st.session_state.current_hierarchy = hierarchy
        st.session_state.current_work_item_id = work_item_id

    # Display the work item analysis if hierarchy exists in session state
    if st.session_state.current_hierarchy:
        hierarchy = st.session_state.current_hierarchy

        # Display main work item
        st.markdown("## 📄 Work Item Details")
        render_work_item_card(hierarchy['main'], show_details=True)

        # Display hierarchy
        st.markdown("## 🌳 Work Item Hierarchy")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**⬆️ Parents ({len(hierarchy['parents'])})**")
            if hierarchy['parents']:
                for parent in hierarchy['parents']:
                    render_work_item_card(parent['data'], show_details=False)
            else:
                st.info("No parent work items")

        with col2:
            st.markdown(f"**⬇️ Children ({len(hierarchy['children'])})**")
            if hierarchy['children']:
                for child in hierarchy['children']:
                    render_work_item_card(child['data'], show_details=False)
            else:
                st.info("No child work items")

        with col3:
            st.markdown(f"**🔗 Related ({len(hierarchy['related'])})**")
            if hierarchy['related']:
                for related in hierarchy['related']:
                    render_work_item_card(related['data'], show_details=False)
            else:
                st.info("No related work items")

        # AI Analysis Section
        st.markdown("---")
        st.markdown("## 🤖 AI Analysis")

        # Get work item state
        main_state = hierarchy['main'].get('fields', {}).get('System.State', 'Unknown')
        is_closed = main_state.lower() in ['closed', 'done', 'resolved', 'completed']

        # Summary - What is this ADO about?
        st.markdown("### 📊 What is this Work Item About?")
        with st.spinner("🧠 AI is analyzing the work item..."):
            summary = st.session_state.ai_analyzer.generate_summary(
                hierarchy['main'],
                hierarchy
            )

        st.markdown(f'<div class="ai-summary">{summary}</div>', unsafe_allow_html=True)

        # Solution - Always show BOTH actual (if closed) AND AI solution
        st.markdown("---")

        # For CLOSED items - show actual solution from ADO
        if is_closed:
            st.markdown("### ✅ Actual Solution from Team (Work Item is Closed)")
            st.info("📋 This work item is completed. Here's what the team documented:")

            # Get actual solution from ADO
            with st.spinner("📥 Fetching actual solution from ADO..."):
                actual_solution = st.session_state.ado_client.get_resolved_solution(hierarchy['main'])

            if actual_solution and actual_solution != "No detailed solution information available in ADO.":
                st.markdown(f'<div class="ai-solution">{actual_solution}</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ No solution details found in ADO comments or resolution fields.")

            st.markdown("---")

        # ALWAYS show AI solution (for both open and closed items)
        st.markdown("### 💡 AI-Generated Implementation Solution")
        if is_closed:
            st.success("🤖 Here's the AI's recommended approach (for reference):")
        else:
            st.success("🚀 Here's how to implement this work item:")

        with st.spinner("🤖 AI is generating technical solution..."):
            solution = st.session_state.ai_analyzer.generate_solution(
                hierarchy['main'],
                hierarchy
            )

        st.markdown(f'<div class="ai-solution">{solution}</div>', unsafe_allow_html=True)

        # Download solution
        st.download_button(
            label="📥 Download Solution as Text File",
            data=solution,
            file_name=f"solution_{hierarchy['main'].get('id')}.txt",
            mime="text/plain"
        )

        # Store solution in session for chatbot
        st.session_state.current_solution = solution
        st.session_state.current_work_item = hierarchy['main']

        # Chatbot Section - Using Streamlit's Native Chat Interface
        st.markdown("---")
        st.markdown("## 💬 Chat with AI About This Work Item")
        st.info("💡 Ask questions about the implementation, request code examples, or get clarifications!")

        # Initialize chat history for current work item
        main_wi_id = hierarchy['main'].get('id')
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = {}
        if main_wi_id not in st.session_state.chat_messages:
            st.session_state.chat_messages[main_wi_id] = []

        # Display chat messages using Streamlit's native chat interface
        for message in st.session_state.chat_messages[main_wi_id]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Show suggested questions if no chat history
        if not st.session_state.chat_messages[main_wi_id]:
            st.markdown("### 💡 Try asking:")
            st.caption("• How do I implement step 2?")
            st.caption("• What libraries or frameworks should I use?")
            st.caption("• Can you provide code examples?")
            st.caption("• What are the potential challenges?")
            st.caption("• How should I test this?")

        # Chat input using Streamlit's native chat_input
        if prompt := st.chat_input("Ask a question about this work item..."):
            # Add user message to chat history
            st.session_state.chat_messages[main_wi_id].append({"role": "user", "content": prompt})

            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        # Call LiteLLM
                        from litellm import completion

                        # Build ULTRA COMPREHENSIVE context with ALL work item details
                        fields = hierarchy['main'].get('fields', {})
                        wi_state = fields.get('System.State', 'Unknown')
                        wi_type = fields.get('System.WorkItemType', 'Unknown')
                        wi_title = fields.get('System.Title', 'Untitled')
                        wi_description = fields.get('System.Description', 'No description')

                        # People fields
                        wi_assigned = fields.get('System.AssignedTo', {})
                        assigned_name = wi_assigned.get('displayName', 'Unassigned') if isinstance(wi_assigned, dict) else 'Unassigned'

                        wi_created_by = fields.get('System.CreatedBy', {})
                        created_by_name = wi_created_by.get('displayName', 'Unknown') if isinstance(wi_created_by, dict) else 'Unknown'

                        wi_changed_by = fields.get('System.ChangedBy', {})
                        changed_by_name = wi_changed_by.get('displayName', 'Unknown') if isinstance(wi_changed_by, dict) else 'Unknown'

                        wi_closed_by = fields.get('Microsoft.VSTS.Common.ClosedBy', {}) or fields.get('System.ClosedBy', {})
                        closed_by_name = wi_closed_by.get('displayName', 'N/A') if isinstance(wi_closed_by, dict) else 'N/A'

                        wi_resolved_by = fields.get('Microsoft.VSTS.Common.ResolvedBy', {}) or fields.get('System.ResolvedBy', {})
                        resolved_by_name = wi_resolved_by.get('displayName', 'N/A') if isinstance(wi_resolved_by, dict) else 'N/A'

                        # Date fields
                        created_date = fields.get('System.CreatedDate', 'Unknown')
                        changed_date = fields.get('System.ChangedDate', 'Unknown')
                        closed_date = fields.get('Microsoft.VSTS.Common.ClosedDate', 'N/A') or fields.get('System.ClosedDate', 'N/A')
                        resolved_date = fields.get('Microsoft.VSTS.Common.ResolvedDate', 'N/A') or fields.get('System.ResolvedDate', 'N/A')

                        # Other metadata
                        priority = fields.get('Microsoft.VSTS.Common.Priority', 'N/A')
                        effort = fields.get('Microsoft.VSTS.Scheduling.Effort', 'N/A')
                        story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 'N/A')
                        iteration = fields.get('System.IterationPath', 'N/A')
                        area = fields.get('System.AreaPath', 'N/A')
                        tags = fields.get('System.Tags', 'None')
                        reason = fields.get('System.Reason', 'N/A')

                        # Check if closed
                        is_closed = wi_state.lower() in ['closed', 'done', 'resolved', 'completed']

                        # Build COMPLETE HIERARCHY context
                        hierarchy_context = ""

                        # Add Parent Epics/Features
                        if hierarchy.get('parents'):
                            hierarchy_context += "\n\n🔼 PARENT WORK ITEMS:\n"
                            for idx, parent in enumerate(hierarchy['parents'][:3], 1):  # Limit to top 3
                                p_fields = parent['data'].get('fields', {})
                                p_id = parent['data'].get('id')
                                p_type = p_fields.get('System.WorkItemType', 'Unknown')
                                p_title = p_fields.get('System.Title', 'Untitled')
                                p_state = p_fields.get('System.State', 'Unknown')
                                p_desc = p_fields.get('System.Description', 'No description')[:300]
                                hierarchy_context += f"\n{idx}. {p_type} #{p_id}: {p_title}\n   State: {p_state}\n   Description: {p_desc}\n"

                        # Add Child Stories/Tasks
                        if hierarchy.get('children'):
                            hierarchy_context += "\n\n🔽 CHILD WORK ITEMS:\n"
                            for idx, child in enumerate(hierarchy['children'][:5], 1):  # Limit to top 5
                                c_fields = child['data'].get('fields', {})
                                c_id = child['data'].get('id')
                                c_type = c_fields.get('System.WorkItemType', 'Unknown')
                                c_title = c_fields.get('System.Title', 'Untitled')
                                c_state = c_fields.get('System.State', 'Unknown')
                                c_desc = c_fields.get('System.Description', 'No description')[:300]
                                hierarchy_context += f"\n{idx}. {c_type} #{c_id}: {c_title}\n   State: {c_state}\n   Description: {c_desc}\n"

                        # Add Related Items
                        if hierarchy.get('related'):
                            hierarchy_context += "\n\n🔗 RELATED WORK ITEMS:\n"
                            for idx, related in enumerate(hierarchy['related'][:3], 1):  # Limit to top 3
                                r_fields = related['data'].get('fields', {})
                                r_id = related['data'].get('id')
                                r_type = r_fields.get('System.WorkItemType', 'Unknown')
                                r_title = r_fields.get('System.Title', 'Untitled')
                                r_state = r_fields.get('System.State', 'Unknown')
                                hierarchy_context += f"\n{idx}. {r_type} #{r_id}: {r_title}\n   State: {r_state}\n"

                        # Build context with ALL details INCLUDING HIERARCHY
                        context = f"""
================================
📌 MAIN WORK ITEM #{main_wi_id}
================================
Type: {wi_type}
Title: {wi_title}
State: {wi_state} {"(CLOSED - This work item is completed)" if is_closed else "(OPEN - This work item is still in progress)"}
Priority: {priority}
Effort/Story Points: {effort if effort != 'N/A' else story_points}

👤 PEOPLE:
- Assigned To: {assigned_name}
- Created By: {created_by_name}
- Last Changed By: {changed_by_name}
- Closed By: {closed_by_name}
- Resolved By: {resolved_by_name}

📅 DATES:
- Created: {created_date}
- Last Changed: {changed_date}
- Closed: {closed_date}
- Resolved: {resolved_date}

📋 DETAILS:
- Iteration: {iteration}
- Area: {area}
- Tags: {tags}
- Reason: {reason}
- Description: {wi_description[:500]}

💡 AI-Generated Solution:
{solution[:1500]}

================================
🌳 WORK ITEM HIERARCHY
================================
{hierarchy_context if hierarchy_context else "No parent, child, or related items."}

================================
📊 HIERARCHY SUMMARY
================================
- Total Parents: {len(hierarchy.get('parents', []))}
- Total Children: {len(hierarchy.get('children', []))}
- Total Related: {len(hierarchy.get('related', []))}
"""

                        # Create messages with ULTRA ENHANCED system prompt including hierarchy
                        messages = [
                            {"role": "system", "content": f"""You are an ULTRA-INTELLIGENT AI assistant with COMPLETE ACCESS to Azure DevOps work item data INCLUDING THE ENTIRE WORK ITEM HIERARCHY.

🎯 YOUR FULL CAPABILITIES:
You have COMPLETE INTELLIGENCE about:
✅ MAIN WORK ITEM: Current state, who created/modified/closed it, all dates, priority, effort, complete description and solution
✅ PARENT EPICS/FEATURES: All parent work items with their titles, states, and descriptions
✅ CHILD STORIES/TASKS: All child work items with their titles, states, and descriptions
✅ RELATED ITEMS: All related work items in the hierarchy
✅ METADATA: Iteration, area, tags, assignments, and all other fields

📊 COMPLETE WORK ITEM CONTEXT WITH HIERARCHY:
{context}

✨ HOW TO INTELLIGENTLY ANSWER:
1. **WHO questions** (who closed, who created, who is assigned): Refer to the PEOPLE section
2. **WHEN questions** (when closed, when created, dates): Refer to the DATES section
3. **STATUS/STATE questions** (is it closed, what's the status): Check the State field
4. **PRIORITY/EFFORT questions**: Refer to the Priority and Effort/Story Points fields
5. **IMPLEMENTATION questions** (how to implement, code examples): Use the AI-Generated Solution
6. **HIERARCHY questions** (what epics, what stories, parent/child items): Use the WORK ITEM HIERARCHY section
7. **RELATED ITEMS questions** (associated stories, related tasks): Use PARENT/CHILD/RELATED sections
8. **VELOCITY/METRICS questions**: Calculate using effort/story points and dates from hierarchy
9. **GENERAL questions about the project**: Synthesize information from the entire hierarchy

⚡ CRITICAL RULES:
- Answer based on ACTUAL DATA from the context above
- Be SPECIFIC: Mention names, dates, work item IDs, and details
- For hierarchy questions: Reference specific parent/child/related items by ID and title
- If asked about related items, list them with their IDs, types, titles, and states
- Calculate velocity/metrics using the effort points and dates from ALL related items
- If something is not in the context, clearly state "This information is not available in the current context"
- Always cite your sources (e.g., "According to the Closed By field, this was closed by John Doe on 2024-01-15")

💡 EXAMPLES OF INTELLIGENT RESPONSES:
- "Is this closed?" → "Yes, this work item is CLOSED. According to the State field, it was closed on [date] by [name]."
- "What are the related stories?" → "There are 3 related items: 1) Story #12345: [title] (State: Active), 2) Story #12346: [title] (State: Closed)..."
- "What's the parent epic?" → "The parent epic is Epic #10000: [title] (State: Active). Description: [excerpt from parent description]"
- "What's the velocity?" → "Based on the child items, the total effort is [X] story points completed over [Y] days, giving a velocity of [Z] points/day."

Now answer the user's question intelligently and comprehensively using ALL the context above."""}
                        ]

                        # Add chat history (last 6 messages for context)
                        for msg in st.session_state.chat_messages[main_wi_id][-6:]:
                            messages.append({"role": msg["role"], "content": msg["content"]})

                        # Get environment variables (already loaded at top of file)
                        litellm_model = os.getenv('LITELLM_MODEL', 'gpt-4')
                        litellm_base = os.getenv('LITELLM_API_BASE')
                        litellm_key = os.getenv('LITELLM_API_KEY')

                        # Call LiteLLM
                        response = completion(
                            model=litellm_model,
                            api_base=litellm_base,
                            api_key=litellm_key,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=800,
                            custom_llm_provider="openai"
                        )

                        ai_response = response.choices[0].message.content
                        st.markdown(ai_response)

                        # Add assistant response to chat history
                        st.session_state.chat_messages[main_wi_id].append({"role": "assistant", "content": ai_response})

                    except Exception as e:
                        error_message = f"❌ **Error:** {str(e)}\n\n**Troubleshooting:**\n- Connect to TR VPN\n- Check LiteLLM endpoint\n- Verify .env configuration"
                        st.error(error_message)
                        st.session_state.chat_messages[main_wi_id].append({"role": "assistant", "content": error_message})

        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_messages[main_wi_id] = []
            st.rerun()

        # Clickable Work Items List Section (Optional - for exploring other items)
        st.markdown("---")
        st.markdown("## 📋 All Associated Work Items")
        st.info("👆 Click on any work item below to see its details and generate a separate solution")

        # Collect all work items
        all_work_items = collect_all_work_items(hierarchy)

        # Categorize work items
        epics = [wi for wi in all_work_items if wi.get('fields', {}).get('System.WorkItemType', '').lower() == 'epic']
        features = [wi for wi in all_work_items if wi.get('fields', {}).get('System.WorkItemType', '').lower() == 'feature']
        user_stories = [wi for wi in all_work_items if wi.get('fields', {}).get('System.WorkItemType', '').lower() in ['user story', 'product backlog item']]
        tasks = [wi for wi in all_work_items if wi.get('fields', {}).get('System.WorkItemType', '').lower() == 'task']
        bugs = [wi for wi in all_work_items if wi.get('fields', {}).get('System.WorkItemType', '').lower() == 'bug']

        # Create columns for organized display
        col1, col2 = st.columns(2)

        with col1:
            # Epics
            if epics:
                st.markdown(f"### 📦 Epics ({len(epics)})")
                for epic in epics:
                    wi_id = epic.get('id')
                    wi_title = epic.get('fields', {}).get('System.Title', 'Untitled')
                    wi_state = epic.get('fields', {}).get('System.State', 'Unknown')

                    if st.button(f"🔍 #{wi_id} - {wi_title[:40]}", key=f"epic_{wi_id}"):
                        st.session_state.selected_work_item_id = wi_id
                        st.session_state.selected_work_item = epic
                        st.rerun()

                    st.caption(f"State: {wi_state}")
                    st.markdown("---")

            # User Stories
            if user_stories:
                st.markdown(f"### 📖 User Stories ({len(user_stories)})")
                for story in user_stories:
                    wi_id = story.get('id')
                    wi_title = story.get('fields', {}).get('System.Title', 'Untitled')
                    wi_state = story.get('fields', {}).get('System.State', 'Unknown')

                    if st.button(f"🔍 #{wi_id} - {wi_title[:40]}", key=f"story_{wi_id}"):
                        st.session_state.selected_work_item_id = wi_id
                        st.session_state.selected_work_item = story
                        st.rerun()

                    st.caption(f"State: {wi_state}")
                    st.markdown("---")

        with col2:
            # Features
            if features:
                st.markdown(f"### 🎨 Features ({len(features)})")
                for feature in features:
                    wi_id = feature.get('id')
                    wi_title = feature.get('fields', {}).get('System.Title', 'Untitled')
                    wi_state = feature.get('fields', {}).get('System.State', 'Unknown')

                    if st.button(f"🔍 #{wi_id} - {wi_title[:40]}", key=f"feature_{wi_id}"):
                        st.session_state.selected_work_item_id = wi_id
                        st.session_state.selected_work_item = feature
                        st.rerun()

                    st.caption(f"State: {wi_state}")
                    st.markdown("---")

            # Tasks
            if tasks:
                st.markdown(f"### ✅ Tasks ({len(tasks)})")
                for task in tasks:
                    wi_id = task.get('id')
                    wi_title = task.get('fields', {}).get('System.Title', 'Untitled')
                    wi_state = task.get('fields', {}).get('System.State', 'Unknown')

                    if st.button(f"🔍 #{wi_id} - {wi_title[:40]}", key=f"task_{wi_id}"):
                        st.session_state.selected_work_item_id = wi_id
                        st.session_state.selected_work_item = task
                        st.rerun()

                    st.caption(f"State: {wi_state}")
                    st.markdown("---")

            # Bugs
            if bugs:
                st.markdown(f"### 🐛 Bugs ({len(bugs)})")
                for bug in bugs:
                    wi_id = bug.get('id')
                    wi_title = bug.get('fields', {}).get('System.Title', 'Untitled')
                    wi_state = bug.get('fields', {}).get('System.State', 'Unknown')

                    if st.button(f"🔍 #{wi_id} - {wi_title[:40]}", key=f"bug_{wi_id}"):
                        st.session_state.selected_work_item_id = wi_id
                        st.session_state.selected_work_item = bug
                        st.rerun()

                    st.caption(f"State: {wi_state}")
                    st.markdown("---")

        # Display AI Solution for Selected Work Item (PERSISTENT PANEL)
        if st.session_state.selected_work_item_id:
            st.markdown("---")
            st.markdown("## 💡 AI-Generated Technical Solution & Chat")

            selected_wi = st.session_state.selected_work_item
            wi_id = selected_wi.get('id')
            wi_type = selected_wi.get('fields', {}).get('System.WorkItemType', 'Unknown')
            wi_title = selected_wi.get('fields', {}).get('System.Title', 'Untitled')

            st.success(f"💡 Analyzing **{wi_type} #{wi_id}**: {wi_title}")

            # Create two columns: Solution (left) and Chat (right)
            solution_col, chat_col = st.columns([1.2, 1])

            with solution_col:
                st.markdown("### 📖 Implementation Solution")

                # Show work item details
                with st.expander("📄 View Work Item Details", expanded=False):
                    render_work_item_card(selected_wi, show_details=True)

                # Generate and display solution with INTELLIGENT CACHING
                # Check if solution is already cached
                if wi_id in st.session_state.solution_cache:
                    # Use cached solution - INSTANT LOAD!
                    solution = st.session_state.solution_cache[wi_id]
                    st.success(f"⚡ Loaded cached solution for #{wi_id} instantly!")
                else:
                    # Generate new solution and cache it
                    with st.spinner(f"🤖 AI is analyzing {wi_type} #{wi_id} and generating solution..."):
                        solution = st.session_state.ai_analyzer.generate_solution(
                            selected_wi,
                            {'main': selected_wi, 'parents': [], 'children': [], 'related': []}
                        )
                        # Cache the solution for future instant access
                        st.session_state.solution_cache[wi_id] = solution
                        st.session_state.current_solution = solution
                        st.session_state.last_solution_wi_id = wi_id

                # Display solution in persistent container
                st.markdown(f'<div class="ai-solution">{solution}</div>', unsafe_allow_html=True)

                # Download solution as text file
                st.download_button(
                    label="📥 Download Solution",
                    data=solution,
                    file_name=f"solution_{wi_id}.txt",
                    mime="text/plain",
                    key=f"download_{wi_id}"
                )

            with chat_col:
                st.markdown("### 💬 Ask Questions")
                st.info("Chat with AI about this work item and solution")

                # Initialize chat history for this work item
                if wi_id not in st.session_state.chat_history:
                    st.session_state.chat_history[wi_id] = []

                # Display chat history
                chat_container = st.container()
                with chat_container:
                    if st.session_state.chat_history[wi_id]:
                        for msg in st.session_state.chat_history[wi_id]:
                            if msg['role'] == 'user':
                                st.markdown(f"**👤 You:** {msg['content']}")
                            else:
                                st.markdown(f"**🤖 AI:** {msg['content']}")
                            st.markdown("---")
                    else:
                        st.caption("💡 Ask questions like:")
                        st.caption("- How do I implement step 2?")
                        st.caption("- What libraries should I use?")
                        st.caption("- Can you provide code examples?")
                        st.caption("- What are the potential issues?")

                # Chat input
                user_question = st.text_area(
                    "Your question:",
                    placeholder="e.g., Can you explain how to implement the authentication part?",
                    key=f"chat_input_{wi_id}",
                    height=100
                )

                col_send, col_clear = st.columns([1, 1])

                with col_send:
                    if st.button("📤 Send", key=f"send_{wi_id}", type="primary"):
                        if user_question.strip():
                            with st.spinner("🤖 AI is thinking..."):
                                # Get AI response
                                ai_response = st.session_state.chatbot.chat(
                                    work_item=selected_wi,
                                    solution=solution,
                                    chat_history=st.session_state.chat_history[wi_id],
                                    user_message=user_question
                                )

                                # Update chat history
                                st.session_state.chat_history[wi_id].append({
                                    'role': 'user',
                                    'content': user_question
                                })
                                st.session_state.chat_history[wi_id].append({
                                    'role': 'assistant',
                                    'content': ai_response
                                })

                                st.rerun()

                with col_clear:
                    if st.button("🗑️ Clear Chat", key=f"clear_chat_{wi_id}"):
                        st.session_state.chat_history[wi_id] = []
                        st.rerun()

            # Clear selection button
            st.markdown("---")
            if st.button("🔄 Select Another Work Item"):
                st.session_state.selected_work_item_id = None
                st.session_state.selected_work_item = None
                st.session_state.current_solution = None
                st.rerun()

        # Raw JSON view (collapsible)
        with st.expander("🔍 View Raw JSON Data"):
            st.json(hierarchy['main'])


if __name__ == "__main__":
    main()
