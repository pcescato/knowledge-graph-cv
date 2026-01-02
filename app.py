import streamlit as st
import google.generativeai as genai
import os
import json
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv

# Chargement des variables d'env (.env en local, Secrets sur Cloud Run)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("Clé API manquante ! Configurez GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=api_key)

# Ton prompt anglais testé dans AI Studio
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

uploaded_file = st.file_uploader("Dépose ton CV ou un article (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Analyse par Gemini en cours..."):
        # Lecture du fichier
        file_bytes = uploaded_file.read()
        
        # Envoi à Gemini
        response = model.generate_content([
            {"mime_type": "application/pdf", "data": file_bytes},
            "Extract the knowledge graph from this document."
        ])
        
        try:
            # Nettoyage de la réponse au cas où (parfois Gemini met des backticks ```json)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Affichage du graphe
            nodes = [Node(id=n['id'], label=n['label'], size=n.get('importance', 5)*5, 
                          color="#00ADEE" if n['type'] == 'Skill' else "#F39C12") 
                     for n in data['nodes']]
            edges = [Edge(source=e['from'], target=e['to'], label=e['label']) 
                     for e in data['edges']]
            
            config = Config(width=1000, height=600, directed=True, nodeHighlightBehavior=True)
            
            st.success("Graphe généré !")
            agraph(nodes=nodes, edges=edges, config=config)
            
        except Exception as e:
            st.error(f"Erreur de parsing : {e}")
            st.code(response.text)