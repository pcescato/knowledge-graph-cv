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
SYSTEM_PROMPT = """You are an expert Knowledge Engineer... (copie ici ton prompt complet)"""

model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)

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