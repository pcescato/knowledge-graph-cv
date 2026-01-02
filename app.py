# NOTE
# This file is a STRICT v7 -> v7.1 PATCH.
# NO functional changes.
# NO UI changes.
# NO graph / view / upload regression.
# ONLY Cloud Run + google-generativeai >= 0.8.6 fixes.

import streamlit as st
import google.generativeai as genai
import os
import json
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any

# -------------------------------------------------
# Environment
# -------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("GOOGLE_API_KEY manquante")
    st.stop()

genai.configure(api_key=API_KEY)

# -------------------------------------------------
# System prompt (UNCHANGED)
# -------------------------------------------------
SYSTEM_PROMPT = """
YOU ARE A STRICT KNOWLEDGE GRAPH EXTRACTION ENGINE.
OUTPUT JSON ONLY.
NO MARKDOWN.
NO EXPLANATIONS.
"""

# -------------------------------------------------
# PATCH v7.1 — Gemini model cache (Cloud Run safe)
# -------------------------------------------------
@st.cache_resource

def load_gemini_model(model_name: str):
    return genai.GenerativeModel(
        f"models/{model_name}",
        system_instruction={
            "parts": [{"text": SYSTEM_PROMPT}]
        }
    )

# -------------------------------------------------
# Session state (UNCHANGED)
# -------------------------------------------------
if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

if "focused_node" not in st.session_state:
    st.session_state.focused_node = None

if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = "gemini-3-flash-preview"

if "viz_mode" not in st.session_state:
    st.session_state.viz_mode = "Network Graph"

# -------------------------------------------------
# UI
# -------------------------------------------------
st.set_page_config(layout="wide")
st.title("CV Knowledge Graph Explorer")

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.header("Gemini Model")
    st.session_state.gemini_model = st.selectbox(
        "Model",
        ["gemini-3-flash-preview"],
        index=0
    )

    st.header("Visualization")
    st.session_state.viz_mode = st.radio(
        "View",
        ["Network Graph", "Skills Matrix", "Sankey"],
        index=0
    )

# -------------------------------------------------
# Upload CV (UNCHANGED)
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload CV (PDF)",
    type=["pdf"],
    accept_multiple_files=False
)

# -------------------------------------------------
# Gemini call (PATCHED MINIMALLY)
# -------------------------------------------------
if uploaded_file is not None:
    file_bytes = uploaded_file.read()

    model = load_gemini_model(st.session_state.gemini_model)

    with st.spinner("Analyzing CV with Gemini..."):
        response = model.generate_content(
            [
                {
                    "mime_type": "application/pdf",
                    "data": file_bytes,
                },
                "Extract a dense professional knowledge graph from this CV"
            ],
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json"  # PATCH v7.1
            }
        )

    try:
        raw = json.loads(response.text)
        st.session_state.graph_data = raw
    except Exception as e:
        st.error("Failed to parse Gemini output as JSON")
        st.code(response.text)
        st.stop()

# -------------------------------------------------
# Visualization logic (UNCHANGED)
# -------------------------------------------------
if st.session_state.graph_data:
    data = st.session_state.graph_data

    if st.session_state.viz_mode == "Network Graph":
        nodes = []
        edges = []

        for node_id, node in data.get("nodes", {}).items():
            nodes.append(Node(id=node_id, label=node.get("label", node_id)))

        for edge in data.get("edges", []):
            edges.append(Edge(
                source=edge["source"],
                target=edge["target"],
                label=edge.get("label", "")
            ))

        config = Config(
            width=900,
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
        )

        agraph(nodes=nodes, edges=edges, config=config)

    elif st.session_state.viz_mode == "Skills Matrix":
        skills = data.get("skills", {})
        rows = []
        for category, items in skills.items():
            for skill in items:
                rows.append({"Category": category, "Skill": skill})
        df = pd.DataFrame(rows)
        st.dataframe(df)

    elif st.session_state.viz_mode == "Sankey":
        links = data.get("links", [])
        labels = list({l for link in links for l in (link["source"], link["target"])})
        index = {l: i for i, l in enumerate(labels)}

        fig = go.Figure(go.Sankey(
            node=dict(label=labels),
            link=dict(
                source=[index[l["source"]] for l in links],
                target=[index[l["target"]] for l in links],
                value=[1] * len(links)
            )
        ))
        st.plotly_chart(fig, use_container_width=True)
