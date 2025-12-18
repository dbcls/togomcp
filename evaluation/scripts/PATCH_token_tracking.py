#!/usr/bin/env python3
"""
PATCH: Add Token Usage Tracking to TogoMCP Tests

This patch modifies automated_test_runner.py to capture exact token usage
and costs from the Agent SDK's ResultMessage.

Apply this patch by replacing the _make_togomcp_call method.
"""

# NEW VERSION OF _make_togomcp_call METHOD
# Replace lines ~280-330 in automated_test_runner.py

async def _make_togomcp_call(
    self, 
    question: str,
    mcp_servers: Optional[Dict] = None
) -> Dict:
    """Make TogoMCP call using Agent SDK with ClaudeSDKClient."""
    start_time = time.time()
    
    if mcp_servers is None:
        mcp_servers = self.config["mcp_servers"]
    
    try:
        options = ClaudeAgentOptions(
            system_prompt=self.config["togomcp_system_prompt"],
            mcp_servers=mcp_servers,
            model=self.config["model"],
            allowed_tools=self.config["allowed_tools"],
            disallowed_tools=self.config["disallowed_tools"],
            can_use_tool=self._auto_approve_mcp_tools
        )
        
        tool_uses = []
        final_text = None
        usage_data = None  # NEW: Capture usage data
        total_cost_usd = None  # NEW: Capture cost
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(question)
            
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    if hasattr(message, 'content') and isinstance(message.content, list):
                        for block in message.content:
                            block_type = getattr(block, 'type', type(block).__name__)
                            if block_type == "tool_use" or "ToolUse" in type(block).__name__:
                                tool_name = getattr(block, 'name', 'unknown')
                                tool_input = getattr(block, 'input', {})
                                tool_uses.append({
                                    "name": tool_name,
                                    "input": tool_input
                                })
                
                if isinstance(message, ResultMessage):
                    if hasattr(message, 'result') and isinstance(message.result, str):
                        final_text = message.result
                    
                    # NEW: Extract usage data from ResultMessage
                    if hasattr(message, 'usage'):
                        usage_data = message.usage
                    
                    # NEW: Extract cost from ResultMessage
                    if hasattr(message, 'total_cost_usd'):
                        total_cost_usd = message.total_cost_usd
        
        elapsed_time = time.time() - start_time
        
        result = {
            "success": True,
            "text": final_text if final_text else "[No text content extracted]",
            "tool_uses": tool_uses,
            "elapsed_time": elapsed_time
        }
        
        # NEW: Add usage data if available
        if usage_data:
            result["usage"] = usage_data
        
        # NEW: Add cost if available
        if total_cost_usd is not None:
            result["total_cost_usd"] = total_cost_usd
        
        return result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        import traceback
        return {
            "success": False,
            "error": f"{str(e)}\n{traceback.format_exc()}",
            "elapsed_time": elapsed_time
        }


# NEW: Also update run_single_evaluation to save TogoMCP token data
# Add these lines after line ~470 (where baseline tokens are saved):

# Add TogoMCP token usage if available
if togomcp_result["success"] and "usage" in togomcp_result:
    usage = togomcp_result["usage"]
    result["togomcp_input_tokens"] = usage.get("input_tokens", 0)
    result["togomcp_output_tokens"] = usage.get("output_tokens", 0)
    result["togomcp_cache_creation_tokens"] = usage.get("cache_creation_input_tokens", 0)
    result["togomcp_cache_read_tokens"] = usage.get("cache_read_input_tokens", 0)

# Add TogoMCP cost if available
if togomcp_result["success"] and "total_cost_usd" in togomcp_result:
    result["togomcp_cost_usd"] = togomcp_result["total_cost_usd"]


# NEW: Update CSV fieldnames in _export_to_csv method
# Add these fields to the fieldnames list around line ~510:

fieldnames = [
    "question_id", "date", "category", "question_text",
    "baseline_success", "baseline_actually_answered", "baseline_has_expected", "baseline_confidence",
    "baseline_text", "baseline_error", "baseline_time",
    "baseline_input_tokens", "baseline_output_tokens",
    "togomcp_success", "togomcp_has_expected", "togomcp_confidence",
    "togomcp_text", "togomcp_error", "togomcp_time",
    "togomcp_input_tokens", "togomcp_output_tokens",  # NEW
    "togomcp_cache_creation_tokens", "togomcp_cache_read_tokens",  # NEW
    "togomcp_cost_usd",  # NEW
    "tools_used", "tool_details",
    "value_add", "expected_answer", "notes"
]
