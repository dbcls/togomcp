#!/usr/bin/env python3
"""
Agent SDK Token Inspector

This script helps identify if the Agent SDK exposes token usage information
that we can use for exact cost calculations instead of estimation.

Usage:
    python inspect_agent_sdk_tokens.py "What is the capital of France?"
"""

import asyncio
import sys
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk import AssistantMessage, ResultMessage

async def inspect_sdk_response():
    """Run a simple query and inspect all response attributes."""
    
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Hi, what is 2+2?"
    
    print(f"Testing query: {query}\n")
    print("="*80)
    
    # Basic setup
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        mcp_servers={
            "togomcp": {
                "type": "http",
                "url": "https://togomcp.rdfportal.org/mcp"
            }
        }
    )
    
    print("Inspecting Agent SDK response messages...\n")
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query(query)
        
        message_count = 0
        async for message in client.receive_response():
            message_count += 1
            print(f"\n--- Message {message_count} ---")
            print(f"Type: {type(message).__name__}")
            
            # List all attributes
            attrs = [a for a in dir(message) if not a.startswith('_')]
            print(f"Attributes: {', '.join(attrs[:10])}{'...' if len(attrs) > 10 else ''}")
            
            # Check for usage-related attributes
            usage_attrs = [a for a in attrs if 'usage' in a.lower() or 'token' in a.lower()]
            if usage_attrs:
                print(f"⭐ FOUND USAGE/TOKEN ATTRIBUTES: {usage_attrs}")
                for attr in usage_attrs:
                    try:
                        value = getattr(message, attr)
                        print(f"   {attr}: {value}")
                    except Exception as e:
                        print(f"   {attr}: Error accessing - {e}")
            
            # Check common fields
            for attr in ['content', 'result', 'data', 'metadata', 'stats']:
                if hasattr(message, attr):
                    value = getattr(message, attr)
                    print(f"{attr}: {type(value).__name__} = {str(value)[:100]}...")
            
            if isinstance(message, ResultMessage):
                print("\n✅ This is the final result message")
                print("Checking for token info in result...")
                if hasattr(message, 'result'):
                    print(f"Result type: {type(message.result)}")
    
    print("\n" + "="*80)
    print("\nCONCLUSION:")
    print("If no 'usage' or 'token' attributes were found, the Agent SDK")
    print("does not expose token counts in its current form.")
    print("\nYou would need to either:")
    print("  1. Switch to direct API calls (gives exact tokens)")
    print("  2. Use the Anthropic Usage API (query account usage)")
    print("  3. Continue with estimation (current approach)")

if __name__ == "__main__":
    try:
        asyncio.run(inspect_sdk_response())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
