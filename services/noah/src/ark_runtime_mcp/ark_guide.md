## ARK Platform Resources

ARK provides Kubernetes-native resources for AI workloads. All resources follow the ark.mckinsey.com API group.

### Core Resources

**Agent** - Individual AI agents with specific capabilities
- Defines prompt, model, tools, and execution environment
- Can be standalone or part of a team
- Executes queries and interacts with external systems
- Required fields: name, version, role, guidance, model
- Optional: tools, leader, code_execution, talk_with, term_regexes

**Model** - LLM configurations and parameters  
- Specifies model type, API endpoints, and parameters
- Referenced by agents for inference
- Supports multiple providers (OpenAI, Azure, local models)

**Query** - Reusable prompts and instructions
- Template-based prompts with parameters
- Can be executed by agents or teams
- Supports complex multi-step workflows

**Team** - Groups of agents working together
- Orchestrates multi-agent workflows
- Defines agent roles and interactions
- Enables collaborative problem solving

### Tool and Integration Resources

**MCPServer** - Model Context Protocol servers providing tools
- Exposes external tools to agents (kubectl, APIs, etc.)
- Defines tool capabilities and permissions
- Enables agent access to external systems

**A2AServer** - Agent-to-Agent communication servers
- Facilitates inter-agent communication
- Manages agent discovery and messaging
- Supports distributed agent workflows

**Tool** - External integrations and capabilities
- Defines individual tools available to agents
- Can be provided by MCP servers or other sources
- Includes authentication and access controls

### Runtime and Support Resources

**ExecutionEngine** - Runtime environments for agents
- Supports LangChain, CrewAI, AutoGen frameworks
- Manages agent execution and lifecycle
- Provides isolation and resource management

**Evaluator** - Performance measurement and scoring
- Defines metrics and evaluation criteria
- Monitors agent performance and quality
- Supports continuous improvement workflows

**Memory** - Persistent storage for agent state
- Stores conversation history and context
- Enables stateful agent interactions
- Supports long-term learning and adaptation
