import os
import sys
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
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
        from langchain_google_genai import ChatGoogleGenerativeAI
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
        from langchain_community.chat_models import ChatOpenAI
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
            # Update session state if running inside Streamlit
            var_map = {
                "vision_mission.md": "vision_mission_result",
                "market_research.md": "research_result",
                "prd_requirements.md": "requirements_result",
                "launch_plan.md": "planning_result",
                "technical_architecture.md": "architecture_result"
            }
            if target_doc in var_map:
                state_var = var_map[target_doc]
                if state_var in st.session_state:
                    st.session_state[state_var] = content
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
    # 1. Resolve model and bind tools
    chat_model = get_chat_model(selected_model, llm_engine, server_host)
    tools = build_document_tools(project_folder, target_doc)
    model_with_tools = chat_model.bind_tools(tools)

    # 2. Define conditional router edge
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If model called a tool, transition to 'tools' node
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # 3. Define agent execution node
    def call_agent(state: AgentState):
        messages = state["messages"]
        # Ensure system prompt is first message
        sys_msg = SystemMessage(content=agent_system_prompt)
        response = model_with_tools.invoke([sys_msg] + messages)
        return {"messages": [response]}

    # 4. Compile workflow graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    graph = workflow.compile()

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
    for output in graph.stream(inputs, config={"recursion_limit": 20}):
        # Event structure is a dict mapping node_name -> state update
        for node_name, state_update in output.items():
            if node_name == "agent":
                # Print/render new agent message content
                new_msg = state_update["messages"][-1]
                if isinstance(new_msg, AIMessage) and new_msg.content:
                    full_response = new_msg.content
                    response_placeholder.markdown(full_response)
            elif node_name == "tools":
                # Let user know what tool is running
                tool_msg = state_update["messages"][-1]
                status_placeholder.markdown(f"🛠️ *Executing Action:* {tool_msg.name}")
                
    status_placeholder.empty()
    return full_response
