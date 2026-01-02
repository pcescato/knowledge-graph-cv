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
if "focused_node" not in st.session_state:
    st.session_state.focused_node = None
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = "gemini-3-flash-preview"

SYSTEM_PROMPT = """You are an expert Knowledge Engineer analyzing professional CVs to create DENSE, INTERCONNECTED knowledge graphs.

EXTRACTION STRATEGY:
1. PERSON NODE: Create exactly ONE node for the candidate (use their name from CV)
2. CORE SKILLS: Extract ALL significant technical skills mentioned (10-15 skills including languages, frameworks, tools)
   - Include: Programming languages (Python, PHP, JavaScript, etc.)
   - Include: Frameworks (Astro, Hugo, Django, etc.)
   - Include: Tools (Docker, PostgreSQL, Git, etc.)
   - Include: Methodologies (RAG, SSG, CI/CD, etc.)
3. KEY PROJECTS: Identify ALL significant projects (5-8 projects)
4. PROFESSIONAL ROLES: Extract all mentioned positions/companies (3-5 roles)
5. EXPERTISE AREAS: Create 3-5 high-level concept nodes (e.g., "Web Performance", "AI Automation", "Migration Engineering")

CRITICAL: DO NOT artificially limit extraction. If a CV lists 15 skills, extract all 15. Better to have complete information than arbitrary limits.

RELATIONSHIP STRATEGY - CREATE A DENSE GRAPH:

LEVEL 1 - Direct relationships (Person-centric):
- Person -> MASTERS -> Core Skills (for main expertise)
- Person -> CREATED -> Key Projects
- Person -> WORKED_AS -> Roles
- Role -> AT_COMPANY -> Companies

LEVEL 2 - Cross-connections (Project-centric):
- Project -> USES -> Multiple Skills (list ALL technologies used in each project, minimum 3-5 per project)
- Project -> DEMONSTRATES -> Concepts (what domain expertise it shows)
- Project -> BUILT_WITH -> Specific tech stack

LEVEL 3 - Skill interconnections (create the network effect):
- Skill -> ENABLES -> Other Skill (e.g., "Python" enables "LLM Integration")
- Skill -> PART_OF -> Concept (e.g., "Astro" is part of "SSG Ecosystem")
- Concept -> IMPLEMENTED_IN -> Project

LEVEL 4 - Transversal relationships (the magic):
- Project -> RELATED_TO -> Project (if they share technologies or concepts)
- Skill -> REQUIRED_FOR -> Role
- Concept -> SPANS -> Multiple Projects

LEVEL 5 - Technological relationships (CRITICAL FOR ACCURACY):
- Technology Stack Relationships:
  * PHP -> ENABLES -> WordPress (WordPress is built with PHP)
  * WordPress -> REQUIRES -> PHP (WordPress needs PHP to run)
  * Docker -> REQUIRES -> Linux (Docker runs on Linux)
  * NGINX/Apache -> RUNS_ON -> Linux
  * PostgreSQL/MySQL -> RUNS_ON -> Linux
  * Git -> ENABLES -> Collaboration/DevOps
  
- Framework/Language Relationships:
  * Astro/Hugo -> BUILT_WITH -> JavaScript/Go
  * Python Libraries (lxml, Pillow) -> PART_OF -> Python
  * SSG Frameworks -> ENABLES -> Web Performance
  
- Ecosystem Relationships:
  * Astro -> ALTERNATIVE_TO -> Hugo (both are SSG)
  * PostgreSQL -> ALTERNATIVE_TO -> MySQL (both are databases)
  * NGINX -> ALTERNATIVE_TO -> Apache (both are web servers)

IMPORTANT: Add these technological relationships even if not explicitly stated in the CV.
They are common knowledge relationships that enrich the graph's accuracy.

CRITICAL RULES:
1. STRICT JSON OUTPUT (no markdown, no explanations)
2. IMPORTANCE SCORING:
   - Person: 10
   - Core Skills (used in 2+ projects): 8-9
   - Secondary Skills (used in 1 project): 6-7
   - Key Projects: 7-9
   - Concepts: 6-8
   - Roles/Companies: 4-6
3. DEDUPLICATION: Use consistent IDs (lowercase, underscores, no spaces)
4. TARGET: 20-30 nodes for comprehensive coverage (NOT a hard limit)
5. TARGET EDGES: Aim for 40-60 relationships (dense graph)
6. IDs must be unique and descriptive (e.g., "python_language", not just "python")
7. COMPLETENESS: Extract ALL mentioned skills, even if briefly mentioned. Better complete than filtered.

DENSE GRAPH EXAMPLE:
{
  "nodes": [
    {"id": "pascal_cescato", "label": "Pascal Cescato", "type": "Person", "importance": 10},
    {"id": "python_language", "label": "Python", "type": "Skill", "importance": 9},
    {"id": "astro_framework", "label": "Astro", "type": "Skill", "importance": 9},
    {"id": "wp2md_project", "label": "wp2md", "type": "Project", "importance": 8},
    {"id": "newsletter_engine", "label": "Newsletter Engine", "type": "Project", "importance": 8},
    {"id": "ai_automation", "label": "AI Automation", "type": "Concept", "importance": 7},
    {"id": "web_performance", "label": "Web Performance", "type": "Concept", "importance": 7}
  ],
  "edges": [
    {"from": "pascal_cescato", "to": "python_language", "label": "MASTERS"},
    {"from": "pascal_cescato", "to": "astro_framework", "label": "MASTERS"},
    {"from": "pascal_cescato", "to": "wp2md_project", "label": "CREATED"},
    {"from": "pascal_cescato", "to": "newsletter_engine", "label": "CREATED"},
    {"from": "wp2md_project", "to": "python_language", "label": "USES"},
    {"from": "wp2md_project", "to": "astro_framework", "label": "USES"},
    {"from": "newsletter_engine", "to": "python_language", "label": "USES"},
    {"from": "python_language", "to": "ai_automation", "label": "ENABLES"},
    {"from": "wp2md_project", "to": "web_performance", "label": "DEMONSTRATES"},
    {"from": "newsletter_engine", "to": "ai_automation", "label": "DEMONSTRATES"},
    {"from": "wp2md_project", "to": "newsletter_engine", "label": "RELATED_TO"}
  ]
}

ALLOWED NODE CATEGORIES:
- "Person": The candidate/author
- "Role": Job titles or positions
- "Skill": Technologies, frameworks, languages, tools
- "Project": Specific achievements or work samples
- "Entity": Companies, schools, or organizations
- "Concept": High-level domains (e.g., "Web Performance", "AI/ML", "Migration Engineering")

ALLOWED RELATIONSHIPS (expanded for density):
PRIMARY:
- "MASTERS" (Person -> Skill)
- "CREATED" (Person -> Project)
- "WORKED_AS" (Person -> Role)
- "AT_COMPANY" (Role -> Entity)

SECONDARY (CREATE DENSITY):
- "USES" (Project -> Skill) [Use multiple times per project]
- "DEMONSTRATES" (Project -> Concept)
- "ENABLES" (Skill -> Skill or Concept)
- "PART_OF" (Skill -> Concept)
- "RELATED_TO" (Project -> Project)
- "REQUIRED_FOR" (Skill -> Role)
- "IMPLEMENTED_IN" (Concept -> Project)

TECHNOLOGICAL (ADD THESE FOR ACCURACY):
- "REQUIRES" (Technology -> Dependency) - e.g., WordPress REQUIRES PHP
- "RUNS_ON" (Tool -> Platform) - e.g., Docker RUNS_ON Linux
- "BUILT_WITH" (Framework -> Language) - e.g., Astro BUILT_WITH JavaScript
- "ALTERNATIVE_TO" (Technology -> Technology) - e.g., Astro ALTERNATIVE_TO Hugo

QUALITY CHECK:
- Minimum 50 edges for a comprehensive graph
- Each project should have 4-6 "USES" relationships
- Skills used in multiple projects should be highly connected
- Concepts should span multiple projects
- Add technological relationships (PHP-WordPress, Docker-Linux, etc.)"""

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
    edge_set = set()  # Pour éviter les doublons d'edges
    
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
            
            # Éviter les doublons d'edges
            edge_key = (edge_from, edge_to, edge['label'])
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                valid_edges.append(edge)
    
    # 3. Inférence de relations supplémentaires (enrichissement automatique)
    
    # 3a. Trouver les projets qui partagent des technologies
    projects = [n for n in unique_nodes if n['type'] == 'Project']
    skills = [n for n in unique_nodes if n['type'] == 'Skill']
    
    # Créer un mapping project -> skills utilisées
    project_skills = {}
    for project in projects:
        project_skills[project['id']] = set()
        for edge in valid_edges:
            if edge['from'] == project['id'] and edge['label'] == 'USES':
                project_skills[project['id']].add(edge['to'])
    
    # Ajouter des relations RELATED_TO entre projets partageant 2+ skills
    for i, proj1 in enumerate(projects):
        for proj2 in projects[i+1:]:
            shared_skills = project_skills[proj1['id']] & project_skills[proj2['id']]
            if len(shared_skills) >= 2:
                edge_key = (proj1['id'], proj2['id'], 'RELATED_TO')
                reverse_key = (proj2['id'], proj1['id'], 'RELATED_TO')
                if edge_key not in edge_set and reverse_key not in edge_set:
                    valid_edges.append({
                        'from': proj1['id'],
                        'to': proj2['id'],
                        'label': 'RELATED_TO'
                    })
                    edge_set.add(edge_key)
    
    # 3b. Connecter les skills fréquemment utilisées aux concepts
    concepts = [n for n in unique_nodes if n['type'] == 'Concept']
    for skill in skills:
        skill_usage_count = sum(1 for e in valid_edges if e['to'] == skill['id'] and e['label'] == 'USES')
        
        # Si une skill est utilisée dans 2+ projets, la relier aux concepts pertinents
        if skill_usage_count >= 2:
            for concept in concepts:
                # Heuristique simple basée sur les mots-clés
                concept_lower = concept['label'].lower()
                skill_lower = skill['label'].lower()
                
                # Exemples de connexions logiques
                if ('ai' in concept_lower or 'automation' in concept_lower) and \
                   ('python' in skill_lower or 'llm' in skill_lower or 'gemini' in skill_lower):
                    edge_key = (skill['id'], concept['id'], 'ENABLES')
                    if edge_key not in edge_set:
                        valid_edges.append({
                            'from': skill['id'],
                            'to': concept['id'],
                            'label': 'ENABLES'
                        })
                        edge_set.add(edge_key)
                
                elif ('performance' in concept_lower or 'web' in concept_lower) and \
                     ('astro' in skill_lower or 'hugo' in skill_lower or 'ssg' in skill_lower):
                    edge_key = (skill['id'], concept['id'], 'ENABLES')
                    if edge_key not in edge_set:
                        valid_edges.append({
                            'from': skill['id'],
                            'to': concept['id'],
                            'label': 'ENABLES'
                        })
                        edge_set.add(edge_key)
    
    # 3c. Ajouter des relations technologiques logiques (NOUVEAU V6)
    # Créer des mappings des nœuds par label (case-insensitive)
    nodes_by_label = {}
    for node in unique_nodes:
        label_lower = node['label'].lower()
        nodes_by_label[label_lower] = node
    
    # Relations technologiques à ajouter automatiquement
    tech_relationships = [
        # PHP <-> WordPress
        ('php', 'wordpress', 'ENABLES'),
        ('wordpress', 'php', 'REQUIRES'),
        
        # Docker <-> Linux
        ('docker', 'linux', 'RUNS_ON'),
        
        # Web servers <-> Linux
        ('nginx', 'linux', 'RUNS_ON'),
        ('apache', 'linux', 'RUNS_ON'),
        
        # Databases <-> Linux (optionnel)
        ('postgresql', 'linux', 'RUNS_ON'),
        ('mysql', 'linux', 'RUNS_ON'),
        
        # SSG alternatives
        ('astro', 'hugo', 'ALTERNATIVE_TO'),
    ]
    
    for skill_a_key, skill_b_key, relationship in tech_relationships:
        # Chercher les nœuds correspondants (partiel match)
        skill_a_node = None
        skill_b_node = None
        
        for label, node in nodes_by_label.items():
            if skill_a_key in label and node['type'] == 'Skill':
                skill_a_node = node
            if skill_b_key in label and (node['type'] == 'Skill' or node['type'] == 'Concept'):
                skill_b_node = node
        
        # Si les deux nœuds existent, créer la relation
        if skill_a_node and skill_b_node:
            edge_key = (skill_a_node['id'], skill_b_node['id'], relationship)
            reverse_key = (skill_b_node['id'], skill_a_node['id'], relationship)
            
            if edge_key not in edge_set and reverse_key not in edge_set:
                valid_edges.append({
                    'from': skill_a_node['id'],
                    'to': skill_b_node['id'],
                    'label': relationship
                })
                edge_set.add(edge_key)
    
    # 4. Calcul des connexions pour ajuster l'importance
    connections = {nid: 0 for nid in seen_ids}
    for edge in valid_edges:
        connections[edge['from']] += 1
        connections[edge['to']] += 1
    
    for node in unique_nodes:
        # Boost l'importance des nœuds très connectés
        base_importance = node.get('importance', 5)
        if connections[node['id']] >= 5:
            node['importance'] = min(10, base_importance + 2)
        elif connections[node['id']] >= 3:
            node['importance'] = min(10, base_importance + 1)
    
    return {'nodes': unique_nodes, 'edges': valid_edges}

def calculate_node_size(node_type, importance):
    """Calcule la taille du nœud en fonction du type et de l'importance"""
    base_sizes = {
        "Person": 70,      # Augmenté de 60 à 70
        "Skill": 40,       # Augmenté de 35 à 40
        "Project": 45,     # Augmenté de 40 à 45
        "Role": 35,        # Augmenté de 30 à 35
        "Entity": 33,      # Augmenté de 28 à 33
        "Concept": 37      # Augmenté de 32 à 37
    }
    base = base_sizes.get(node_type, 30)
    # Augmenter légèrement l'impact de l'importance
    return base + (importance * 2.5)

def get_connected_nodes(node_id, edges):
    """Retourne tous les nœuds directement connectés à un nœud donné"""
    connected = set()
    for edge in edges:
        if edge['from'] == node_id:
            connected.add(edge['to'])
        if edge['to'] == node_id:
            connected.add(edge['from'])
    return connected

def get_relevant_edges(node_id, edges):
    """Retourne les edges connectés à un nœud donné"""
    relevant = []
    for edge in edges:
        if edge['from'] == node_id or edge['to'] == node_id:
            relevant.append(edge)
    return relevant

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
            
            # Utiliser le modèle sélectionné
            selected_model = st.session_state.get('gemini_model', 'gemini-3-flash-preview')
            model = genai.GenerativeModel(f'models/{selected_model}', system_instruction=SYSTEM_PROMPT)
            
            try:
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": file_bytes},
                    """Extract a COMPREHENSIVE and DENSE knowledge graph with maximum interconnections.

CRITICAL INSTRUCTIONS:
- Extract 20-30 nodes minimum (be exhaustive, not selective)
- Create 45-60 edges minimum for a richly connected graph
- For EACH project, list ALL technologies used (minimum 4-5 USES relationships per project)
- Extract ALL skills mentioned, even briefly (Python, PHP, JavaScript, Docker, Git, etc.)
- Connect skills that enable each other (ENABLES relationships)
- Link related projects (RELATED_TO relationships)
- Connect concepts to multiple projects (IMPLEMENTED_IN)

COMPLETENESS OVER BREVITY:
If the CV mentions PHP, extract it. If it mentions 15 skills, extract all 15.
Better to have complete information than filtered/curated content.

Quality over quantity, but PRIORITIZE COMPLETENESS and DENSITY of interconnections.
Do not artificially limit yourself to "top N" items - extract everything relevant."""
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
                width=1600,
                height=1000,
                directed=True,
                physics=True,
                nodeHighlightBehavior=True,
                highlightColor="#FFD700",
                collapsible=True,
                physicsOptions={
                    "barnesHut": {
                        "gravitationalConstant": -8000,  # Force de répulsion très élevée
                        "centralGravity": 0.1,           # Faible gravité centrale
                        "springLength": 250,             # Longueur des "ressorts" entre nœuds
                        "springConstant": 0.02,          # Rigidité des ressorts
                        "damping": 0.5,                  # Amortissement du mouvement
                        "avoidOverlap": 1                # Évite les chevauchements
                    },
                    "solver": "barnesHut",               # Meilleur pour les graphes denses
                    "stabilization": {
                        "enabled": True,
                        "iterations": 500,               # Plus d'itérations pour convergence
                        "updateInterval": 25,
                        "fit": True
                    },
                    "minVelocity": 0.75                  # Vitesse minimale avant arrêt
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
                
                # Sélection du modèle (nouveauté V6)
                st.subheader("🤖 Modèle IA")
                gemini_model = st.selectbox(
                    "Modèle Gemini",
                    options=["gemini-3-flash-preview", "gemini-3-pro-preview"],
                    index=0 if st.session_state.gemini_model == "gemini-3-flash-preview" else 1,
                    help="Flash: rapide, Pro: plus précis et inférences avancées"
                )
                
                # Mettre à jour le modèle si changé
                if gemini_model != st.session_state.gemini_model:
                    st.session_state.gemini_model = gemini_model
                    st.session_state.graph_data = None  # Reset pour forcer nouvelle analyse
                    st.info("💡 Modèle changé. Uploadez à nouveau votre CV pour réanalyser.")
                
                st.caption("💡 Pro recommandé pour graphes plus précis (relations technologiques)")
                
                st.divider()
                
                # Contrôles d'espacement (nouveauté)
                # Mapping vers les paramètres de physique
                spacing_configs = {
                    "Compact": {"gravity": -8000, "spring": 200},
                    "Normal": {"gravity": -15000, "spring": 280},
                    "Large": {"gravity": -20000, "spring": 350},
                    "Extra Large": {"gravity": -30000, "spring": 450},
                    "Ultra Wide": {"gravity": -40000, "spring": 550}
                }
                
                with st.expander("⚙️ Espacement des nœuds", expanded=False):
                    spacing_level = st.select_slider(
                        "Niveau d'espacement",
                        options=["Compact", "Normal", "Large", "Extra Large", "Ultra Wide"],
                        value="Extra Large",  # Défaut augmenté
                        help="Ajuste l'espace entre les nœuds pour éviter les chevauchements"
                    )
                    
                    show_edge_labels = st.checkbox(
                        "Afficher labels des relations", 
                        value=False,
                        help="Masquer les labels peut améliorer la lisibilité"
                    )
                    
                    st.caption(f"💡 Pour graphes denses, utilisez 'Extra Large' ou 'Ultra Wide'")
                
                st.divider()
                
                # Mode debug (nouveauté)
                debug_mode = st.checkbox(
                    "🔍 Mode Debug", 
                    value=False,
                    help="Affiche les données brutes extraites par Gemini"
                )
                
                st.divider()
                
                # Mode focus
                if st.session_state.focused_node:
                    focused_info = next((n for n in data['nodes'] if n['id'] == st.session_state.focused_node), None)
                    if focused_info:
                        st.info(f"🎯 Focus: **{focused_info['label']}**")
                        if st.button("🔄 Reset Focus", use_container_width=True):
                            st.session_state.focused_node = None
                            st.rerun()
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
                
                # Densité du graphe (relations par nœud)
                if len(filtered_nodes_data) > 0:
                    density = len(filtered_edges_data) / len(filtered_nodes_data)
                    st.metric(
                        "Densité", 
                        f"{density:.1f}",
                        help="Nombre moyen de relations par nœud. Un graphe dense a > 1.5"
                    )
                    
                    # Indicateur visuel de qualité
                    if density >= 2.0:
                        st.success("🌟 Graphe très interconnecté")
                    elif density >= 1.5:
                        st.info("✅ Bonne interconnexion")
                    else:
                        st.warning("⚠️ Graphe peu connecté")
                
                st.divider()
                
                # Debug info (si activé)
                if debug_mode:
                    st.subheader("🔍 Debug Info")
                    
                    with st.expander("📊 Statistiques Détaillées", expanded=True):
                        st.write(f"**Nœuds totaux extraits** : {len(data['nodes'])}")
                        st.write(f"**Relations totales extraites** : {len(data['edges'])}")
                        
                        # Répartition par type
                        node_types = {}
                        for node in data['nodes']:
                            node_type = node['type']
                            node_types[node_type] = node_types.get(node_type, 0) + 1
                        
                        st.write("**Répartition par type** :")
                        for node_type, count in sorted(node_types.items()):
                            st.write(f"  - {node_type}: {count}")
                    
                    with st.expander("📋 Liste Complète des Nœuds", expanded=False):
                        for node in sorted(data['nodes'], key=lambda x: x.get('importance', 0), reverse=True):
                            st.write(f"**{node['label']}** ({node['type']}) - Importance: {node.get('importance', '?')}/10")
                            st.write(f"  ID: `{node['id']}`")
                            # Compter les connexions
                            connections = sum(1 for e in data['edges'] if e['from'] == node['id'] or e['to'] == node['id'])
                            st.write(f"  Connexions: {connections}")
                            st.caption("")  # Espacement
                    
                    with st.expander("🔗 Liste Complète des Relations", expanded=False):
                        for edge in data['edges']:
                            from_node = next((n for n in data['nodes'] if n['id'] == edge['from']), None)
                            to_node = next((n for n in data['nodes'] if n['id'] == edge['to']), None)
                            if from_node and to_node:
                                st.write(f"{from_node['label']} **{edge.get('label', '→')}** {to_node['label']}")
                    
                    with st.expander("💻 JSON Brut", expanded=False):
                        st.json(data)
                    
                    st.divider()
                
                # Barre de recherche (nouveauté V6)
                st.subheader("🔎 Recherche de Nœud")
                search_query = st.text_input(
                    "Nom du nœud",
                    placeholder="Ex: PHP, Python, wp2md...",
                    help="Recherche case-insensitive dans les labels",
                    key="node_search"
                )
                
                if search_query:
                    matching_nodes = [
                        n for n in data['nodes'] 
                        if search_query.lower() in n['label'].lower()
                    ]
                    
                    if matching_nodes:
                        st.success(f"✅ {len(matching_nodes)} nœud(s) trouvé(s)")
                        
                        for node in matching_nodes:
                            # Badge avec type et importance
                            badge = f"{node['type']} • {node.get('importance', '?')}/10"
                            connections_count = sum(1 for e in data['edges'] if e['from'] == node['id'] or e['to'] == node['id'])
                            
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{node['label']}**")
                                st.caption(f"{badge} • {connections_count} connexions")
                            with col2:
                                if st.button("📍", key=f"focus_{node['id']}", help="Focus sur ce nœud"):
                                    st.session_state.focused_node = node['id']
                                    st.rerun()
                        
                        # Auto-focus si un seul résultat
                        if len(matching_nodes) == 1 and st.session_state.focused_node != matching_nodes[0]['id']:
                            st.info("💡 Cliquez sur 📍 pour activer le focus")
                    else:
                        st.warning("❌ Aucun nœud ne correspond")
                else:
                    st.caption("💡 Tapez un nom pour rechercher un nœud spécifique")
                
                st.divider()
                
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

            # --- 1. DÉFINITION DE LA CONFIGURATION (après récupération des paramètres) ---
            # Récupérer les paramètres d'espacement
            spacing_params = spacing_configs.get(spacing_level, spacing_configs["Large"])
            
            config = Config(
                width=2000,
                height=1400,
                directed=True,
                physics=True,
                nodeHighlightBehavior=True,
                highlightColor="#FFD700",
                collapsible=True,
                physicsOptions={
                    "barnesHut": {
                        "gravitationalConstant": spacing_params["gravity"],  # Paramètre ajustable
                        "centralGravity": 0.1,
                        "springLength": spacing_params["spring"],            # Paramètre ajustable
                        "springConstant": 0.02,
                        "damping": 0.5,
                        "avoidOverlap": 1
                    },
                    "solver": "barnesHut",
                    "stabilization": {
                        "enabled": True,
                        "iterations": 500,
                        "updateInterval": 25,
                        "fit": True
                    },
                    "minVelocity": 0.75
                }
            )

            # --- 3. CRÉATION DES OBJETS GRAPH ---
            # Déterminer les nœuds et edges actifs si mode focus
            if st.session_state.focused_node:
                connected_nodes = get_connected_nodes(st.session_state.focused_node, data['edges'])
                active_node_ids = {st.session_state.focused_node} | connected_nodes
                active_edges = get_relevant_edges(st.session_state.focused_node, data['edges'])
            else:
                active_node_ids = set(filtered_node_ids)
                active_edges = filtered_edges_data
            
            nodes = []
            for n in filtered_nodes_data:
                node_color = color_map.get(n['type'], "#BDC3C7")
                node_size = calculate_node_size(n['type'], n.get('importance', 5))
                
                # Appliquer le style atténué si pas dans le focus
                if st.session_state.focused_node and n['id'] not in active_node_ids:
                    # Couleur grise et taille réduite pour les nœuds non connectés
                    node_color = "#E0E0E0"
                    node_size = node_size * 0.6
                    opacity = 0.3
                else:
                    opacity = 1.0
                
                nodes.append(Node(
                    id=n['id'], 
                    label=n['label'], 
                    size=node_size, 
                    color=node_color,
                    shape="dot"
                ))

            edges = []
            for e in filtered_edges_data:
                # Déterminer si l'edge est active
                is_active = (not st.session_state.focused_node) or (e in active_edges)
                
                edge_color = "#95A5A6" if is_active else "#E8E8E8"
                edge_width = 2 if is_active else 1
                
                # Afficher le label seulement si demandé par l'utilisateur ET si l'edge est active
                edge_label = ''
                if show_edge_labels and is_active:
                    edge_label = e.get('label', '')
                
                edges.append(
                    Edge(
                        source=e['from'], 
                        target=e['to'],
                        label=edge_label,
                        color=edge_color
                    )
                )

            # --- 4. AFFICHAGE DU GRAPHE ---
            if st.session_state.focused_node:
                st.success("✨ Mode Focus actif ! Les nœuds grisés ne sont pas directement connectés. Clique sur 'Reset Focus' pour revenir.")
            else:
                st.success("✨ Graphe prêt ! Clique sur un nœud pour activer le mode focus.")
            
            # Info box
            with st.expander("💡 Comment utiliser ce graphe ?"):
                st.markdown("""
                - **Clique sur un nœud** pour activer le mode focus (met en arrière-plan tout ce qui n'est pas connecté)
                - **Reset Focus** pour revenir à la vue complète
                - **Zoom/déplace** le graphe avec ta souris
                - **Filtre** les catégories dans la barre latérale
                - Les **nœuds plus gros** sont plus importants dans ton profil
                - Les **couleurs** représentent les différentes catégories
                """)
            
            clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)

            # --- 5. GESTION DU CLIC (Activation du mode focus) ---
            if clicked_node_id and clicked_node_id != st.session_state.focused_node:
                st.session_state.focused_node = clicked_node_id
                st.rerun()
            # --- 5. GESTION DU CLIC (Activation du mode focus) ---
            if clicked_node_id and clicked_node_id != st.session_state.focused_node:
                st.session_state.focused_node = clicked_node_id
                st.rerun()
            
            # Afficher les détails du nœud en focus
            if st.session_state.focused_node:
                node_info = next((n for n in data['nodes'] if n['id'] == st.session_state.focused_node), None)
                
                if node_info:
                    # Trouver les relations
                    incoming = [e for e in data['edges'] if e['to'] == st.session_state.focused_node]
                    outgoing = [e for e in data['edges'] if e['from'] == st.session_state.focused_node]
                    
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