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

# Initialisation de la mémoire pour éviter de relancer Gemini au clic
if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

SYSTEM_PROMPT = """You are an expert Knowledge Engineer analyzing professional CVs.

EXTRACTION STRATEGY:
1. PERSON NODE: Create exactly ONE node for the candidate (use their name from CV)
2. CORE SKILLS: Extract 5-8 PRIMARY technical skills (frameworks, languages, methodologies)
3. KEY PROJECTS: Identify 3-5 FLAGSHIP projects with clear business impact
4. PROFESSIONAL ROLES: Extract 2-4 main positions/companies
5. EXPERTISE AREAS: Create 2-3 high-level concept nodes (e.g., "Web Performance", "AI Automation")

RELATIONSHIP PRIORITIES:
- Person -> MASTERS -> Core Skills
- Person -> CREATED -> Key Projects  
- Projects -> USES -> Skills
- Projects -> DEMONSTRATES -> Concepts
- Person -> WORKED_AS -> Roles -> AT_COMPANY -> Companies

CRITICAL RULES:
1. STRICT JSON OUTPUT (no markdown, no explanations)
2. IMPORTANCE SCORING:
   - Person: 10
   - Core Skills: 7-9
   - Key Projects: 6-8
   - Concepts: 5-7
   - Roles/Companies: 4-6
3. DEDUPLICATION: Use consistent IDs (lowercase, underscores, no spaces)
4. TARGET: 15-20 nodes maximum for readability
5. IDs must be unique and descriptive (e.g., "astro_framework", not just "astro")

OUTPUT SCHEMA:
{
  "nodes": [
    {"id": "pascal_cescato", "label": "Pascal Cescato", "type": "Person", "importance": 10},
    {"id": "astro_framework", "label": "Astro", "type": "Skill", "importance": 9},
    {"id": "wp2md_project", "label": "wp2md Migration Tool", "type": "Project", "importance": 8}
  ],
  "edges": [
    {"from": "pascal_cescato", "to": "astro_framework", "label": "MASTERS"},
    {"from": "pascal_cescato", "to": "wp2md_project", "label": "CREATED"},
    {"from": "wp2md_project", "to": "astro_framework", "label": "USES"}
  ]
}

ALLOWED NODE CATEGORIES:
- "Person": The candidate/author
- "Role": Job titles or positions
- "Skill": Technologies, frameworks, or methodologies
- "Project": Specific achievements or work samples
- "Entity": Companies, schools, or organizations
- "Concept": High-level domains (e.g., "Web Performance", "AI/ML", "DevOps")

ALLOWED RELATIONSHIPS:
- "MASTERS" (Person -> Skill)
- "CREATED" (Person -> Project)
- "WORKED_AS" (Person -> Role)
- "AT_COMPANY" (Role -> Entity)
- "USES" (Project -> Skill)
- "DEMONSTRATES" (Project -> Concept)
- "REQUIRES" (Role -> Skill)"""

model = genai.GenerativeModel('models/gemini-3-flash-preview', system_instruction=SYSTEM_PROMPT)

def validate_and_enhance_graph(data):
    """Nettoie et enrichit le graphe retourné par Gemini"""
    
    # 1. Déduplication des nœuds
    seen_ids = set()
    unique_nodes = []
    id_mapping = {}  # Pour remapper les IDs
    
    for node in data['nodes']:
        # Normalisation de l'ID
        original_id = node['id']
        node_id = original_id.lower().replace(' ', '_').replace('-', '_')
        
        if node_id not in seen_ids:
            node['id'] = node_id
            seen_ids.add(node_id)
            unique_nodes.append(node)
            id_mapping[original_id] = node_id
        else:
            # Si doublon, on mappe quand même l'ancien ID
            id_mapping[original_id] = node_id
    
    # 2. Validation et normalisation des edges
    valid_edges = []
    for edge in data['edges']:
        # Remapper les IDs avec normalisation
        edge_from = edge['from'].lower().replace(' ', '_').replace('-', '_')
        edge_to = edge['to'].lower().replace(' ', '_').replace('-', '_')
        
        # Utiliser le mapping si disponible
        edge_from = id_mapping.get(edge['from'], edge_from)
        edge_to = id_mapping.get(edge['to'], edge_to)
        
        if edge_from in seen_ids and edge_to in seen_ids:
            edge['from'] = edge_from
            edge['to'] = edge_to
            # Normaliser le label si manquant
            if 'label' not in edge or not edge['label']:
                edge['label'] = 'RELATES_TO'
            valid_edges.append(edge)
    
    # 3. Calcul des connexions pour ajuster l'importance
    connections = {nid: 0 for nid in seen_ids}
    for edge in valid_edges:
        connections[edge['from']] += 1
        connections[edge['to']] += 1
    
    for node in unique_nodes:
        # Boost l'importance des nœuds très connectés
        base_importance = node.get('importance', 5)
        if connections[node['id']] > 4:
            node['importance'] = min(10, base_importance + 2)
        elif connections[node['id']] > 2:
            node['importance'] = min(10, base_importance + 1)
    
    return {'nodes': unique_nodes, 'edges': valid_edges}

def calculate_node_size(node_type, importance):
    """Calcule la taille du nœud en fonction du type et de l'importance"""
    base_sizes = {
        "Person": 60,
        "Skill": 35,
        "Project": 40,
        "Role": 30,
        "Entity": 28,
        "Concept": 32
    }
    base = base_sizes.get(node_type, 25)
    return base + (importance * 2)

# Configuration de la page
st.set_page_config(
    page_title="AI Knowledge Graph CV Builder",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 AI Knowledge Graph CV Builder")
st.markdown("*Transforme ton CV en graphe de connaissances interactif avec l'IA*")

uploaded_file = st.file_uploader(
    "Dépose ton CV (PDF)", 
    type=['pdf'],
    help="Le fichier sera analysé par Gemini pour extraire les compétences, projets et relations"
)

if uploaded_file:
    # --- PHASE D'ANALYSE (Seulement si pas déjà en mémoire) ---
    if st.session_state.graph_data is None:
        with st.spinner("🔍 Analyse par Gemini en cours..."):
            file_bytes = uploaded_file.read()
            
            try:
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": file_bytes},
                    "Extract the knowledge graph focusing on the most important entities and relationships. Be selective and prioritize quality over quantity."
                ])
                
                # Nettoyage de la réponse
                clean_json = response.text.replace("```json", "").replace("```", "").strip()
                
                # Parsing et validation
                raw_data = json.loads(clean_json)
                st.session_state.graph_data = validate_and_enhance_graph(raw_data)
                
                st.success("✅ Analyse terminée !")
                
            except json.JSONDecodeError as e:
                st.error(f"❌ Erreur de parsing JSON : {e}")
                st.code(response.text)
                st.stop()
            except Exception as e:
                st.error(f"❌ Erreur lors de l'analyse : {e}")
                st.stop()

    # --- PHASE D'AFFICHAGE (Interactive) ---
    if st.session_state.graph_data:
        data = st.session_state.graph_data

        try:
            # --- 1. DÉFINITION DE LA CONFIGURATION ---
            config = Config(
                width=1400,
                height=900,
                directed=True,
                physics=True,
                nodeHighlightBehavior=True,
                highlightColor="#FFD700",
                collapsible=True,
                physicsOptions={
                    "hierarchicalRepulsion": {
                        "nodeDistance": 200,
                        "springLength": 200,
                        "springConstant": 0.05,
                    },
                    "solver": "hierarchicalRepulsion",
                    "stabilization": {
                        "enabled": True,
                        "iterations": 300,
                        "fit": True
                    }
                }
            )

            # --- 2. BARRE LATÉRALE ET FILTRAGE ---
            with st.sidebar:
                st.header("🔍 Filtres")
                
                all_types = sorted(list(set(n['type'] for n in data['nodes'])))
                selected_types = st.multiselect(
                    "Catégories :", 
                    all_types, 
                    default=all_types,
                    help="Filtre les nœuds par catégorie"
                )
                
                st.divider()
                
                # Statistiques
                st.subheader("📊 Statistiques")
                filtered_nodes_data = [n for n in data['nodes'] if n['type'] in selected_types]
                filtered_node_ids = [n['id'] for n in filtered_nodes_data]
                filtered_edges_data = [
                    e for e in data['edges'] 
                    if e['from'] in filtered_node_ids and e['to'] in filtered_node_ids
                ]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Nœuds", len(filtered_nodes_data))
                with col2:
                    st.metric("Relations", len(filtered_edges_data))
                
                st.divider()
                
                # Légende des couleurs
                st.subheader("🎨 Légende")
                color_map = {
                    "Person": "#FF4B4B",   # Rouge
                    "Role": "#F39C12",     # Orange
                    "Skill": "#00ADEE",    # Bleu
                    "Project": "#2ECC71",  # Vert
                    "Entity": "#9B59B6",   # Violet
                    "Concept": "#95A5A6"   # Gris
                }
                
                for node_type in all_types:
                    color = color_map.get(node_type, "#BDC3C7")
                    count = sum(1 for n in data['nodes'] if n['type'] == node_type)
                    st.markdown(
                        f'<span style="color:{color}; font-size:20px;">●</span> **{node_type}** ({count})',
                        unsafe_allow_html=True
                    )
                
                st.divider()
                
                # Bouton de réinitialisation
                if st.button("🔄 Analyser un nouveau CV", use_container_width=True):
                    st.session_state.graph_data = None
                    st.rerun()
                
                st.divider()
                
                # Container pour les détails au clic
                details_container = st.empty()

            # --- 3. CRÉATION DES OBJETS GRAPH ---
            nodes = []
            for n in filtered_nodes_data:
                node_color = color_map.get(n['type'], "#BDC3C7")
                node_size = calculate_node_size(n['type'], n.get('importance', 5))
                
                nodes.append(Node(
                    id=n['id'], 
                    label=n['label'], 
                    size=node_size, 
                    color=node_color,
                    shape="dot"
                ))

            edges = [
                Edge(
                    source=e['from'], 
                    target=e['to'],
                    label=e.get('label', ''),
                    color="#95A5A6"
                ) 
                for e in filtered_edges_data
            ]

            # --- 4. AFFICHAGE DU GRAPHE ---
            st.success("✨ Graphe prêt ! Clique sur un nœud pour voir les détails.")
            
            # Info box
            with st.expander("💡 Comment utiliser ce graphe ?"):
                st.markdown("""
                - **Clique sur un nœud** pour voir ses détails et relations
                - **Zoom/déplace** le graphe avec ta souris
                - **Filtre** les catégories dans la barre latérale
                - Les **nœuds plus gros** sont plus importants dans ton profil
                - Les **couleurs** représentent les différentes catégories
                """)
            
            clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)

            # --- 5. GESTION DU CLIC (Affichage des détails) ---
            if clicked_node_id:
                node_info = next((n for n in data['nodes'] if n['id'] == clicked_node_id), None)
                
                if node_info:
                    # Trouver les relations
                    incoming = [e for e in data['edges'] if e['to'] == clicked_node_id]
                    outgoing = [e for e in data['edges'] if e['from'] == clicked_node_id]
                    
                    with details_container.container():
                        st.markdown(f"### 📄 {node_info['label']}")
                        
                        # Badges
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Type:** `{node_info['type']}`")
                        with col2:
                            importance = node_info.get('importance', 5)
                            st.markdown(f"**Importance:** `{importance}/10`")
                        with col3:
                            total_connections = len(incoming) + len(outgoing)
                            st.markdown(f"**Connexions:** `{total_connections}`")
                        
                        st.divider()
                        
                        # Relations sortantes
                        if outgoing:
                            st.markdown("**🔗 Relations sortantes:**")
                            for e in outgoing[:8]:  # Limiter à 8
                                target = next((n for n in data['nodes'] if n['id'] == e['to']), None)
                                if target:
                                    label = e.get('label', '→')
                                    st.markdown(f"  `{label}` → **{target['label']}** *({target['type']})*")
                        
                        # Relations entrantes
                        if incoming:
                            st.markdown("**🔗 Relations entrantes:**")
                            for e in incoming[:8]:  # Limiter à 8
                                source = next((n for n in data['nodes'] if n['id'] == e['from']), None)
                                if source:
                                    label = e.get('label', '←')
                                    st.markdown(f"  **{source['label']}** *({source['type']})* `{label}`")
                        
                        if not incoming and not outgoing:
                            st.info("Aucune relation trouvée pour ce nœud.")

        except Exception as e:
            st.error(f"❌ Erreur d'affichage : {e}")
            st.exception(e)
            
else:
    # Message d'accueil
    st.info("👆 Upload ton CV pour commencer l'analyse")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 Objectif")
        st.markdown("""
        Transforme ton CV statique en un **graphe de connaissances dynamique** 
        qui met en évidence tes compétences, projets et leur interconnexions.
        """)
    
    with col2:
        st.markdown("### ⚡ Fonctionnalités")
        st.markdown("""
        - Extraction automatique par IA (Gemini)
        - Visualisation interactive
        - Filtrage par catégories
        - Analyse des relations
        """)
    
    with col3:
        st.markdown("### 🚀 Cas d'usage")
        st.markdown("""
        - Portfolio interactif
        - Préparation d'entretiens
        - Identification de gaps de compétences
        - Storytelling professionnel
        """)