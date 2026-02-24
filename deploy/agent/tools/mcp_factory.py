"""
MCP Tool Factory - Creates MCP clients from environment variables.

Environment variable format:
    MCP_SERVERS="server1=http://host1:port1/sse,server2=http://host2:port2/sse"

Each key/value pair creates an MCPClient that can be used with the Strands agent.
"""

import os
from typing import Dict, List
from mcp.client.sse import sse_client
from strands.tools.mcp import MCPClient


def parse_mcp_servers_env() -> Dict[str, str]:
    """
    Parse MCP_SERVERS environment variable into a dictionary.

    Expected format: "name1=url1,name2=url2"
    Example: "prometheus=http://localhost:8001/sse,kubernetes=http://localhost:8002/sse"

    Returns:
        Dict mapping server names to their SSE URLs
    """
    env_value = os.environ.get("MCP_SERVERS", "")

    if not env_value:
        return {}

    servers = {}
    for pair in env_value.split(","):
        pair = pair.strip()
        if "=" in pair:
            name, url = pair.split("=", 1)
            name = name.strip()
            url = url.strip()
            if name and url:
                servers[name] = url

    return servers


def get_mcp_tools() -> List[MCPClient]:
    """
    Create MCP clients for each server defined in the MCP_SERVERS env var.

    Returns:
        List of MCPClient instances ready to use with the Strands agent
    """
    servers = parse_mcp_servers_env()
    clients = []

    for name, url in servers.items():
        client = MCPClient(lambda u=url: sse_client(u))
        clients.append(client)
        print(f"Created MCP client: {name} -> {url}")

    return clients
