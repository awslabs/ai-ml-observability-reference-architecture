"""
Streamlit app for testing the ML Optimization Agent.
"""

import streamlit as st
import requests
import json
import os

# Configuration
AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8080")

st.set_page_config(
    page_title="AI/ML Optimization Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI/ML Optimization Agent")
st.markdown("Ask questions about your AI/ML workloads and get optimization recommendations.")

# Sidebar with info
with st.sidebar:
    st.header("About")
    st.markdown("""
    This agent helps identify inefficiencies in AI/ML workloads:
    - GPU utilization issues
    - Resource right-sizing
    - Cost optimization
    - Performance bottlenecks
    """)
    
    st.header("Configuration")
    agent_url = st.text_input("Agent URL", value=AGENT_URL)
    
    # Health check
    try:
        response = requests.get(f"{agent_url}/health", timeout=2)
        if response.status_code == 200:
            health = response.json()
            st.success("✅ Agent is healthy")
            if health.get("mcp_servers"):
                st.info(f"MCP Servers: {health['mcp_servers']}")
        else:
            st.error("❌ Agent is not responding")
    except Exception as e:
        st.error(f"❌ Cannot connect to agent: {str(e)}")
    st.header("Export")
    if st.session_state.get("messages"):
        markdown = "# AI/ML Optimization Agent - Conversation\n\n"
        for m in st.session_state.messages:
            role = "🧑 User" if m["role"] == "user" else "🤖 Assistant"
            markdown += f"## {role}\n{m['content']}\n\n---\n\n"

        st.download_button(
            "📥 Download as Markdown",
            markdown,
            "ai_ml_agent_conversation.md",
            "text/markdown"
        )
    else:
        st.caption("No conversation to export yet")
# Example prompts
st.subheader("Example Prompts")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Analyze GPU Usage"):
        st.session_state.prompt = "Show me GPU utilization metrics for all training jobs in the last hour"

with col2:
    if st.button("💰 Cost Analysis"):
        st.session_state.prompt = "What are the most expensive workloads running right now and can we optimize them?"

with col3:
    if st.button("🔍 Debug Job"):
        st.session_state.prompt = "Why is my training job showing high 5XX errors?"

# Chat interface
st.subheader("Chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about your ML workloads..."):
    st.session_state.prompt = prompt

# Process prompt
if "prompt" in st.session_state and st.session_state.prompt:
    prompt = st.session_state.prompt
    del st.session_state.prompt
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Stream agent response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Make streaming request
            with requests.post(
                f"{agent_url}/prompt",
                json={"prompt": prompt},
                stream=True,
                timeout=300,
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            try:
                                data = json.loads(data_str)
                                
                                if data.get('type') == 'text':
                                    content = data.get('content', '')
                                    full_response += content
                                    message_placeholder.markdown(full_response + "▌")
                                elif data.get('type') == 'error':
                                    st.error(f"Error: {data.get('content')}")
                                    break
                                elif data.get('type') == 'done':
                                    break
                            except json.JSONDecodeError:
                                continue
                
                message_placeholder.markdown(full_response)
        
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to agent: {str(e)}")
            full_response = f"Error: {str(e)}"
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Clear chat button
if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()
