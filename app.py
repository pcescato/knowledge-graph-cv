# app_v7_cloudrun_revised.py
# Revised for Cloud Run + Streamlit + Gemini (stable)

import streamlit as st
import google.generativeai as genai
import os
import json
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ─────────────────────────────────────────────
# Environment & API
# ─────────────────────────────────────────────
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("GOOGLE_API_KEY not set")
    st.stop()

genai.configure(api_key=api_key)

# ─────────────────────────────────────────────
# Cache Gemini model (Cloud Run friendly)
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_model(model_name: str = "models/gemini-3-flash-preview"):
    return genai.GenerativeModel(model_name)

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "graph_data" not in st.session_state:
    st.session_state.graph_data = None
if "focused_node" not in st.session_state:
    st.session_state.focused_node = None
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = "gemini-3-flash-preview"
if "viz_mode" not in st.session_state:
    st.session_state.viz_mode = "Network Graph"

# ─────────────────────────────────────────────
# System prompt (kept as content, not constructor arg)
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert Knowledge Engineer analyzing professional CVs to create DENSE, CONNECTED knowledge graphs.

EXTRACTION STRATEGY:
1. PERSON NODE: Create exactly ONE node for the candidate (use their name from CV)
2. CORE SKILLS: Extract ALL significant technical skills mentioned (10-15 skills including languages, frameworks, tools)
3. KEY PROJECTS: Identify ALL significant projects (5-8 projects)
4. PROFESSIONAL ROLES: Extract all mentioned positions/companies (3-5 roles)
5. EXPERTISE AREAS: Create 3-5 high-level concept nodes

RELATIONSHIPS:
- Person -> MASTERS -> Skills
- Person -> CREATED -> Projects
- Project -> USES -> Skills (3-5 minimum)
- Skill -> PART_OF -> Concepts
- Concept -> IMPLEMENTED_IN -> Projects

Return STRICT JSON with nodes and edges.
"""

# ─────────────────────────────────────────────
# Prompt helpers
# ─────────────────────────────────────────────

def build_prompt(system_prompt: str, user_prompt: str) -> str:
    return f"""
SYSTEM:
{system_prompt}

USER:
{user_prompt}
"""

# ─────────────────────────────────────────────
# Gemini call wrapper
# ─────────────────────────────────────────────

def run_gemini(user_prompt: str, model_name: str):
    model = load_model(f"models/{model_name}" if not model_name.startswith("models/") else model_name)
    prompt = build_prompt(SYSTEM_PROMPT, user_prompt)
    response = model.generate_content(prompt)
    return response.text

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────

st.set_page_config(page_title="Knowledge Graph CV", layout="wide")
st.title("Knowledge Graph Portfolio")

with st.sidebar:
    st.header("Settings")
    st.session_state.gemini_model = st.selectbox(
        "Gemini model",
        ["gemini-3-flash-preview"],
        index=0,
    )
    st.session_state.viz_mode = st.radio(
        "Visualization",
        ["Network Graph", "Flow", "Matrix"],
        index=0,
    )

cv_text = st.text_area("Paste CV text", height=220)

if st.button("Generate / Update Graph") and cv_text:
    with st.spinner("Analyzing CV with Gemini…"):
        raw = run_gemini(cv_text, st.session_state.gemini_model)
        try:
            st.session_state.graph_data = json.loads(raw)
        except Exception:
            st.error("Failed to parse Gemini output as JSON")
            st.code(raw)

# ─────────────────────────────────────────────
# Visualizations
# ─────────────────────────────────────────────

def render_network(graph):
    nodes = [Node(id=n["id"], label=n["label"], size=15) for n in graph.get("nodes", [])]
    edges = [Edge(source=e["source"], target=e["target"], label=e.get("label", "")) for e in graph.get("edges", [])]
    config = Config(width=900, height=600, directed=True, physics=True)
    agraph(nodes=nodes, edges=edges, config=config)


def render_matrix(graph):
    skills = [n["label"] for n in graph.get("nodes", []) if n.get("type") == "skill"]
    projects = [n["label"] for n in graph.get("nodes", []) if n.get("type") == "project"]
    data = []
    for s in skills:
        row = []
        for p in projects:
            row.append(1)
        data.append(row)
    df = pd.DataFrame(data, index=skills, columns=projects)
    fig = px.imshow(df, aspect="auto", title="Skills × Projects")
    st.plotly_chart(fig, use_container_width=True)


if st.session_state.graph_data:
    if st.session_state.viz_mode == "Network Graph":
        render_network(st.session_state.graph_data)
    elif st.session_state.viz_mode == "Matrix":
        render_matrix(st.session_state.graph_data)
    else:
        st.json(st.session_state.graph_data)
