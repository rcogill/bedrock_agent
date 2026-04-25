# Bedrock Agent CLI

A minimal command-line application for running agentic workflows using AWS Bedrock models with LangChain.

## Installation

### From source

```bash
# Clone the repository
git clone <repository-url>
cd bedrock-agent-cli

# Install with pip
pip install -e .
```

## AWS Credentials Setup

The application uses AWS credentials to access Bedrock. Configure your credentials using one of these methods:

### Option 1: AWS Credentials File (Recommended)

Create or edit `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

And `~/.aws/config`:

```ini
[default]
region = us-east-1
```

### Option 2: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
export AWS_DEFAULT_REGION=us-east-1
```

### Option 3: Configuration File

Add credentials directly in your agent configuration file (not recommended for production):

```yaml
aws:
  access_key_id: YOUR_ACCESS_KEY
  secret_access_key: YOUR_SECRET_KEY
  region: us-east-1
```

## Usage

### Basic Usage

Run with the default coding agent:

```bash
bedrock-agent
```

### With Custom Configuration

```bash
# Run the coding agent
bedrock-agent --config config/coding_agent.yaml

# Run the research agent
bedrock-agent --config config/research_agent.yaml
```

### Interactive Commands

Once the application is running, you can:

- Type any message to interact with the agent
- `/save <filename>` - Save conversation history to a JSON file
- `/load <filename>` - Load a previously saved conversation
- `/clear` - Clear the current conversation history
- `/help` - Show available commands
- `/exit` or `/quit` - Exit the application

## Available Agents

### Coding Agent (`config/coding_agent.yaml`)

A coding assistant with filesystem access for exploring and modifying code.

**Tools:**
- `list_directory` - List contents of a directory
- `read_file` - Read contents of a file
- `write_file` - Write content to a file
- `create_directory` - Create a new directory

### Research Agent (`config/research_agent.yaml`)

A research assistant that can search the web and analyze documents.

**Tools:**
- `web_search` - Search the web using DuckDuckGo
- `fetch_webpage` - Fetch and extract text from web pages
- `fetch_pdf` - Download and extract text from PDF documents

## Configuration File Format

```yaml
# Agent configuration
model:
  model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
  temperature: 0.7
  max_tokens: 4096

# AWS configuration (optional - uses default credentials if not specified)
aws:
  region: us-east-1
  # access_key_id: YOUR_KEY  # Optional
  # secret_access_key: YOUR_SECRET  # Optional

# System prompt for the agent
system_prompt: |
  You are a helpful assistant...

# Tools to enable (pick from available tools)
tools:
  - list_directory
  - read_file
  - write_file
  - create_directory
  - web_search
  - fetch_webpage
  - fetch_pdf
```

## Available Tools

### Filesystem Tools

| Tool | Description |
|------|-------------|
| `list_directory` | List contents of a directory |
| `read_file` | Read contents of a file (max 1MB) |
| `write_file` | Write content to a file |
| `create_directory` | Create a new directory |

### Research Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web via DuckDuckGo (returns up to 10 results) |
| `fetch_webpage` | Fetch a webpage and convert to plain text |
| `fetch_pdf` | Fetch a PDF and extract text content (max 50MB) |

## Example Sessions

### Coding Agent

```
$ bedrock-agent --config config/coding_agent.yaml

Bedrock Agent CLI
Model: us.anthropic.claude-opus-4-5-20251101-v1:0
Tools: list_directory, read_file, write_file, create_directory
Type /help for available commands, /exit to quit.

You: List the files in the current directory

Agent: I'll list the contents of the current directory for you.

[Tool: list_directory(path=".")]
  Contents of '.': - README.md (file)...

The current directory contains:
- **README.md** - Project documentation
- **pyproject.toml** - Python project configuration
- **src/** - Source code directory
- **config/** - Configuration files

You: /exit
Goodbye!
```

### Research Agent

```
$ bedrock-agent --config config/research_agent.yaml

Bedrock Agent CLI
Model: us.anthropic.claude-opus-4-5-20251101-v1:0
Tools: web_search, fetch_webpage, fetch_pdf
Type /help for available commands, /exit to quit.

You: What are the latest developments in quantum computing?

Agent: I'll search for recent developments in quantum computing.

[Tool: web_search(query="quantum computing latest developments 2024")]
  Search results for 'quantum computing latest developments 2024'...

[Tool: fetch_webpage(url="https://example.com/quantum-news")]
  Content from 'https://example.com/quantum-news'...

Based on my research, here are the key recent developments in quantum computing:

1. **Error Correction Advances**: ...
2. **New Qubit Technologies**: ...
3. **Industry Milestones**: ...

Sources:
- https://example.com/quantum-news
- https://example.com/quantum-research

You: /exit
Goodbye!
```

## Creating Custom Agents

You can create your own agent configurations by:

1. Creating a new YAML file in the `config/` directory
2. Specifying the model, system prompt, and tools
3. Running with `bedrock-agent --config config/your_agent.yaml`

Mix and match tools from both filesystem and research categories to create specialized agents for your use case.

## License

MIT
