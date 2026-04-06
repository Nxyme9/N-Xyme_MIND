"""
Rosetta Stone - Wrapper for Ollama models without native tool calling
Parses tool calls from JSON in content field
"""

import json
import re
import ollama
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RosettaStone:
    """Wrapper for models without native tool calling capability"""
    
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model
    
    def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Call model with tools and parse tool calls from response.
        
        Returns:
            {
                "type": "tool_call" | "text",
                "name": str (if tool_call),
                "arguments": dict (if tool_call),
                "content": str (if text)
            }
        """
        # Format tools as text description
        tool_descriptions = self._format_tools(tools)
        
        # Create system prompt that forces tool usage
        if not system_prompt:
            system_prompt = f"""You are a helpful assistant with access to tools.

AVAILABLE TOOLS:
{tool_descriptions}

IMPORTANT: When the user's request requires using a tool, you MUST respond with ONLY valid JSON:
{{"name": "tool_name", "arguments": {{"param": "value"}}}}

Do NOT wrap in markdown. Do NOT add explanation. Just the JSON object."""
        
        # Prepare messages
        new_messages = [{"role": "system", "content": system_prompt}]
        new_messages.extend(messages)
        
        # Call model
        try:
            response = ollama.chat(
                model=self.model,
                messages=new_messages,
                **kwargs
            )
            
            content = response.get("message", {}).get("content", "").strip()
            
            # Strip markdown code blocks if present
            content = self._strip_markdown(content)
            
            # Try to parse as JSON tool call
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "name" in parsed:
                    arguments = parsed.get("arguments", parsed.get("parameters", {}))
                    if not isinstance(arguments, dict):
                        arguments = {}
                    return {
                        "type": "tool_call",
                        "name": parsed["name"],
                        "arguments": arguments
                    }
            except json.JSONDecodeError:
                pass
            
            # Return as text
            return {
                "type": "text",
                "content": content
            }
            
        except Exception as e:
            logger.error(f"RosettaStone error: {e}")
            return {
                "type": "error",
                "content": str(e)
            }
    
    def _strip_markdown(self, text: str) -> str:
        """Strip markdown code blocks from text"""
        # Remove ```json ... ``` blocks
        text = re.sub(r'```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```', '', text)
        return text.strip()
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """Format tools as text description"""
        descriptions = []
        for tool in tools:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            
            desc_text = f"- {name}: {desc}"
            
            if "parameters" in func:
                params = func.get("parameters", {})
                if isinstance(params, dict):
                    props = params.get("properties", {})
                    if props:
                        param_list = []
                        for param_name, param_info in props.items():
                            if isinstance(param_info, dict):
                                param_type = param_info.get("type", "any")
                                param_desc = param_info.get("description", "")
                                param_list.append(f"{param_name} ({param_type}): {param_desc}")
                            else:
                                param_list.append(str(param_name))
                        desc_text += f"\n  Parameters: {', '.join(param_list)}"
            
            descriptions.append(desc_text)
        
        return "\n".join(descriptions)


# Test it
if __name__ == "__main__":
    print("=== ROSETTA STONE TEST ===")
    print()
    
    rosetta = RosettaStone("qwen2.5-coder:7b")
    
    tools = [{
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Calculate math expressions",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"]
            }
        }
    }]
    
    messages = [{"role": "user", "content": "Calculate 5*3"}]
    
    result = rosetta.chat_with_tools(messages, tools)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if result["type"] == "tool_call":
        print(f"SUCCESS: Tool call parsed!")
        print(f"  Name: {result['name']}")
        print(f"  Arguments: {result['arguments']}")
    else:
        print(f"FAIL: Got text response instead of tool call")
        print(f"  Content: {result.get('content', '')[:200]}")
