import os
import sys

# Set up paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph_agent import run_document_refiner
import streamlit as st

# Mock project
os.environ["CURRENT_PROJECT"] = "default_project"

chat_history = []
user_message = "What is the vision statement in the current document?"
project_folder = "default_project"
target_doc = "vision_mission.md"
agent_system_prompt = "You are a helpful assistant."

# Ensure document exists
from utils import save_document
save_document(target_doc, "# 🎯 Vision Statement\nTo build a better world through tiffin deliveries.")

print("Running graph refiner with llama.cpp...")
try:
    response = run_document_refiner(
        chat_history=chat_history,
        user_message=user_message,
        project_folder=project_folder,
        target_doc=target_doc,
        agent_system_prompt=agent_system_prompt,
        selected_model="gemma-4-E2B-it-GGUF",
        llm_engine="llama.cpp (llama-server)",
        server_host="http://localhost:8080"
    )
    print("Graph execution complete.")
    print("Response:", response)
except Exception as e:
    import traceback
    print("ERROR DURING GRAPH RUN:")
    traceback.print_exc()
