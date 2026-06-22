import os
import sys
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.message import add_messages
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware, SummarizationMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st

# Import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_docs_dir, save_document, read_pdf

# ----------------------------------------------------------------------
# 1. State Definition
# ----------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ----------------------------------------------------------------------
# 2. LLM Model Resolver
# ----------------------------------------------------------------------
def get_chat_model(selected_model: str, llm_engine: str, server_host: str) -> BaseChatModel:
    """Instantiates the correct LangChain chat model wrapper based on settings."""
    if llm_engine == "Google Gemini API":
       
        try:
            api_key = st.session_state.get("gemini_api_key", "").strip()
        except Exception:
            api_key = ""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            
        if not api_key:
            raise ValueError("Google Gemini API Key is missing. Please set it in the sidebar or GEMINI_API_KEY environment variable.")
            
        return ChatGoogleGenerativeAI(
            model=selected_model,
            google_api_key=api_key,
            temperature=0.2
        )
    elif llm_engine == "Ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=selected_model,
            base_url=server_host,
            temperature=0.2
        )
    else:  # llama.cpp
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=selected_model,
            openai_api_key="pct",  # dummy key
            openai_api_base=f"{server_host}/v1",
            temperature=0.2
        )

# ----------------------------------------------------------------------
# 3. Dynamic Tool Builder
# ----------------------------------------------------------------------
def build_document_tools(project_folder: str, target_doc: str):
    """
    Creates document manipulation tools bound to the active project folder 
    and the specific document being discussed.
    """
    proj_dir = get_docs_dir()

    @tool
    def read_current_document() -> str:
        """Reads the current contents of the active document being refined (e.g., prd_requirements.md)."""
        path = os.path.join(proj_dir, target_doc)
        if not os.path.exists(path):
            return f"The document '{target_doc}' does not exist yet. You can create it using the 'write_document' tool."
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading document: {e}"

    @tool
    def write_document(content: str) -> str:
        """Overwrites or updates the active document with new content. Use this to apply edits requested by the user."""
        try:
            save_document(target_doc, content)
            return f"Successfully updated '{target_doc}' with new content."
        except Exception as e:
            return f"Error writing document: {e}"

    @tool
    def read_other_workspace_files() -> str:
        """Reads other reference files in the workspace (e.g. constraints.txt, vision_mission.md) to gather context."""
        files = os.listdir(proj_dir)
        context_parts = []
        for file in sorted(files):
            if file == target_doc:
                continue
            path = os.path.join(proj_dir, file)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(file)[1].lower()
            content = ""
            if ext in ['.txt', '.md', '.json', '.yaml', '.yml']:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
            elif ext == '.pdf':
                content = read_pdf(path)
            else:
                continue
            context_parts.append(f"--- DOCUMENT: {file} ---\n{content}\n")
        return "\n".join(context_parts) if context_parts else "No other files found in workspace."

    return [read_current_document, write_document, read_other_workspace_files]

# ----------------------------------------------------------------------
# 4. LangGraph ReAct Graph Construction
# ----------------------------------------------------------------------
def run_document_refiner(
    chat_history: list,
    user_message: str,
    project_folder: str,
    target_doc: str,
    agent_system_prompt: str,
    selected_model: str,
    llm_engine: str,
    server_host: str
):
    """
    Compiles and runs a LangGraph ReAct Agent to discuss and modify a document.
    Streams output back or returns the final response.
    """
    # Explicitly set the active project in the environment for tool-execution threads
    os.environ["CURRENT_PROJECT"] = project_folder

    # 1. Resolve model and build tools
    chat_model = get_chat_model(selected_model, llm_engine, server_host)
    tools = build_document_tools(project_folder, target_doc)

    # Append strict tool enforcement rules to the system prompt
    enforced_system_prompt = (
        f"{agent_system_prompt}\n\n"
        "=== CRITICAL INSTRUCTIONS FOR TOOL USAGE ===\n"
        f"1. To apply any edits, updates, rewrites, or translations to '{target_doc}', you MUST call the `write_document` tool.\n"
        "2. Do NOT just output the updated text in your message or claim you have updated the file without calling the tool.\n"
        "3. You must execute the `write_document` tool to make your changes persistent.\n"
        "4. Always call `read_current_document` first if you need to know the current state before updating.\n"
        "============================================"
    )

    # 2. Compile agent using create_agent from langchain.agents with middleware
    graph = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=enforced_system_prompt,
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
            SummarizationMiddleware(model=chat_model, trigger=("messages", 20), keep=("messages", 10))
        ]
    )

    # 5. Convert standard chat history to LangChain Message format
    lc_messages = []
    for msg in chat_history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
            
    # Append the new user message
    lc_messages.append(HumanMessage(content=user_message))

    # 6. Execute the graph run
    inputs = {"messages": lc_messages}
    
    # We yield tokens or status updates back to Streamlit
    response_placeholder = st.empty()
    status_placeholder = st.empty()
    
    full_response = ""
    status_placeholder.markdown("*Agent thinking...*")
    
    # Run graph stream
    with open("agent_debug.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"--- START GRAPH RUN: target_doc={target_doc} ---\n")
        try:
            for output in graph.stream(inputs, config={"recursion_limit": 20}):
                log_file.write(f"Graph yield output keys: {list(output.keys())}\n")
                for node_name, state_update in output.items():
                    log_file.write(f"Node: {node_name}\n")
                    if state_update and "messages" in state_update:
                        new_msg = state_update["messages"][-1]
                        log_file.write(f"  Msg type: {type(new_msg).__name__}\n")
                        log_file.write(f"  Msg content: {repr(new_msg.content)}\n")
                        if hasattr(new_msg, "tool_calls"):
                            log_file.write(f"  Tool calls: {repr(new_msg.tool_calls)}\n")
                        
                        if node_name in ("agent", "model"):
                            if isinstance(new_msg, AIMessage) and new_msg.content:
                                full_response = new_msg.content
                                response_placeholder.markdown(full_response)
                            elif not isinstance(new_msg, AIMessage):
                                log_file.write(f"  WARNING: msg is not AIMessage\n")
                    else:
                        log_file.write(f"  No messages in state_update\n")
                    
                    if state_update and node_name == "tools" and "messages" in state_update:
                        tool_msg = state_update["messages"][-1]
                        status_placeholder.markdown(f"🛠️ *Executing Action:* {tool_msg.name}")
        except Exception as err:
            log_file.write(f"EXCEPTION DURING RUN: {err}\n")
            import traceback
            traceback.print_exc(file=log_file)
            raise err
        log_file.write(f"--- END GRAPH RUN: full_response length={len(full_response)} ---\n")
    status_placeholder.empty()
    return full_response
