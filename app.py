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
from sprint_dashboard import SprintAnalytics, MultiSprintAnalytics
import json
import pandas as pd
from urllib.parse import quote
from typing import List, Dict

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


def collect_all_related_items(hierarchy, ado_client):
    """
    Collect all work items in the complete hierarchy tree including grandchildren.

    For Epic with Stories and Tasks, this returns:
    - The main work item (Epic)
    - All parents (if any)
    - All children (User Stories)
    - All grandchildren (Tasks under User Stories)
    - All related items (Bugs, dependencies)

    Args:
        hierarchy: Work item hierarchy dict
        ado_client: AzureDevOpsClient instance

    Returns:
        list: All related work items
    """
    all_items = []
    processed_ids = set()  # Avoid duplicates

    def add_item(item):
        """Add item if not already processed"""
        item_id = item.get('id')
        if item_id and item_id not in processed_ids:
            all_items.append(item)
            processed_ids.add(item_id)

    # Add main work item
    main_item = hierarchy['main']
    add_item(main_item)

    # Add all parents
    for parent in hierarchy.get('parents', []):
        add_item(parent['data'])

    # Add all children and their children (grandchildren)
    for child in hierarchy.get('children', []):
        child_data = child['data']
        add_item(child_data)

        # Fetch grandchildren (e.g., Tasks under User Story)
        try:
            child_id = child_data.get('id')
            if child_id:
                child_hierarchy = ado_client.get_work_item_hierarchy(child_id)
                for grandchild in child_hierarchy.get('children', []):
                    add_item(grandchild['data'])
        except:
            pass  # Skip if grandchild fetch fails

    # Add related items
    for related in hierarchy.get('related', []):
        add_item(related['data'])

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

    # Create tabs for different features
    tab1, tab2, tab3 = st.tabs(["🔍 Work Item Analyzer", "📊 Sprint Dashboard", "👤 Person Search"])

    # TAB 1: Work Item Analyzer (existing functionality)
    with tab1:
        render_work_item_analyzer()

    # TAB 2: Sprint Dashboard (new functionality)
    with tab2:
        render_sprint_dashboard()

    # TAB 3: Person Search (new functionality)
    with tab3:
        render_person_search()


def render_work_item_analyzer():
    """Render the Work Item Analyzer tab (original functionality)"""

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

        # Collect all related items for filtered dashboard view
        st.session_state.filtered_work_items = collect_all_related_items(hierarchy, st.session_state.ado_client)
        st.session_state.filter_mode = 'work_item'

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

        # Notify user about filtered dashboard
        st.info("💡 **Tip:** Switch to the '📊 Sprint Dashboard' tab to see metrics and graphs for this work item and its associated items!")

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


def render_filtered_dashboard():
    """Render dashboard filtered to analyzed work item and its related items"""

    filtered_items = st.session_state.filtered_work_items
    hierarchy = st.session_state.current_hierarchy
    main_item = hierarchy['main']

    # Display what we're viewing
    main_id = main_item.get('id')
    main_type = main_item['fields']['System.WorkItemType']
    main_title = main_item['fields']['System.Title']

    st.success(f"📌 **Filtered View:** {main_type} #{main_id} - {main_title}")

    # Add toggle button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 View Full Sprint"):
            st.session_state.filter_mode = 'sprint'
            st.rerun()

    st.markdown("---")

    # Show scope summary
    st.markdown("### 🌳 Work Item Scope")

    col1, col2, col3, col4 = st.columns(4)

    parent_count = len(hierarchy.get('parents', []))
    child_count = len(hierarchy.get('children', []))
    related_count = len(hierarchy.get('related', []))

    # Count grandchildren
    grandchild_count = 0
    for child in hierarchy.get('children', []):
        child_id = child['data'].get('id')
        try:
            child_hier = st.session_state.ado_client.get_work_item_hierarchy(child_id)
            grandchild_count += len(child_hier.get('children', []))
        except:
            pass

    with col1:
        st.metric("Parents", parent_count)

    with col2:
        st.metric("Main Item", 1, help=f"{main_type} #{main_id}")

    with col3:
        total_children = child_count + grandchild_count
        st.metric("Children & Descendants", total_children)

    with col4:
        st.metric("Related Items", related_count)

    st.markdown("---")

    # Calculate metrics using ONLY filtered items
    analytics = SprintAnalytics(filtered_items, iteration_data=None)
    metrics = analytics.calculate_metrics()

    # Display key metrics
    st.markdown("### 📈 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if main_type in ['Epic', 'Feature', 'User Story']:
            st.metric(
                label="📊 Story Points",
                value=f"{metrics['completed_points']:.0f} / {metrics['total_points']:.0f}",
                delta=f"{metrics['completion_rate']:.1f}% complete"
            )
        else:
            st.metric(
                label="📊 Total Items",
                value=metrics['total_items']
            )

    with col2:
        st.metric(
            label="✅ Completed",
            value=f"{metrics['closed_items']} / {metrics['total_items']}",
            delta=f"{metrics['item_completion_rate']:.1f}%"
        )

    with col3:
        scope_desc = {
            'Epic': 'User Stories',
            'Feature': 'User Stories',
            'User Story': 'Tasks',
            'Task': 'Subtasks'
        }.get(main_type, 'Items')

        st.metric(
            label=f"📋 {scope_desc}",
            value=child_count + grandchild_count
        )

    with col4:
        health_status = metrics['health_status']
        health_emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴', 'unknown': '⚪'}
        health_text = {'green': 'On Track', 'yellow': 'At Risk', 'red': 'Behind', 'unknown': 'N/A'}

        st.metric(
            label="🎯 Status",
            value=health_text.get(health_status, 'Unknown'),
            delta=health_emoji.get(health_status, '⚪')
        )

    st.markdown("---")

    # Visualizations
    st.markdown("### 📊 Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 Work Item Status")
        state_counts = metrics['state_counts']

        if state_counts:
            filtered_states = {k: v for k, v in state_counts.items() if v > 0}
            if filtered_states:
                state_df = pd.DataFrame({
                    'State': list(filtered_states.keys()),
                    'Count': list(filtered_states.values())
                })
                st.bar_chart(state_df.set_index('State'), use_container_width=True)
        else:
            st.info("No state data available")

    with col2:
        st.markdown("#### 🎨 Work Item Types")
        type_counts = metrics['type_counts']

        if type_counts:
            type_df = pd.DataFrame({
                'Type': list(type_counts.keys()),
                'Count': list(type_counts.values())
            })
            st.bar_chart(type_df.set_index('Type'), use_container_width=True)
        else:
            st.info("No type data available")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 👥 Team Distribution")
        assignee_counts = metrics['assignee_counts']

        if assignee_counts:
            assignee_df = pd.DataFrame(list(assignee_counts.items()), columns=['Assignee', 'Count'])
            st.bar_chart(assignee_df.set_index('Assignee'), use_container_width=True)
        else:
            st.info("No assignee data available")

    with col2:
        st.markdown("#### 📊 Completion Progress")

        completed = metrics['closed_items']
        remaining = metrics['total_items'] - completed

        if metrics['total_items'] > 0:
            progress_data = {
                'Status': ['Completed', 'Remaining'],
                'Count': [completed, remaining]
            }
            progress_df = pd.DataFrame(progress_data)
            st.bar_chart(progress_df.set_index('Status'), use_container_width=True)

    st.markdown("---")

    # Work Items Table
    st.markdown("### 📋 Work Items in Scope")

    table_data = []
    for wi in filtered_items:
        fields = wi.get('fields', {})

        assigned_to = fields.get('System.AssignedTo', {})
        if isinstance(assigned_to, dict):
            assignee_name = assigned_to.get('displayName', 'Unassigned')
        else:
            assignee_name = 'Unassigned'

        story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0

        table_data.append({
            'ID': wi.get('id'),
            'Type': fields.get('System.WorkItemType', 'Unknown'),
            'Title': fields.get('System.Title', 'Untitled'),
            'State': fields.get('System.State', 'Unknown'),
            'Assigned To': assignee_name,
            'Story Points': story_points
        })

    if table_data:
        df = pd.DataFrame(table_data)

        # Add filters
        col1, col2 = st.columns(2)

        with col1:
            type_filter = st.multiselect(
                "Filter by Type",
                options=df['Type'].unique(),
                default=df['Type'].unique()
            )

        with col2:
            state_filter = st.multiselect(
                "Filter by State",
                options=df['State'].unique(),
                default=df['State'].unique()
            )

        # Apply filters
        filtered_df = df[
            (df['Type'].isin(type_filter)) &
            (df['State'].isin(state_filter))
        ]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

        # Export
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"work_item_{main_id}_scope.csv",
            mime="text/csv"
        )
    else:
        st.info("No work items to display")

    st.markdown("---")

    # AI Analysis for filtered items
    st.markdown("### 🤖 AI Analysis")

    with st.expander("🧠 Generate Analysis for This Scope", expanded=False):
        if st.button("Generate Analysis", type="primary"):
            # Prepare context
            context = f"""
**Main Work Item:** {main_type} #{main_id} - {main_title}

**Scope:**
- Total Items: {len(filtered_items)}
- Parents: {parent_count}
- Children: {child_count + grandchild_count}
- Related: {related_count}

**Progress:**
- Story Points: {metrics['completed_points']:.0f} / {metrics['total_points']:.0f} ({metrics['completion_rate']:.1f}%)
- Items Completed: {metrics['closed_items']} / {metrics['total_items']} ({metrics['item_completion_rate']:.1f}%)
- Status: {health_text.get(health_status, 'Unknown')}

**Team:**
{', '.join([f"{name} ({count} items)" for name, count in list(assignee_counts.items())[:5]])}
"""

            system_prompt = f"""You are an Agile coach analyzing a {main_type} and all its related work items.
Provide insights on:
1. Overall progress and health
2. Completion timeline estimate
3. Potential blockers or risks
4. Recommendations for the team

Be specific and actionable."""

            user_prompt = f"""Analyze this work item scope:

{context}

Provide comprehensive analysis with recommendations."""

            with st.spinner("🤖 Analyzing..."):
                try:
                    from litellm import completion

                    response = completion(
                        model=os.getenv('LITELLM_MODEL', 'gpt-4'),
                        api_base=os.getenv('LITELLM_API_BASE'),
                        api_key=os.getenv('LITELLM_API_KEY'),
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3
                    )

                    st.markdown(response.choices[0].message.content)

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Please check your LiteLLM connection and VPN status.")


def render_sprint_dashboard():
    """Render the Sprint Dashboard tab with analytics and visualizations"""

    st.markdown("## 📊 Sprint Analytics Dashboard")

    # Check if we should show filtered view for a specific work item
    if 'filtered_work_items' in st.session_state and st.session_state.get('filter_mode') == 'work_item':
        render_filtered_dashboard()
        return

    # Otherwise show full sprint dashboard
    st.markdown("Visualize sprint progress, team velocity, and work distribution")
    st.markdown("---")

    # Add option to go back to filtered view if available
    if 'filtered_work_items' in st.session_state:
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("📌 Back to Work Item View"):
                st.session_state.filter_mode = 'work_item'
                st.rerun()

    # Fetch available iterations
    with st.spinner("🔄 Fetching sprints/iterations..."):
        iterations = st.session_state.ado_client.get_all_iterations()

    if not iterations:
        st.warning("⚠️ No iterations found for this project. Please check your Azure DevOps configuration.")
        st.info("**Troubleshooting:**\n- Ensure your project has sprints/iterations configured\n- Check your Azure DevOps PAT has correct permissions\n- Verify the project name in your .env file")
        return

    # Sprint Selection
    st.markdown("### 🎯 Select Sprint/Iteration")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Create dropdown options
        iteration_options = {}
        for iteration in iterations:
            iter_name = iteration.get('name', 'Unknown')
            iter_path = iteration.get('path', '')
            attributes = iteration.get('attributes', {})
            start_date = attributes.get('startDate', '')
            end_date = attributes.get('finishDate', '')

            # Format display name
            if start_date and end_date:
                try:
                    start = start_date[:10]
                    end = end_date[:10]
                    display_name = f"{iter_name} ({start} to {end})"
                except:
                    display_name = iter_name
            else:
                display_name = iter_name

            iteration_options[display_name] = iteration

        selected_iteration_name = st.selectbox(
            "Choose a sprint:",
            options=list(iteration_options.keys()),
            help="Select a sprint/iteration to view analytics"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh_button = st.button("🔄 Refresh Data", help="Clear cache and refresh sprint data")

    if refresh_button:
        st.cache_data.clear()
        st.rerun()

    # Get selected iteration data
    selected_iteration = iteration_options[selected_iteration_name]
    iteration_path = selected_iteration.get('path', '')

    st.markdown("---")

    # Fetch work items for selected sprint
    with st.spinner(f"📥 Fetching work items for {selected_iteration.get('name')}..."):
        sprint_work_items = st.session_state.ado_client.get_sprint_work_items(iteration_path)

    if not sprint_work_items:
        st.info(f"📭 No work items found in sprint: **{selected_iteration.get('name')}**")
        st.markdown("This sprint might be empty or work items might not be assigned to this iteration yet.")
        return

    # Initialize Analytics
    analytics = SprintAnalytics(sprint_work_items, selected_iteration)
    metrics = analytics.calculate_metrics()

    # Display Key Metrics Cards
    st.markdown("### 📈 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Story Points",
            value=f"{metrics['completed_points']:.0f} / {metrics['total_points']:.0f}",
            delta=f"{metrics['completion_rate']:.1f}% complete",
            delta_color="normal"
        )

    with col2:
        st.metric(
            label="✅ Work Items",
            value=f"{metrics['closed_items']} / {metrics['total_items']}",
            delta=f"{metrics['item_completion_rate']:.1f}% closed",
            delta_color="normal"
        )

    with col3:
        sprint_progress = metrics['sprint_progress']
        st.metric(
            label="📅 Sprint Progress",
            value=f"{sprint_progress.get('days_elapsed', 0)} / {sprint_progress.get('days_total', 0)} days",
            delta=f"{sprint_progress.get('progress_pct', 0):.1f}% elapsed",
            delta_color="normal"
        )

    with col4:
        # Health indicator
        health_status = metrics['health_status']
        health_emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴', 'unknown': '⚪'}
        health_text = {'green': 'On Track', 'yellow': 'At Risk', 'red': 'Behind', 'unknown': 'Unknown'}

        st.metric(
            label="🎯 Sprint Health",
            value=health_text.get(health_status, 'Unknown'),
            delta=health_emoji.get(health_status, '⚪')
        )

    st.markdown("---")

    # Visualizations Row
    st.markdown("### 📊 Sprint Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        # Burndown Chart
        st.markdown("#### 🔥 Burndown Chart")
        ideal_burndown, actual_burndown = analytics.generate_burndown_data()

        if ideal_burndown and actual_burndown:
            # Create DataFrame for chart
            days = list(range(len(ideal_burndown)))
            burndown_df = pd.DataFrame({
                'Day': days,
                'Ideal': ideal_burndown,
                'Actual': actual_burndown[:len(days)]
            })
            burndown_df = burndown_df.set_index('Day')

            st.line_chart(burndown_df, use_container_width=True)
        else:
            st.info("Not enough data to display burndown chart")

    with col2:
        # Work Item Status Distribution
        st.markdown("#### 📋 Work Item Status")
        state_counts = metrics['state_counts']

        if state_counts:
            # Filter out zero counts
            filtered_states = {k: v for k, v in state_counts.items() if v > 0}

            if filtered_states:
                state_df = pd.DataFrame({
                    'State': list(filtered_states.keys()),
                    'Count': list(filtered_states.values())
                })
                st.bar_chart(state_df.set_index('State'), use_container_width=True)
            else:
                st.info("No work items to display")
        else:
            st.info("No state data available")

    st.markdown("---")

    # Work Item Type Breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🎨 Work Item Types")
        type_counts = metrics['type_counts']

        if type_counts:
            type_df = pd.DataFrame({
                'Type': list(type_counts.keys()),
                'Count': list(type_counts.values())
            })
            st.bar_chart(type_df.set_index('Type'), use_container_width=True)
        else:
            st.info("No type data available")

    with col2:
        st.markdown("#### 👥 Work Distribution by Assignee")
        assignee_counts = metrics['assignee_counts']

        if assignee_counts:
            # Show top 10 assignees
            sorted_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            assignee_df = pd.DataFrame(sorted_assignees, columns=['Assignee', 'Count'])
            st.bar_chart(assignee_df.set_index('Assignee'), use_container_width=True)
        else:
            st.info("No assignee data available")

    st.markdown("---")

    # AI Sprint Analysis
    st.markdown("### 🤖 AI Sprint Analysis")

    with st.expander("🧠 Generate AI Insights", expanded=False):
        if st.button("Generate Sprint Analysis", type="primary"):
            context = analytics.generate_ai_summary_context()

            system_prompt = """You are a Scrum Master and Agile coach analyzing a sprint.
Provide insights on:
1. Sprint health and progress
2. Potential risks and blockers
3. Recommendations to complete the sprint successfully
4. Team performance observations

Be concise, actionable, and supportive."""

            user_prompt = f"""Analyze this sprint and provide insights:

{context}

Provide a comprehensive sprint analysis with actionable recommendations."""

            with st.spinner("🤖 AI is analyzing the sprint..."):
                try:
                    from litellm import completion

                    response = completion(
                        model=os.getenv('LITELLM_MODEL', 'gpt-4'),
                        api_base=os.getenv('LITELLM_API_BASE'),
                        api_key=os.getenv('LITELLM_API_KEY'),
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3
                    )

                    ai_analysis = response.choices[0].message.content
                    st.markdown(ai_analysis)

                except Exception as e:
                    st.error(f"Error generating AI analysis: {str(e)}")
                    st.info("Please check your LiteLLM connection and VPN status.")

    st.markdown("---")

    # ADVANCED FEATURES SECTION
    st.markdown("## 🚀 Advanced Analytics")

    # Create tabs for advanced features
    adv_tab1, adv_tab2, adv_tab3, adv_tab4 = st.tabs([
        "📈 Velocity Trends",
        "📊 Burnup Chart",
        "🔮 Forecast",
        "📑 Compare Sprints"
    ])

    # TAB 1: Velocity Trends
    with adv_tab1:
        st.markdown("#### 📈 Team Velocity Over Time")

        # Get last 5 sprints for velocity tracking
        with st.spinner("Fetching historical sprint data..."):
            # Get up to 5 recent iterations
            recent_iterations = iterations[-5:] if len(iterations) >= 5 else iterations

            sprints_data = []
            for iteration in recent_iterations:
                iter_path = iteration.get('path', '')
                iter_work_items = st.session_state.ado_client.get_sprint_work_items(iter_path)
                sprints_data.append({
                    'sprint_info': iteration,
                    'work_items': iter_work_items
                })

            if len(sprints_data) > 1:
                multi_analytics = MultiSprintAnalytics(sprints_data)
                velocity_data = multi_analytics.calculate_velocity_trends()

                # Display velocity trend
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Velocity line chart
                    velocity_df = pd.DataFrame({
                        'Sprint': velocity_data['sprint_names'],
                        'Velocity (Story Points)': velocity_data['velocities']
                    })
                    st.line_chart(velocity_df.set_index('Sprint'), use_container_width=True)

                with col2:
                    # Velocity metrics
                    st.metric(
                        label="Average Velocity",
                        value=f"{velocity_data['average_velocity']:.1f}",
                        delta=velocity_data['trend'].capitalize()
                    )

                    trend_emoji = {
                        'increasing': '📈',
                        'decreasing': '📉',
                        'stable': '➡️'
                    }
                    st.markdown(f"### {trend_emoji.get(velocity_data['trend'], '➡️')}")
                    st.caption(f"Trend: **{velocity_data['trend'].capitalize()}**")

                # Velocity insights
                st.markdown("#### 💡 Insights")
                if velocity_data['trend'] == 'increasing':
                    st.success("✅ **Great!** Team velocity is increasing over time. The team is becoming more efficient.")
                elif velocity_data['trend'] == 'decreasing':
                    st.warning("⚠️ **Attention:** Team velocity is decreasing. Consider investigating potential blockers or capacity issues.")
                else:
                    st.info("➡️ Team velocity is stable. Consistent performance across sprints.")

            else:
                st.info("Need at least 2 sprints to show velocity trends. Complete more sprints to see this analysis.")

    # TAB 2: Burnup Chart
    with adv_tab2:
        st.markdown("#### 📊 Sprint Burnup Chart")
        st.caption("Shows work completed over time vs total scope")

        total_scope, completed_work = analytics.generate_burnup_data()

        if total_scope and completed_work:
            days = list(range(len(total_scope)))
            burnup_df = pd.DataFrame({
                'Day': days,
                'Total Scope': total_scope,
                'Completed Work': completed_work[:len(days)]
            })
            burnup_df = burnup_df.set_index('Day')

            st.line_chart(burnup_df, use_container_width=True)

            # Burnup insights
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Scope", f"{total_scope[0]:.0f} pts")
            with col2:
                current_completed = completed_work[min(len(completed_work)-1, metrics['sprint_progress']['days_elapsed'])]
                st.metric("Completed", f"{current_completed:.0f} pts")
            with col3:
                remaining = total_scope[0] - current_completed
                st.metric("Remaining", f"{remaining:.0f} pts")

        else:
            st.info("Not enough data to display burnup chart")

    # TAB 3: Forecast Completion
    with adv_tab3:
        st.markdown("#### 🔮 Sprint Completion Forecast")
        st.caption("Predict if sprint will complete based on current velocity")

        if len(sprints_data) > 1:
            multi_analytics = MultiSprintAnalytics(sprints_data)

            # Calculate current velocity
            sprint_progress = metrics['sprint_progress']
            days_elapsed = sprint_progress.get('days_elapsed', 1)
            current_velocity = metrics['completed_points'] / days_elapsed if days_elapsed > 0 else 0
            remaining_points = metrics['remaining_points']

            prediction = multi_analytics.predict_completion(remaining_points, current_velocity)

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    label="Current Velocity",
                    value=f"{current_velocity:.1f} pts/day"
                )
                st.metric(
                    label="Days Needed",
                    value=f"{prediction['days_needed']:.1f} days"
                )

            with col2:
                st.metric(
                    label="Confidence",
                    value=prediction['confidence'].capitalize()
                )

                if prediction['can_complete']:
                    st.success("✅ **On track** to complete sprint!")
                else:
                    st.warning("⚠️ **At risk** - May not complete all work")

            st.markdown("#### 📊 Forecast Details")
            st.info(prediction['message'])

            # Recommendations
            st.markdown("#### 💡 Recommendations")
            if not prediction['can_complete']:
                st.markdown("""
                - Consider reducing scope or deferring lower-priority items
                - Identify and remove blockers affecting velocity
                - Ensure team has adequate capacity
                - Review work item complexity and re-estimate if needed
                """)
            else:
                st.markdown("""
                - Continue current pace
                - Monitor for new blockers
                - Consider taking on additional work if time permits
                """)
        else:
            st.info("Need historical sprint data to generate forecast. Complete more sprints to see predictions.")

    # TAB 4: Compare Sprints
    with adv_tab4:
        st.markdown("#### 📑 Sprint Comparison")
        st.caption("Compare metrics across multiple sprints")

        if len(sprints_data) > 1:
            multi_analytics = MultiSprintAnalytics(sprints_data)
            comparison = multi_analytics.compare_sprints()

            # Create comparison DataFrame
            comparison_df = pd.DataFrame({
                'Sprint': comparison['sprint_names'],
                'Total Points': comparison['total_points'],
                'Completed Points': comparison['completed_points'],
                'Completion %': comparison['completion_rates'],
                'Total Items': comparison['total_items'],
                'Closed Items': comparison['closed_items']
            })

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Completion %": st.column_config.NumberColumn("Completion %", format="%.1f%%")
                }
            )

            # Comparison charts
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Story Points Comparison**")
                points_df = pd.DataFrame({
                    'Sprint': comparison['sprint_names'],
                    'Completed': comparison['completed_points']
                })
                st.bar_chart(points_df.set_index('Sprint'), use_container_width=True)

            with col2:
                st.markdown("**Completion Rate Comparison**")
                completion_df = pd.DataFrame({
                    'Sprint': comparison['sprint_names'],
                    'Completion %': comparison['completion_rates']
                })
                st.bar_chart(completion_df.set_index('Sprint'), use_container_width=True)

            # Export comparison
            csv = comparison_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Comparison as CSV",
                data=csv,
                file_name="sprint_comparison.csv",
                mime="text/csv"
            )
        else:
            st.info("Need at least 2 sprints to compare. Complete more sprints to see comparison.")

    st.markdown("---")

    # Work Items Table
    st.markdown("### 📋 Sprint Work Items")

    # Get table data
    table_data = analytics.get_work_items_table_data()

    if table_data:
        df = pd.DataFrame(table_data)

        # Add filters
        col1, col2, col3 = st.columns(3)

        with col1:
            type_filter = st.multiselect(
                "Filter by Type",
                options=df['Type'].unique(),
                default=df['Type'].unique()
            )

        with col2:
            state_filter = st.multiselect(
                "Filter by State",
                options=df['State'].unique(),
                default=df['State'].unique()
            )

        with col3:
            assignee_filter = st.multiselect(
                "Filter by Assignee",
                options=df['Assigned To'].unique(),
                default=df['Assigned To'].unique()
            )

        # Apply filters
        filtered_df = df[
            (df['Type'].isin(type_filter)) &
            (df['State'].isin(state_filter)) &
            (df['Assigned To'].isin(assignee_filter))
        ]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d"),
                "Story Points": st.column_config.NumberColumn("Story Points", format="%.0f")
            }
        )

        # Export button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"sprint_{selected_iteration.get('name', 'export')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No work items to display")


def render_person_search():
    """Render the Person Search tab - search work items by assignee name"""

    st.markdown("## 👤 Person Search")
    st.markdown("Search for work items assigned to a specific person and view their ADO links and metrics.")

    # Search input
    col1, col2 = st.columns([3, 1])
    with col1:
        person_name = st.text_input(
            "🔍 Enter person's name",
            placeholder="e.g., Aditya, John Smith, or john.smith@company.com",
            help="Enter full or partial name. The search will find all matching assignees."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_button = st.button("🔎 Search", type="primary")

    # Perform search
    if search_button and person_name:
        if not person_name.strip():
            st.warning("⚠️ Please enter a person's name to search.")
            return

        with st.spinner(f"🔄 Searching work items and dashboards for '{person_name}'..."):
            try:
                # Search work items by assignee
                work_items = st.session_state.ado_client.get_work_items_by_assignee(person_name)

                # Search dashboards by owner
                dashboards = st.session_state.ado_client.get_dashboards_by_owner(person_name)

                if not work_items and not dashboards:
                    st.warning(f"❌ No work items or dashboards found for '{person_name}'. Please check the name and try again.")
                    return

                # Store in session state for dashboard view
                st.session_state.person_work_items = work_items
                st.session_state.person_dashboards = dashboards
                st.session_state.person_search_name = person_name

                # Display results
                results_text = []
                if work_items:
                    results_text.append(f"**{len(work_items)}** work items")
                if dashboards:
                    results_text.append(f"**{len(dashboards)}** dashboards")
                st.success(f"✅ Found {' and '.join(results_text)} for '{person_name}'")

                # Extract unique assignee name from results (to get full name)
                assignee_names = set()
                for item in work_items:
                    assignee = item.get('fields', {}).get('System.AssignedTo', {})
                    if isinstance(assignee, dict):
                        full_name = assignee.get('displayName', '')
                        if full_name:
                            assignee_names.add(full_name)

                if assignee_names:
                    st.info(f"📌 **Matched assignees:** {', '.join(assignee_names)}")

                # Calculate metrics
                if work_items:
                    render_person_metrics(work_items, person_name)

                # Display dashboards owned by person
                if dashboards:
                    render_person_dashboards(dashboards, person_name)

                # Display work items with ADO links
                if work_items:
                    render_person_work_items(work_items)

                # Option to view filtered dashboard
                if work_items:
                    st.markdown("---")
                    st.markdown("### 📊 View Dashboard")
                if st.button("🎯 View Filtered Dashboard for This Person", type="secondary"):
                    # Set filter mode to person
                    st.session_state.filter_mode = 'person'
                    st.session_state.filtered_work_items = work_items
                    # Switch to sprint dashboard tab would require rerun with tab selection
                    st.info("💡 **Tip:** Switch to the '📊 Sprint Dashboard' tab to see detailed metrics and charts for this person's work items!")

            except Exception as e:
                st.error(f"❌ Error searching for work items: {str(e)}")
                return

    # If there's existing search results, show them
    elif 'person_work_items' in st.session_state or 'person_dashboards' in st.session_state:
        work_items = st.session_state.get('person_work_items', [])
        dashboards = st.session_state.get('person_dashboards', [])
        person_name = st.session_state.get('person_search_name', 'Unknown')

        # Display results summary
        results_text = []
        if work_items:
            results_text.append(f"**{len(work_items)}** work items")
        if dashboards:
            results_text.append(f"**{len(dashboards)}** dashboards")
        if results_text:
            st.info(f"📌 Showing {' and '.join(results_text)} for '{person_name}'")

        # Calculate metrics
        if work_items:
            render_person_metrics(work_items, person_name)

        # Display dashboards owned by person
        if dashboards:
            render_person_dashboards(dashboards, person_name)

        # Display work items with ADO links
        if work_items:
            render_person_work_items(work_items)

        # Option to view filtered dashboard
        if work_items:
            st.markdown("---")
            st.markdown("### 📊 View Dashboard")
            if st.button("🎯 View Filtered Dashboard for This Person", type="secondary"):
                st.session_state.filter_mode = 'person'
                st.session_state.filtered_work_items = work_items
                st.info("💡 **Tip:** Switch to the '📊 Sprint Dashboard' tab to see detailed metrics and charts for this person's work items!")


def render_person_metrics(work_items: List[Dict], person_name: str):
    """Display metrics for person's work items"""

    st.markdown("---")
    st.markdown("### 📈 Metrics Overview")

    # Calculate metrics
    total_items = len(work_items)

    # Count by state
    state_counts = {}
    type_counts = {}
    total_story_points = 0
    completed_story_points = 0

    for item in work_items:
        fields = item.get('fields', {})

        # State
        state = fields.get('System.State', 'Unknown')
        state_counts[state] = state_counts.get(state, 0) + 1

        # Type
        work_item_type = fields.get('System.WorkItemType', 'Unknown')
        type_counts[work_item_type] = type_counts.get(work_item_type, 0) + 1

        # Story points
        story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0
        total_story_points += story_points

        # Completed story points (Closed or Resolved states)
        if state in ['Closed', 'Resolved', 'Done']:
            completed_story_points += story_points

    # Calculate completion rate
    active_items = state_counts.get('Active', 0)
    closed_items = state_counts.get('Closed', 0) + state_counts.get('Resolved', 0) + state_counts.get('Done', 0)
    completion_rate = (closed_items / total_items * 100) if total_items > 0 else 0

    # Display metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📋 Total Items", total_items)

    with col2:
        st.metric("⚡ Active", active_items)

    with col3:
        st.metric("✅ Completed", closed_items)

    with col4:
        st.metric("📊 Story Points", f"{int(total_story_points)}")

    with col5:
        st.metric("🎯 Completion Rate", f"{completion_rate:.1f}%")

    # Display breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🔹 By State")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_items * 100) if total_items > 0 else 0
            st.markdown(f"- **{state}**: {count} ({percentage:.1f}%)")

    with col2:
        st.markdown("#### 🔸 By Type")
        for wi_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_items * 100) if total_items > 0 else 0
            st.markdown(f"- **{wi_type}**: {count} ({percentage:.1f}%)")


def render_person_work_items(work_items: List[Dict]):
    """Display person's work items with ADO links"""

    st.markdown("---")
    st.markdown("### 🔗 Work Items with ADO Links")

    # Filters
    col1, col2, col3 = st.columns(3)

    # Get unique values for filters
    all_states = set()
    all_types = set()
    all_iterations = set()

    for item in work_items:
        fields = item.get('fields', {})
        all_states.add(fields.get('System.State', 'Unknown'))
        all_types.add(fields.get('System.WorkItemType', 'Unknown'))
        iteration = fields.get('System.IterationPath', 'Unknown')
        if iteration:
            all_iterations.add(iteration)

    with col1:
        state_filter = st.multiselect(
            "Filter by State",
            options=sorted(all_states),
            default=[]
        )

    with col2:
        type_filter = st.multiselect(
            "Filter by Type",
            options=sorted(all_types),
            default=[]
        )

    with col3:
        iteration_filter = st.multiselect(
            "Filter by Iteration",
            options=sorted(all_iterations),
            default=[]
        )

    # Apply filters
    filtered_items = work_items
    if state_filter:
        filtered_items = [item for item in filtered_items if item.get('fields', {}).get('System.State') in state_filter]
    if type_filter:
        filtered_items = [item for item in filtered_items if item.get('fields', {}).get('System.WorkItemType') in type_filter]
    if iteration_filter:
        filtered_items = [item for item in filtered_items if item.get('fields', {}).get('System.IterationPath') in iteration_filter]

    st.markdown(f"Showing **{len(filtered_items)}** of **{len(work_items)}** work items")

    # Display work items
    for item in filtered_items:
        fields = item.get('fields', {})
        item_id = item.get('id')
        title = fields.get('System.Title', 'No Title')
        state = fields.get('System.State', 'Unknown')
        work_item_type = fields.get('System.WorkItemType', 'Unknown')
        story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0
        iteration = fields.get('System.IterationPath', 'N/A')
        area = fields.get('System.AreaPath', 'N/A')

        # Generate ADO link
        organization = st.session_state.ado_client.organization
        project = st.session_state.ado_client.project
        encoded_project = quote(project, safe='')
        ado_link = f"https://dev.azure.com/{organization}/{encoded_project}/_workitems/edit/{item_id}"

        # Display work item card
        with st.container():
            # Type and state badges
            type_badge_class = {
                'Epic': 'wi-epic',
                'Feature': 'wi-feature',
                'User Story': 'wi-story',
                'Task': 'wi-task',
                'Bug': 'wi-bug'
            }.get(work_item_type, 'wi-task')

            state_badge_class = {
                'New': 'state-new',
                'Active': 'state-active',
                'Resolved': 'state-resolved',
                'Closed': 'state-closed',
                'Done': 'state-resolved'
            }.get(state, 'state-new')

            st.markdown(f"""
            <div class="work-item-card">
                <div>
                    <span class="wi-badge {type_badge_class}">{work_item_type}</span>
                    <span class="state-badge {state_badge_class}">{state}</span>
                </div>
                <div class="wi-title">#{item_id}: {title}</div>
                <div style="margin-top: 8px; color: #605e5c;">
                    <strong>📊 Story Points:</strong> {int(story_points) if story_points else 'N/A'} |
                    <strong>🔄 Iteration:</strong> {iteration.split('\\')[-1] if iteration != 'N/A' else 'N/A'} |
                    <strong>📁 Area:</strong> {area.split('\\')[-1] if area != 'N/A' else 'N/A'}
                </div>
                <div style="margin-top: 8px;">
                    <a href="{ado_link}" target="_blank" style="color: #0078d4; text-decoration: none; font-weight: 600;">
                        🔗 Open in Azure DevOps →
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if not filtered_items:
        st.info("No work items match the selected filters.")


def render_person_dashboards(dashboards: List[Dict], person_name: str):
    """Display dashboards owned by a person with ADO links"""

    st.markdown("---")
    st.markdown("### 📊 Dashboards Owned")
    st.markdown(f"**{len(dashboards)}** dashboard(s) owned by {person_name}")

    # Display each dashboard
    for dashboard in dashboards:
        dashboard_id = dashboard.get('id')
        dashboard_name = dashboard.get('name', 'Unnamed Dashboard')
        description = dashboard.get('description', 'No description')
        team_name = dashboard.get('teamName', 'Unknown Team')
        team_id = dashboard.get('teamId', '')

        # Owner information
        owner = dashboard.get('owner', {})
        owner_name = owner.get('displayName', 'Unknown') if isinstance(owner, dict) else str(owner)

        # Last modified
        last_modified = dashboard.get('lastAccessedDate', 'N/A')

        # Generate ADO dashboard link
        organization = st.session_state.ado_client.organization
        project = st.session_state.ado_client.project
        encoded_project = quote(project, safe='')
        encoded_team = quote(team_name, safe='')
        dashboard_link = f"https://dev.azure.com/{organization}/{encoded_project}/{encoded_team}/_dashboards/dashboard/{dashboard_id}"

        # Display dashboard card
        with st.container():
            st.markdown(f"""
            <div class="work-item-card">
                <div>
                    <span class="wi-badge wi-feature">📊 Dashboard</span>
                </div>
                <div class="wi-title">{dashboard_name}</div>
                <div style="margin-top: 8px; color: #605e5c;">
                    <strong>📝 Description:</strong> {description if description else 'No description'}
                </div>
                <div style="margin-top: 8px; color: #605e5c;">
                    <strong>👥 Team:</strong> {team_name} |
                    <strong>👤 Owner:</strong> {owner_name}
                </div>
                <div style="margin-top: 8px;">
                    <a href="{dashboard_link}" target="_blank" style="color: #0078d4; text-decoration: none; font-weight: 600;">
                        🔗 Open Dashboard in Azure DevOps →
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")  # Add spacing

    if not dashboards:
        st.info("No dashboards found.")


if __name__ == "__main__":
    main()
