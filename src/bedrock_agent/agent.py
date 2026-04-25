"""Agent implementation using LangChain and AWS Bedrock."""

import json
from pathlib import Path
from typing import Callable, Optional

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .config import AgentConfig
from .tools import TOOL_REGISTRY
from .normalizer import normalize_tool_calls, serialize_tool_calls, normalize_response_content


class BedrockAgent:
    """An agent that uses AWS Bedrock models with tools."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with the given configuration."""
        self.config = config
        self.conversation_history: list = []
        
        # Set up AWS credentials if provided in config
        boto3_kwargs = {"region_name": config.aws.region}
        if config.aws.access_key_id and config.aws.secret_access_key:
            boto3_kwargs["aws_access_key_id"] = config.aws.access_key_id
            boto3_kwargs["aws_secret_access_key"] = config.aws.secret_access_key

        boto_config = Config(read_timeout=1000)
        
        # Create Bedrock client
        self.bedrock_client = boto3.client("bedrock-runtime", config=boto_config, **boto3_kwargs)
        
        # Initialize the LLM
        self.llm = ChatBedrockConverse(
            client=self.bedrock_client,
            model_id=config.model.model_id,
            temperature=config.model.temperature,
            max_tokens=config.model.max_tokens
        )
        
        # Set up tools
        self.tools = []
        for tool_name in config.tools:
            if tool_name in TOOL_REGISTRY:
                self.tools.append(TOOL_REGISTRY[tool_name])
        
        # Bind tools to the LLM if any are configured
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm
        
        # Create tool lookup
        self.tool_lookup = {tool.name: tool for tool in self.tools}
    
    def _execute_tool(self, tool_call: dict) -> str:
        """Execute a tool call and return the result."""
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name not in self.tool_lookup:
            return f"Error: Unknown tool '{tool_name}'"
        
        tool = self.tool_lookup[tool_name]
        try:
            result = tool.invoke(tool_args)
            return result
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    def chat(
        self,
        user_input: str,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None
    ) -> str:
        """Process a user message and return the agent's response.
        
        Args:
            user_input: The user's message
            on_tool_call: Optional callback function that receives (tool_name, tool_args, tool_result)
                          for each tool invocation. Useful for displaying tool usage to the user.
        
        Returns:
            The agent's final text response.
        """
        # Add user message to history
        self.conversation_history.append(HumanMessage(content=user_input))
        
        # Build messages with system prompt
        messages = [SystemMessage(content=self.config.system_prompt)] + self.conversation_history
        
        # Get initial response
        response = self.llm_with_tools.invoke(messages)

        # Handle tool calls in a loop
        while response.tool_calls:
            # Add AI message with tool calls to history
            self.conversation_history.append(response)
            
            # Execute each tool call
            for tool_call in normalize_tool_calls(response.tool_calls):
                tool_result = self._execute_tool(tool_call)
                
                # Invoke callback if provided
                if on_tool_call:
                    on_tool_call(tool_call["name"], tool_call["args"], tool_result)
                
                tool_message = ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call["id"],
                )
                self.conversation_history.append(tool_message)
            
            # Get next response
            messages = [SystemMessage(content=self.config.system_prompt)] + self.conversation_history
            response = self.llm_with_tools.invoke(messages)
        
        # Make sure that AIMessage has a "text" component
        if type(response.content) == list and "text" not in [x["type"] for x in response.content]:
            response.content.append(
                {
                    "type": "text",
                    "text": "Empty response"
                }
            )

        # Add final response to history
        self.conversation_history.append(response)

        return normalize_response_content(response.content)
    
    def save_conversation(self, filepath: str) -> None:
        """Save the conversation history to a JSON file."""
        serialized = []
        for msg in self.conversation_history:
            msg_dict = {
                "type": msg.__class__.__name__,
                "content": (
                    normalize_response_content(msg.content)
                    if isinstance(msg, AIMessage)
                    else msg.content
                ),
            }
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                msg_dict["tool_calls"] = serialize_tool_calls(msg.tool_calls)
            if hasattr(msg, "tool_call_id"):
                msg_dict["tool_call_id"] = msg.tool_call_id
            serialized.append(msg_dict)
        
        with open(filepath, "w") as f:
            json.dump(serialized, f, indent=2)
    
    def load_conversation(self, filepath: str) -> None:
        """Load conversation history from a JSON file."""
        with open(filepath, "r") as f:
            serialized = json.load(f)
        
        self.conversation_history = []
        for msg_dict in serialized:
            msg_type = msg_dict["type"]
            content = msg_dict["content"]
            
            if msg_type == "HumanMessage":
                self.conversation_history.append(HumanMessage(content=content))
            elif msg_type == "AIMessage":
                tool_calls = msg_dict.get("tool_calls")
                msg = AIMessage(content=content, tool_calls=tool_calls or [])
                if "tool_calls" in msg_dict:
                    msg.tool_calls = msg_dict["tool_calls"]
                self.conversation_history.append(msg)
            elif msg_type == "ToolMessage":
                self.conversation_history.append(
                    ToolMessage(content=content, tool_call_id=msg_dict.get("tool_call_id", ""))
                )
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
