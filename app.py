import streamlit as st
import google.generativeai as genai
import os
import json
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv

# Chargement des variables d'env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("Clé API manquante ! Configurez GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=api_key)

SYSTEM_PROMPT = """You are an expert Knowledge Engineer and Entity Extraction specialist. 
Your goal is to analyze professional documents (CVs, portfolios, technical articles) and transform them into a structured Knowledge Graph.

OUTPUT FORMAT:
You must strictly respond in valid JSON format. No conversational filler or markdown code blocks. 
Structure:
{
  "nodes": [
    {"id": "unique_id", "label": "Entity Name", "type": "Category", "importance": 1-10}
  ],
  "edges": [
    {"from": "source_id", "to": "target_id", "label": "relationship_verb"}
  ]
}

ALLOWED NODE CATEGORIES:
- "Person": The candidate/author.
- "Role": Job titles or positions.
- "Skill": Technologies, frameworks, or soft skills.
- "Project": Specific achievements or work samples.
- "Entity": Companies, schools, or organizations.
- "Concept": Theoretical topics (e.g., "Serverless", "Graph Theory").

ALLOWED RELATIONSHIPS:
- "HELD_POSITION" (Person -> Role)
- "WORKED_AT" (Role -> Entity)
- "MASTERS" (Person -> Skill)
- "CREATED" (Role/Person -> Project)
- "USED" (Project -> Skill)
- "AUTHOR_OF" (Person -> Project/Article)
- "COVERS" (Project/Article -> Concept)

CRITICAL GUIDELINES:
1. STRICT JSON ONLY. Do not add any text before or after the JSON.
2. MULTIMODAL ANALYSIS: If an image is provided (architecture diagram, certification), extract the text and concepts to integrate them into the graph.
3. GRANULARITY: Create separate nodes for specific technologies.
4. IMPORTANCE: Assign a weight (1-10) based on how central the node is to the user's career."""

model = genai.GenerativeModel('models/gemini-3-flash-preview', system_instruction=SYSTEM_PROMPT)

st.set_page_config(layout="wide")
st.title("🌐 AI Knowledge Graph CV Builder")

uploaded_file = st.file_uploader("Dépose ton CV (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Analyse par Gemini en cours..."):
        file_bytes = uploaded_file.read()
        
        response = model.generate_content([
            {"mime_type": "application/pdf", "data": file_bytes},
            "Extract the knowledge graph. Focus on the 20 most important entities."
        ])
        
        try:
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            # --- 1. DÉFINITION DE LA CONFIGURATION (INDISPENSABLE ICI) ---
            config = Config(
                width=1200,
                height=800,
                directed=True, 
                physics=True,
                nodeHighlightBehavior=True,
                highlightColor="#F7A7A7",
                collapsible=True,
                physicsOptions={
                    "forceAtlas2Based": {
                        "gravitationConstant": -150,
                        "centralGravity": 0.005,
                        "springLength": 150,
                        "springConstant": 0.05,
                    },
                    "solver": "forceAtlas2Based",
                    "stabilization": {"enabled": True, "iterations": 200}
                }
            )

            # --- 2. BARRE LATÉRALE ET FILTRAGE ---
            with st.sidebar:
                st.header("🔍 Filtres")
                all_types = list(set(n['type'] for n in data['nodes']))
                selected_types = st.multiselect("Catégories :", all_types, default=all_types)
                st.divider()
                details_container = st.empty()

            filtered_nodes_data = [n for n in data['nodes'] if n['type'] in selected_types]
            filtered_node_ids = [n['id'] for n in filtered_nodes_data]
            filtered_edges_data = [
                e for e in data['edges'] 
                if e['from'] in filtered_node_ids and e['to'] in filtered_node_ids
            ]

            # --- 3. CRÉATION DES OBJETS ---
            nodes = [Node(id=n['id'], 
                          label=n['label'], 
                          size=n.get('importance', 5)*3 + 10, 
                          color="#00ADEE" if n['type'] == 'Skill' else "#F39C12") 
                     for n in filtered_nodes_data]

            edges = [Edge(source=e['from'], target=e['to']) for e in filtered_edges_data]

            # --- 4. AFFICHAGE (Le 'config' est maintenant bien défini) ---
            st.success("Graphe généré !")
            clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)

            # --- 5. GESTION DU CLIC ---
            if clicked_node_id:
                node_info = next((n for n in data['nodes'] if n['id'] == clicked_node_id), None)
                if node_info:
                    with details_container.container():
                        st.subheader(f"📄 {node_info['label']}")
                        st.write(f"**Type :** {node_info['type']}")
                        st.write(f"**Importance :** {node_info.get('importance', '?')}/10")

        except Exception as e:
            st.error(f"Erreur : {e}")