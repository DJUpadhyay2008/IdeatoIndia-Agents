import os
import sys
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI

# Import from common package
from common.common_utils import get_docs_dir, save_document, read_pdf

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def get_chat_model(selected_model: str, llm_engine: str, server_host: str) -> BaseChatModel:
    """Instantiates the correct LangChain chat model wrapper based on settings."""
    if llm_engine == "Google Gemini API":
        try:
            import streamlit as st
            api_key = st.session_state.get("gemini_api_key", "").strip()
        except Exception:
            api_key = ""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            
        if not api_key:
            raise ValueError("Google Gemini API Key is missing. Please set it in the sidebar or GEMINI_API_KEY environment variable.")
            
        model = ChatGoogleGenerativeAI(
            model=selected_model,
            google_api_key=api_key,
            temperature=0.2
        )
    elif llm_engine == "Ollama":
        from langchain_ollama import ChatOllama
        model = ChatOllama(
            model=selected_model,
            base_url=server_host,
            temperature=0.2
        )
    else:  # llama.cpp
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(
            model=selected_model,
            openai_api_key="pct",  # dummy key
            openai_api_base=f"{server_host}/v1",
            temperature=0.2
        )
    return model

def build_document_tools(project_folder: str, target_doc: str, model=None, engine=None, host=None, minimized_context=""):
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
                from common.common_utils import strip_yaml_front_matter
                return strip_yaml_front_matter(f.read())
        except Exception as e:
            return f"Error reading document: {e}"

    @tool
    def write_document(content: str) -> str:
        """Overwrites or updates the active document with new content. Use this to apply edits requested by the user."""
        try:
            from common.common_utils import save_document_with_metadata
            # Automatically infer a title from the file name
            clean_name = target_doc.replace("architecture_", "").replace(".md", "").replace("_", " ").replace("-", " ")
            title = clean_name.title()
            if not title.lower().endswith("architecture") and not title.lower().endswith("document"):
                title += " Document"
            save_document_with_metadata(target_doc, content, title, model, engine, host)
            return f"Successfully updated '{target_doc}' and regenerated metadata and summaries."
        except Exception as e:
            return f"Error writing document: {e}"

    @tool
    def read_other_workspace_files() -> str:
        """Reads other reference files in the workspace (e.g. constraints.txt, vision_mission.md) to gather context."""
        if minimized_context:
            return minimized_context
            
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
    import streamlit as st
    from langgraph.prebuilt import create_react_agent

    os.environ["CURRENT_PROJECT"] = project_folder
    docs_dir = get_docs_dir()

    # 1. Run intent detection using the index
    from common.common_utils import detect_intent_and_dependencies, load_minimized_context
    intent = detect_intent_and_dependencies(
        user_message=user_message,
        docs_dir=docs_dir,
        model=selected_model,
        engine=llm_engine,
        host=server_host
    )
    
    # 2. Load minimized context based on intent result
    minimized_context = load_minimized_context(intent, docs_dir)

    chat_model = get_chat_model(selected_model, llm_engine, server_host)
    tools = build_document_tools(
        project_folder=project_folder,
        target_doc=target_doc,
        model=selected_model,
        engine=llm_engine,
        host=server_host,
        minimized_context=minimized_context
    )

    enforced_system_prompt = (
        f"{agent_system_prompt}\n\n"
        "=== RELEVANT CONTEXT (MINIMIZED) ===\n"
        f"{minimized_context}\n\n"
        "=== CRITICAL INSTRUCTIONS FOR TOOL USAGE ===\n"
        f"1. To apply any edits, updates, rewrites, or translations to '{target_doc}', you MUST call the `write_document` tool.\n"
        "2. Do NOT just output the updated text in your message or claim you have updated the file without calling the tool.\n"
        "3. You must execute the `write_document` tool to make your changes persistent.\n"
        "4. Always call `read_current_document` first if you need to know the current state before updating.\n"
        "5. If the user asks for any change, rewrite, addition, deletion, or modification, do NOT reply with just 'Yes' or ask for confirmation/clarification. Instead, IMMEDIATELY call the `read_current_document` tool to get the content, make the changes, call the `write_document` tool to save them, and then explain the updates to the user.\n"
        "6. Do not wait for the user's permission to edit the file. If details are missing, make reasonable assumptions/extrapolations and update the document directly. Your primary goal is to keep the document updated.\n"
        "============================================"
    )

    graph = create_react_agent(
        model=chat_model,
        tools=tools,
        prompt=enforced_system_prompt,
    )

    lc_messages = []
    for msg in chat_history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
            
    lc_messages.append(HumanMessage(content=user_message))
    inputs = {"messages": lc_messages}
    
    response_placeholder = st.empty()
    status_placeholder = st.empty()
    
    full_response = ""
    status_placeholder.markdown("*Agent thinking...*")
    
    MAX_RETRIES = 3
    last_error = None

    with open("agent_debug.log", "a", encoding="utf-8") as log_file:
        for attempt in range(1, MAX_RETRIES + 1):
            log_file.write(f"--- START GRAPH RUN (attempt {attempt}/{MAX_RETRIES}): target_doc={target_doc} ---\n")
            full_response = ""
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

                        if state_update and node_name == "tools" and "messages" in state_update:
                            tool_msg = state_update["messages"][-1]
                            status_placeholder.markdown(f"🛠️ *Executing Action:* {tool_msg.name}")

                log_file.write(f"--- END GRAPH RUN: full_response length={len(full_response)} ---\n")
                break  # Success — exit the retry loop

            except Exception as err:
                last_error = err
                log_file.write(f"EXCEPTION on attempt {attempt}: {err}\n")
                import traceback
                traceback.print_exc(file=log_file)
                if attempt < MAX_RETRIES:
                    import time
                    wait = 2 ** attempt  # exponential back-off: 2s, 4s
                    status_placeholder.markdown(f"⚠️ *Connection issue, retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})...*")
                    time.sleep(wait)
                else:
                    # All retries exhausted — surface a user-friendly error
                    error_message = str(last_error)
                    if any(k in error_message.lower() for k in ["connection refused", "connection error", "connecterror", "connection"]):
                        full_response = (
                            "⚠️ **Connection Refused / LLM Service Offline**\n\n"
                            "The agent could not connect to the local LLM server after multiple retries. Please ensure that either:\n"
                            "1. **Ollama** (typically on port `11434`) is running.\n"
                            "2. **llama-server** (typically on port `8080`) is running.\n\n"
                            "Or switch your LLM Engine in the sidebar configuration.\n\n"
                            f"*Technical details: {error_message}*"
                        )
                    else:
                        full_response = (
                            "⚠️ **Agent Execution Error**\n\n"
                            "An unexpected error occurred while refining the document after multiple retries.\n\n"
                            f"*Technical details: {error_message}*"
                        )
                    response_placeholder.markdown(full_response)

    status_placeholder.empty()
    return full_response
