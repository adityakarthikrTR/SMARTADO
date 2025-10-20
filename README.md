# SmartADO - AI-Powered Azure DevOps Work Item Analyzer

A Streamlit web application that analyzes Azure DevOps work items and provides AI-generated summaries and technical solutions using LiteLLM (Thomson Reuters internal endpoint).

## Features

### 🔍 Work Item Analysis
- **Parse Any ADO URL**: Paste any Azure DevOps work item URL (Epic, User Story, Task, Bug, Feature)
- **Fetch Full Details**: Automatically retrieves work item data via Azure DevOps REST API
- **Hierarchy Visualization**: Shows parent, child, and related work items in a clean interface
- **ADO-Style UI**: Familiar Azure DevOps look and feel with color-coded badges

### 🤖 AI-Powered Insights
- **Smart Summaries**: LiteLLM generates comprehensive summaries of work items and their relationships
- **Technical Solutions**: AI-powered implementation guidance for User Stories and Tasks
- **Multiple Solutions**: Generates separate solutions for each user story in the hierarchy
- **Context-Aware**: AI analyzes descriptions, acceptance criteria, and relationships

### 📊 Display Features
- Work item type badges (Epic, Feature, User Story, Task, Bug)
- State indicators (New, Active, Resolved, Closed)
- Expandable descriptions and acceptance criteria
- Raw JSON data view for debugging
- Separate tabs for each user story solution

## Prerequisites

- Python 3.8 or higher
- Azure DevOps account with access to TR-Legal-Cobalt organization
- Azure DevOps Personal Access Token (PAT)
- Access to Thomson Reuters VPN (for LiteLLM)

## Installation

### 1. Clone or Download the Project

```bash
cd SmartADO
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file by copying the example:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and add your Azure DevOps Personal Access Token:

```env
# Azure DevOps Configuration
ADO_ORGANIZATION=TR-Legal-Cobalt
ADO_PROJECT=Legal Cobalt Backlog
ADO_PAT=YOUR_PERSONAL_ACCESS_TOKEN_HERE

# LiteLLM Configuration (already configured for TR)
LITELLM_API_BASE=https://litellm.int.thomsonreuters.com
LITELLM_API_KEY=sk-zlR9TXis42IY0AuSRvU9Cw
LITELLM_MODEL=gpt-4
```

### 5. Get Your Azure DevOps PAT

1. Go to: https://dev.azure.com/TR-Legal-Cobalt/_usersSettings/tokens
2. Click **"New Token"**
3. Name: `SmartADO`
4. Scopes: Select **"Work Items"** → **"Read"**
5. Click **"Create"**
6. Copy the token and paste it in your `.env` file

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### Using SmartADO

1. **Paste ADO URL**: Copy any Azure DevOps work item URL and paste it in the input field
   - Example: `https://dev.azure.com/TR-Legal-Cobalt/Legal%20Cobalt%20Backlog/_workitems/edit/12345`

2. **Click "Analyze Work Item"**: The app will fetch the work item and its hierarchy

3. **View Details**:
   - Work item details with type, state, and assignment
   - Parent/Child/Related work items
   - Descriptions and acceptance criteria

4. **Read AI Summary**: Get a comprehensive summary of the work item and its context

5. **Get Technical Solutions**: View AI-generated implementation guidance for user stories

### Supported URL Formats

SmartADO supports various Azure DevOps URL formats:

```
# Direct work item edit
https://dev.azure.com/{org}/{project}/_workitems/edit/{id}

# Board view with work item
https://dev.azure.com/{org}/{project}/_boards/board/...?workitem={id}

# Query view with work item selected
https://dev.azure.com/{org}/{project}/_queries/query/{queryid}/?witd={id}

# Backlog view
https://dev.azure.com/{org}/{project}/_backlogs/backlog/.../Stories/?workitem={id}
```

## Project Structure

```
SmartADO/
├── app.py                  # Main Streamlit web application
├── ado_parser.py          # Azure DevOps URL parser
├── ado_client.py          # Azure DevOps API client
├── ai_analyzer.py         # LiteLLM integration for AI analysis
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Architecture

### Data Flow

1. **User Input** → User pastes Azure DevOps URL
2. **URL Parsing** (`ado_parser.py`) → Extract work item ID and metadata
3. **API Fetch** (`ado_client.py`) → Fetch work item data from Azure DevOps REST API
4. **Hierarchy Build** → Fetch parent, child, and related work items
5. **Display** (`app.py`) → Render work item details in ADO-style UI
6. **AI Analysis** (`ai_analyzer.py`) → Generate summary and solutions using LiteLLM
7. **Results Display** → Show AI insights in separate sections

### Key Components

#### 1. URL Parser (`ado_parser.py`)
- Regex-based URL parsing for various ADO URL formats
- Extracts organization, project, work item ID
- Supports queries, boards, backlogs, and direct links

#### 2. ADO Client (`ado_client.py`)
- Azure DevOps REST API v7.0 integration
- Basic authentication using Personal Access Token
- Caches API responses for 5 minutes (300s)
- Fetches work items with full relations

#### 3. AI Analyzer (`ai_analyzer.py`)
- LiteLLM integration for Thomson Reuters endpoint
- Generates context-aware summaries
- Provides technical solutions based on work item type
- Customized prompts for Epic/User Story/Task/Bug

#### 4. Streamlit App (`app.py`)
- ADO-style UI with color-coded badges
- Responsive layout with sidebar configuration
- Separate sections for summary and solutions
- Collapsible details and raw JSON view

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADO_ORGANIZATION` | Azure DevOps organization name | TR-Legal-Cobalt |
| `ADO_PROJECT` | Project name | Legal Cobalt Backlog |
| `ADO_PAT` | Personal Access Token | (required) |
| `LITELLM_API_BASE` | LiteLLM endpoint URL | https://litellm.int.thomsonreuters.com |
| `LITELLM_API_KEY` | LiteLLM API key | sk-zlR9TXis42IY0AuSRvU9Cw |
| `LITELLM_MODEL` | AI model to use | gpt-4 |

### Caching

- Azure DevOps API responses are cached for **5 minutes** using `@st.cache_data(ttl=300)`
- This reduces API calls and improves performance during analysis

## Troubleshooting

### Common Issues

#### 1. "Configuration Error"
- Ensure `.env` file exists and is properly configured
- Check that all required environment variables are set

#### 2. "Work item not found or access denied"
- Verify the work item ID is correct
- Ensure your Azure DevOps PAT has "Work Items (Read)" permissions
- Check that you have access to the TR-Legal-Cobalt organization

#### 3. "Error generating summary/solution"
- Ensure you're connected to Thomson Reuters VPN
- Verify LiteLLM endpoint is accessible
- Check that LITELLM_API_KEY is correct

#### 4. "Invalid Azure DevOps URL"
- Ensure the URL includes a work item ID
- Try using the direct work item edit URL format
- Check that the URL is from dev.azure.com

### Testing Individual Modules

```bash
# Test URL parser
python ado_parser.py

# Test ADO client (requires .env configuration)
python ado_client.py

# Test AI analyzer (requires .env and VPN)
python ai_analyzer.py
```

## Thomson Reuters Specifics

### LiteLLM Access
- **VPN Required**: Must be connected to Thomson Reuters VPN
- **Endpoint**: Internal LiteLLM proxy at `https://litellm.int.thomsonreuters.com`
- **Pre-configured**: API key is already set in `.env.example`
- **Available Models**: gpt-4, gpt-3.5-turbo (gpt-4 recommended)

### Azure DevOps Access
- **Organization**: TR-Legal-Cobalt
- **Project**: Legal Cobalt Backlog
- **PAT Scope**: Work Items (Read) - minimum required permission

## Security Notes

- **Never commit `.env` file** - Contains sensitive credentials
- **PAT Permissions**: Use least privilege (Read-only for work items)
- **Token Rotation**: Regularly rotate your Azure DevOps PAT
- **VPN Requirement**: LiteLLM is only accessible from TR network

## Features Roadmap

- [ ] Support for multiple projects/organizations
- [ ] Export analysis reports to PDF/Word
- [ ] Batch analysis of multiple work items
- [ ] Query-based analysis (analyze all items in a query)
- [ ] Sprint/iteration analysis
- [ ] Work item creation suggestions
- [ ] Integration with Microsoft Teams for notifications

## Contributing

This is an internal Thomson Reuters tool. For issues or feature requests, contact the development team.

## Support

For help or questions:
- Azure DevOps Documentation: https://docs.microsoft.com/en-us/azure/devops/
- Streamlit Documentation: https://docs.streamlit.io/
- LiteLLM Documentation: https://docs.litellm.ai/

## License

Internal Thomson Reuters tool - Not for external distribution.

---

**Built with:**
- 🐍 Python
- 🎨 Streamlit
- 🤖 LiteLLM (Thomson Reuters)
- 📦 Azure DevOps REST API
