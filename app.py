import streamlit as st
import google.generativeai as genai
import os
import json
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Chargement des variables d'env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("api key missing ! configure google_api_key.")
    st.stop()

genai.configure(api_key=api_key)

# Initialisation de la mémoire pour éviter de relancer Gemini au clic
if "graph_data" not in st.session_state:
    st.session_state.graph_data = None
if "focused_node" not in st.session_state:
    st.session_state.focused_node = None
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = "gemini-3-flash-preview"
if "viz_mode" not in st.session_state:
    st.session_state.viz_mode = "Network Graph"
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = False



# Load demo CV by default for Dev.to challenge showcase
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = False

if st.session_state.graph_data is None and not st.session_state.demo_loaded:
    # Load demo CV automatically
    try:
        demo_path = os.path.join(os.path.dirname(__file__), "demo_cv_data.json")
        if os.path.exists(demo_path):
            with open(demo_path, 'r', encoding='utf-8') as f:
                st.session_state.graph_data = json.load(f)
                st.session_state.demo_loaded = True
                st.info("💡 **Demo Mode**: Pascal Cescato's CV loaded automatically. Upload your own to try it!")
    except Exception as e:
        pass  # Si erreur, ignorer silencieusement

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

relationshipsHIP STRATEGY - CREATE A DENSE GRAPH:

LEVEL 1 - Direct relationshipships (Person-centric):
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

LEVEL 4 - Transversal relationshipships (the magic):
- Project -> RELATED_TO -> Project (if they share technologies or concepts)
- Skill -> REQUIRED_FOR -> Role
- Concept -> SPANS -> Multiple Projects

LEVEL 5 - Technological relationshipships (CRITICAL FOR ACCURACY):
- Technology Stack relationshipships:
  * PHP -> ENABLES -> WordPress (WordPress is built with PHP)
  * WordPress -> REQUIRES -> PHP (WordPress needs PHP to run)
  * Docker -> REQUIRES -> Linux (Docker runs on Linux)
  * NGINX/Apache -> RUNS_ON -> Linux
  * PostgreSQL/MySQL -> RUNS_ON -> Linux
  * Git -> ENABLES -> Collaboration/DevOps
  
- Framework/Language relationshipships:
  * Astro/Hugo -> BUILT_WITH -> JavaScript/Go
  * Python Libraries (lxml, Pillow) -> PART_OF -> Python
  * SSG Frameworks -> ENABLES -> Web Performance
  
- Ecosystem relationshipships:
  * Astro -> ALTERNATIVE_TO -> Hugo (both are SSG)
  * PostgreSQL -> ALTERNATIVE_TO -> MySQL (both are databases)
  * NGINX -> ALTERNATIVE_TO -> Apache (both are web servers)

IMPORTANT: Add these technological relationshipships even if not explicitly stated in the CV.
They are common knowledge relationshipships that enrich the graph's accuracy.

LEVEL 6 - Bidirectional Concept-Project links (CRITICAL - MOST OFTEN FORGOTTEN):
For EVERY concept identified, create IMPLEMENTED_IN relationshipships to ALL relevant projects:
- Migration Engineering -> IMPLEMENTED_IN -> [all migration-related projects]
- SSG Ecosystem -> IMPLEMENTED_IN -> [all SSG projects: wp2md, Hugo sites, Astro migrations]
- AI Automation -> IMPLEMENTED_IN -> [all AI/LLM projects]
- Web Performance -> IMPLEMENTED_IN -> [all performance-focused projects]
- Data Engineering -> IMPLEMENTED_IN -> [all data pipeline/database projects]

IMPORTANT EXAMPLES OF BIDIRECTIONAL relationshipsHIPS (ALWAYS CREATE BOTH):
✅ wp2md -> DEMONSTRATES -> SSG Ecosystem (project shows concept)
✅ SSG Ecosystem -> IMPLEMENTED_IN -> wp2md (concept realized in project)
✅ wp2md -> DEMONSTRATES -> Migration Engineering
✅ Migration Engineering -> IMPLEMENTED_IN -> wp2md
✅ Newsletter Engine -> DEMONSTRATES -> AI Automation
✅ AI Automation -> IMPLEMENTED_IN -> Newsletter Engine
✅ WordPress to Astro -> DEMONSTRATES -> Web Performance
✅ Web Performance -> IMPLEMENTED_IN -> WordPress to Astro

ADDITIONAL VALUABLE relationshipsHIPS:
- Person -> EXPERTISE_IN -> Concept (for main domains of expertise)
- Skill -> PART_OF -> Expertise Area (e.g., LLM Integration -> PART_OF -> AI Automation)

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
5. TARGET EDGES: Aim for 60-80 relationshipships (very dense graph)
6. IDs must be unique and descriptive (e.g., "python_language", not just "python")
7. COMPLETENESS: Extract ALL mentioned skills, even if briefly mentioned. Better complete than filtered.

QUALITY CHECK - VERIFY THESE relationshipsHIPS EXIST:
- Each concept has 2+ IMPLEMENTED_IN edges to projects
- Each major project has 1-2 DEMONSTRATES edges to concepts
- Core technologies have PART_OF relationshipships to concepts
- Technologies have ENABLES relationshipships to related skills
- Person has EXPERTISE_IN relationshipships to main concept domains

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

ALLOWED relationshipsHIPS (expanded for density):
PRIMARY:
- "MASTERS" (Person -> Skill)
- "CREATED" (Person -> Project)
- "WORKED_AS" (Person -> Role)
- "AT_COMPANY" (Role -> Entity)
- "EXPERTISE_IN" (Person -> Concept) - for main domains of expertise

SECONDARY (CREATE DENSITY):
- "USES" (Project -> Skill) [Use multiple times per project]
- "DEMONSTRATES" (Project -> Concept)
- "ENABLES" (Skill -> Skill or Concept)
- "PART_OF" (Skill -> Concept)
- "RELATED_TO" (Project -> Project)
- "REQUIRED_FOR" (Skill -> Role)
- "IMPLEMENTED_IN" (Concept -> Project) [CRITICAL: Create for all concepts]

TECHNOLOGICAL (ADD THESE FOR ACCURACY):
- "REQUIRES" (Technology -> Dependency) - e.g., WordPress REQUIRES PHP
- "RUNS_ON" (Tool -> Platform) - e.g., Docker RUNS_ON Linux
- "BUILT_WITH" (Framework -> Language) - e.g., Astro BUILT_WITH JavaScript
- "ALTERNATIVE_TO" (Technology -> Technology) - e.g., Astro ALTERNATIVE_TO Hugo
- "SPANS" (Concept -> Concept) - e.g., SEO SPANS Web Performance

QUALITY CHECK:
- Minimum 60 edges for a comprehensive graph
- Each project should have 4-6 "USES" relationshipships
- Each concept should have 2+ "IMPLEMENTED_IN" relationshipships
- Each major project should have 1-2 "DEMONSTRATES" relationshipships
- Skills used in multiple projects should be highly connected
- Concepts should span multiple projects
- Add technological relationshipships (PHP-WordPress, Docker-Linux, etc.)"""

model = genai.GenerativeModel('models/gemini-3-flash-preview', system_instruction=SYSTEM_PROMPT)

def validate_and_enhance_graph(data):
    """Nettoie et enrichit le graphe retourné par Gemini"""
    
    # 1. Déduplication des nodes
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
    
    # 3. Inférence de relationships supplémentaires (enrichissement automatique)
    
    # 3a. Trouver les projects qui partagent des technologies
    projects = [n for n in unique_nodes if n['type'] == 'Project']
    skills = [n for n in unique_nodes if n['type'] == 'Skill']
    
    # Créer un mapping project -> skills utilisées
    project_skills = {}
    for project in projects:
        project_skills[project['id']] = set()
        for edge in valid_edges:
            if edge['from'] == project['id'] and edge['label'] == 'USES':
                project_skills[project['id']].add(edge['to'])
    
    # Ajouter des relationships RELATED_TO entre projects partageant 2+ skills
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
        
        # Si une skill est utilisée dans 2+ projects, la relier aux concepts pertinents
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
    
    # 3c. Ajouter des relationships technologiques logiques (NOUVEAU V6)
    # Créer des mappings des nodes par label (case-insensitive)
    nodes_by_label = {}
    for node in unique_nodes:
        label_lower = node['label'].lower()
        nodes_by_label[label_lower] = node
    
    # relationships technologiques à ajouter automatiquement
    tech_relationshipships = [
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
    
    for skill_a_key, skill_b_key, relationshipship in tech_relationshipships:
        # Chercher les nodes correspondants (partiel match)
        skill_a_node = None
        skill_b_node = None
        
        for label, node in nodes_by_label.items():
            if skill_a_key in label and node['type'] == 'Skill':
                skill_a_node = node
            if skill_b_key in label and (node['type'] == 'Skill' or node['type'] == 'Concept'):
                skill_b_node = node
        
        # Si les deux nodes existent, créer la relation
        if skill_a_node and skill_b_node:
            edge_key = (skill_a_node['id'], skill_b_node['id'], relationshipship)
            reverse_key = (skill_b_node['id'], skill_a_node['id'], relationshipship)
            
            if edge_key not in edge_set and reverse_key not in edge_set:
                valid_edges.append({
                    'from': skill_a_node['id'],
                    'to': skill_b_node['id'],
                    'label': relationshipship
                })
                edge_set.add(edge_key)
    
    # 4. Calcul des connexions pour ajuster l'importance
    connections = {nid: 0 for nid in seen_ids}
    for edge in valid_edges:
        connections[edge['from']] += 1
        connections[edge['to']] += 1
    
    for node in unique_nodes:
        # Boost l'importance des nodes très connectés
        base_importance = node.get('importance', 5)
        if connections[node['id']] >= 5:
            node['importance'] = min(10, base_importance + 2)
        elif connections[node['id']] >= 3:
            node['importance'] = min(10, base_importance + 1)
    
    return {'nodes': unique_nodes, 'edges': valid_edges}

def calculate_node_size(node_type, importance):
    """Calcule la taille du nœud en fonction du type et de l'importance"""
    base_sizes = {
        "Person": 55,      # Réduit de 70 à 55 (-21%)
        "Skill": 32,       # Réduit de 40 à 32 (-20%)
        "Project": 36,     # Réduit de 45 à 36 (-20%)
        "Role": 28,        # Réduit de 35 à 28 (-20%)
        "Entity": 26,      # Réduit de 33 à 26 (-21%)
        "Concept": 30      # Réduit de 37 à 30 (-19%)
    }
    base = base_sizes.get(node_type, 24)  # Réduit de 30 à 24
    # Légèrement moins d'impact de l'importance pour garder les bulles compactes
    return base + (importance * 2.0)  # Réduit de 2.5 à 2.0

def get_connected_nodes(node_id, edges):
    """Retourne tous les nodes directement connectés à un nœud donné"""
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

def create_sankey_diagram(data):
    """Crée un diagramme Sankey montrant les flux Person → Skills → Projects → Concepts"""
    
    # Définir colors par type
    color_map = {
        "Person": "rgba(255, 75, 75, 0.8)",
        "Role": "rgba(243, 156, 18, 0.8)",
        "Skill": "rgba(0, 173, 238, 0.8)",
        "Project": "rgba(46, 204, 113, 0.8)",
        "Entity": "rgba(155, 89, 182, 0.8)",
        "Concept": "rgba(149, 165, 166, 0.8)"
    }
    
    # Créer un mapping id -> index
    node_dict = {node['id']: i for i, node in enumerate(data['nodes'])}
    
    # Préparer les nodes
    node_labels = [node['label'] for node in data['nodes']]
    node_colors = [color_map.get(node['type'], "rgba(189, 195, 199, 0.8)") for node in data['nodes']]
    
    # Préparer les liens avec values basées sur l'importance
    sources = []
    targets = []
    values = []
    link_colors = []
    
    for edge in data['edges']:
        if edge['from'] in node_dict and edge['to'] in node_dict:
            sources.append(node_dict[edge['from']])
            targets.append(node_dict[edge['to']])
            
            # value basée sur l'importance du nœud cible
            target_node = data['nodes'][node_dict[edge['to']]]
            values.append(target_node.get('importance', 5))
            
            # Couleur du lien = couleur du nœud source avec transparence
            source_node = data['nodes'][node_dict[edge['from']]]
            link_colors.append(color_map.get(source_node['type'], "rgba(189, 195, 199, 0.4)").replace("0.8", "0.3"))
    
    # Créer le diagramme Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=40,  # EXTRÊME : 40px entre nodes (+33% vs V7.5)
            thickness=15,  # Très fin : 15px (-25% vs V7.5)
            line=dict(color="white", width=2),
            label=node_labels,
            color=node_colors,
            hovertemplate='%{label}<br>Importance: %{value}<extra></extra>'
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate='%{source.label} → %{target.label}<br>Importance: %{value}<extra></extra>'
        ),
        # Paramètres d'arrangement
        arrangement='snap',
        orientation='h'
    )])
    
    fig.update_layout(
        title={
            'text': "Career Flow: Skills → Projects → Expertise",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Verdana, Segoe UI, Noto Sans, sans-serif'}
        },
        font=dict(
            size=14,  # Réduit de 15 à 14 (labels moins volumineux)
            family="Verdana, Segoe UI, Noto Sans, sans-serif", 
            color="#000000"
        ),
        height=1500,  # EXTRÊME : 1500px (+25% vs V7.5)
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=80, b=10)
    )
    
    # Désactiver les effets de bordure/ombre sur les labels
    fig.update_traces(
        textfont=dict(
            family="Verdana, Segoe UI, Noto Sans, sans-serif",
            size=14,  # Cohérent avec font global
            color="#000000"
        )
    )
    
    return fig

def create_skills_matrix(data):
    """Crée une matrice heatmap Skills × Projects"""
    
    # Extraire les skills et projects
    skills = [n for n in data['nodes'] if n['type'] == 'Skill']
    projects = [n for n in data['nodes'] if n['type'] == 'Project']
    
    if not skills or not projects:
        return None
    
    # Créer la matrice
    matrix = []
    skill_labels = []
    project_labels = []
    
    for skill in skills:
        row = []
        skill_labels.append(skill['label'])
        
        for project in projects:
            # Chercher si le projet utilise cette skill
            uses_skill = any(
                e['from'] == project['id'] and e['to'] == skill['id'] and e['label'] == 'USES'
                for e in data['edges']
            )
            
            if uses_skill:
                # value = importance de la skill
                row.append(skill.get('importance', 5))
            else:
                row.append(0)
        
        matrix.append(row)
    
    project_labels = [p['label'] for p in projects]
    
    # Créer le DataFrame
    df = pd.DataFrame(matrix, index=skill_labels, columns=project_labels)
    
    # Créer la heatmap
    fig = go.Figure(data=go.Heatmap(
        z=df.values,
        x=df.columns,
        y=df.index,
        colorscale=[
            [0, 'rgba(240, 240, 240, 0.3)'],      # Pas utilisé (gris très clair)
            [0.3, 'rgba(135, 206, 235, 0.5)'],    # Faible importance (bleu clair)
            [0.6, 'rgba(0, 173, 238, 0.7)'],      # Moyenne importance (bleu)
            [1, 'rgba(0, 123, 167, 0.9)']         # Haute importance (bleu foncé)
        ],
        text=df.values,
        texttemplate='%{text}',
        textfont={"size": 10},
        hovertemplate='<b>%{y}</b><br>Project: %{x}<br>Importance: %{z}<extra></extra>',
        showscale=True,
        colorbar=dict(
            title="Importance",
            titleside="right",
            tickmode="linear",
            tick0=0,
            dtick=2
        )
    ))
    
    fig.update_layout(
        title={
            'text': "Skills × Projects Matrix",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis=dict(
            title="Projects",
            tickangle=-45,
            side='top'
        ),
        yaxis=dict(
            title="Skills",
            autorange='reversed'
        ),
        font=dict(size=11, family="Arial"),
        height=600 + len(skills) * 25,  # Hauteur dynamique
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Configuration de la page
st.set_page_config(
    page_title="AI Knowledge Graph CV Builder",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 AI Knowledge Graph CV Builder")
st.markdown("*Transform your resume into an interactive knowledge graph powered by AI*")

# Hero message - philosophical positioning
st.markdown("""
<div style='text-align: center; padding: 15px 0 25px 0; max-width: 800px; margin: 0 auto;'>
    <p style='color: #666; font-size: 1.1em; line-height: 1.6; font-weight: 300;'>
        Professional journeys aren't timelines.<br>
        They're <strong>knowledge graphs</strong>.
    </p>
</div>
""", unsafe_allow_html=True)



# Quick Start instructions

# Safety: ensure uploaded_file is defined before first use to avoid NameError
uploaded_file = None

# Prepare a safe data object for the sidebar (may be empty when no graph yet)
sidebar_data = st.session_state.graph_data if st.session_state.graph_data is not None else { 'nodes': [], 'edges': [] }

# Sidebar: render independently so the uploader can appear even when no graph is loaded
with st.sidebar:
    # Conditional File Uploader
    uploaded_file = None
    if st.session_state.show_uploader:
        uploaded_file = st.file_uploader(
            "Upload Your CV (PDF)", 
            type=['pdf'],
            help="The file will be analyzed by Gemini to extract skills, projects and relationships"
        )
        if st.button("❌ Cancel Upload", use_container_width=True):
            st.session_state.show_uploader = False
            st.rerun()
    elif st.session_state.graph_data is not None and st.session_state.demo_loaded:
        # Only show the trigger button if we are in demo mode or just starting
        if st.button("🚀 Upload Your Own CV", use_container_width=True):
            st.session_state.graph_data = None
            st.session_state.show_uploader = True
            st.rerun()
    elif st.session_state.graph_data is None and not st.session_state.demo_loaded and not st.session_state.show_uploader:
        if st.button("🚀 Upload Your Own CV", use_container_width=True):
            st.session_state.show_uploader = True
            st.session_state.graph_data = None
            st.rerun()
    
    st.divider()
    st.header("🎨 visualization")
    
    # Sélecteur de mode de visualisation (NOUVEAU V7)
    viz_mode = st.radio(
        "display mode",
        options=["Network Graph", "Flow Diagram", "Skills Matrix"],
        key="viz_mode",  # ← FIX: Lie directement à st.session_state.viz_mode
        help="choose how to visualize your skills graph"
    )
    
    # Reset focus when changing views (track previous mode)
    if "prev_viz_mode" not in st.session_state:
        st.session_state.prev_viz_mode = viz_mode
    
    if viz_mode != st.session_state.prev_viz_mode:
        st.session_state.focused_node = None
        st.session_state.prev_viz_mode = viz_mode
    
    # Description des modes
    if viz_mode == "Network Graph":
        st.caption("🕸️ **interactive exploration**: Click nodes to explore connections")
    elif viz_mode == "Flow Diagram":
        st.caption("🌊 **flow view** : follow your skills journey to your projects")
    else:
        st.caption("📊 **matrix view** : quick overview of which projects use which skills")
    
    st.divider()
    
    st.header("🔍 filters")
    
    all_types = sorted(list(set(n['type'] for n in sidebar_data['nodes'])))
    selected_types = st.multiselect(
        "categories:", 
        all_types, 
        default=all_types,
        help="filter nodes by category"
    )
    
    st.divider()
    
    # Sélection du modèle (nouveauté V6)
    st.subheader("🤖 ai model")
    gemini_model = st.selectbox(
        "gemini model",
        options=["gemini-3-flash-preview", "gemini-3-pro-preview"],
        index=0 if st.session_state.gemini_model == "gemini-3-flash-preview" else 1,
        help="Flash: rapide, Pro: plus précis et inférences avancées"
    )
    
    # Mettre à jour le modèle si changé
    if gemini_model != st.session_state.gemini_model:
        st.session_state.gemini_model = gemini_model
        st.session_state.graph_data = None  # Reset pour forcer nouvelle analyse
        st.info("💡 Modèle changé. Uploadez à nouveau votre CV pour réanalyser.")
    
    st.caption("💡 Pro recommandé pour graphes plus précis (relationships technologiques)")
    
    st.divider()
    
    # Contrôles d'espacement (forces ULTRA renforcées pour éviter chevauchement labels)
    spacing_configs = {
        "Compact": {"gravity": -20000, "spring": 350},     # Augmenté encore
        "Normal": {"gravity": -40000, "spring": 500},      # Augmenté encore
        "Large": {"gravity": -70000, "spring": 700},       # Augmenté encore
        "Extra Large": {"gravity": -110000, "spring": 950},   # Augmenté encore
        "Ultra Wide": {"gravity": -160000, "spring": 1300},   # Augmenté encore
        "Mega Wide": {"gravity": -250000, "spring": 1800}     # EXTRÊME pour aucun chevauchement
    }
    
    with st.expander("⚙️ node spacing", expanded=False):
        spacing_level = st.select_slider(
            "spacing level",
            options=["Compact", "Normal", "Large", "Extra Large", "Ultra Wide", "Mega Wide"],
            value="Ultra Wide",  # Défaut augmenté à Ultra Wide
            help="adjust space between nodes to avoid overlaps"
        )
        
        show_edge_labels = st.checkbox(
            "show relationshipship labels", 
            value=False,
            help="hiding labels can improve readability"
        )
        
        st.caption(f"💡 for very dense graphs (30+ nodes), use 'Ultra Wide' ou 'Mega Wide'")
    
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
        focused_info = next((n for n in sidebar_data['nodes'] if n['id'] == st.session_state.focused_node), None)
        if focused_info:
            st.info(f"🎯 Focus: **{focused_info['label']}**")
            if st.button("🔄 reset focus", use_container_width=True):
                st.session_state.focused_node = None
                st.rerun()
            st.divider()
    
    # Statistiques
    st.subheader("📊 statistics")
    filtered_nodes_data = [n for n in sidebar_data['nodes'] if n['type'] in selected_types]
    filtered_node_ids = [n['id'] for n in filtered_nodes_data]
    filtered_edges_data = [
        e for e in sidebar_data['edges'] 
        if e['from'] in filtered_node_ids and e['to'] in filtered_node_ids
    ]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("nodes", len(filtered_nodes_data))
    with col2:
        st.metric("relationships", len(filtered_edges_data))
    
    # density du graphe (relationships par nœud)
    if len(filtered_nodes_data) > 0:
        density = len(filtered_edges_data) / len(filtered_nodes_data)
        st.metric(
            "density", 
            f"{density:.1f}",
            help="Nombre moyen de relationships par nœud. a dense graph has > 1.5"
        )
        
        # Indicateur visuel de qualité
        if density >= 2.0:
            st.success("🌟 highly interconnected graph")
        elif density >= 1.5:
            st.info("✅ good interconnection")
        else:
            st.warning("⚠️ sparsely connected graph")
    
    st.divider()
    
    # Debug info (si activé)
    if debug_mode:
        st.subheader("🔍 debug info")
        
        with st.expander("📊 statistics Détaillées", expanded=True):
            st.write(f"**nodes totaux extraits** : {len(sidebar_data['nodes'])}")
            st.write(f"**relationships totales extraites** : {len(sidebar_data['edges'])}")
            
            # distribution by type
            node_types = {}
            for node in sidebar_data['nodes']:
                node_type = node['type']
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            st.write("**distribution by type** :")
            for node_type, count in sorted(node_types.items()):
                st.write(f"  - {node_type}: {count}")
        
        with st.expander("📋 Liste Complète des nodes", expanded=False):
            for node in sorted(sidebar_data['nodes'], key=lambda x: x.get('importance', 0), reverse=True):
                st.write(f"**{node['label']}** ({node['type']}) - Importance: {node.get('importance', '?')}/10")
                st.write(f"  ID: `{node['id']}`")
                # Compter les connexions
                connections = sum(1 for e in sidebar_data['edges'] if e['from'] == node['id'] or e['to'] == node['id'])
                st.write(f"  Connexions: {connections}")
                st.caption("")  # Espacement
        
        with st.expander("🔗 Liste Complète des relationships", expanded=False):
            for edge in sidebar_data['edges']:
                from_node = next((n for n in sidebar_data['nodes'] if n['id'] == edge['from']), None)
                to_node = next((n for n in sidebar_data['nodes'] if n['id'] == edge['to']), None)
                if from_node and to_node:
                    st.write(f"{from_node['label']} **{edge.get('label', '→')}** {to_node['label']}")
        
        with st.expander("💻 JSON Brut", expanded=False):
            st.json(sidebar_data)
        
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
            n for n in sidebar_data['nodes'] 
            if search_query.lower() in n['label'].lower()
        ]
        
        if matching_nodes:
            st.success(f"✅ {len(matching_nodes)} nœud(s) trouvé(s)")
            
            for node in matching_nodes:
                # Badge avec type et importance
                badge = f"{node['type']} • {node.get('importance', '?')}/10"
                connections_count = sum(1 for e in sidebar_data['edges'] if e['from'] == node['id'] or e['to'] == node['id'])
                
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
                st.info("💡 click 📍 to activate focus")
        else:
            st.warning("❌ no matching nodes")
    else:
        st.caption("💡 type a name to search un nœud spécifique")
    
    st.divider()
    
    st.divider()
    
    # Légende des couleurs
    st.subheader("🎨 legend")
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
        count = sum(1 for n in sidebar_data['nodes'] if n['type'] == node_type)
        st.markdown(
            f'<span style="color:{color}; font-size:20px;">●</span> **{node_type}** ({count})',
            unsafe_allow_html=True
        )
    
    st.divider()
    
    # Container pour les détails au clic
    details_container = st.empty()

# Show main app block either when we have graph data, when a file was uploaded,
# or when the uploader was explicitly requested by the user (show_uploader).
if uploaded_file or st.session_state.graph_data is not None or st.session_state.show_uploader:
    # --- PHASE D'ANALYSE (Seulement si pas déjà en mémoire) ---
    if uploaded_file and st.session_state.graph_data is None:

        with st.spinner("🔍 Gemini analysis in progress..."):
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
- Create 60-80 edges minimum for a richly connected graph
- For EACH project, list ALL technologies used (minimum 4-6 USES relationshipships per project)
- Extract ALL skills mentioned, even briefly (Python, PHP, JavaScript, Docker, Git, etc.)
- Connect skills that enable each other (ENABLES relationshipships)
- Link related projects (RELATED_TO relationshipships)
- Connect concepts to multiple projects (IMPLEMENTED_IN)

BIDIRECTIONAL CONCEPT-PROJECT relationshipsHIPS (CRITICAL):
For EVERY concept you identify, create IMPLEMENTED_IN relationshipships to ALL relevant projects:
- SSG Ecosystem -> IMPLEMENTED_IN -> [all SSG projects like wp2md, Hugo sites, Astro projects]
- Migration Engineering -> IMPLEMENTED_IN -> [all migration projects]
- AI Automation -> IMPLEMENTED_IN -> [all AI/LLM projects]
- Web Performance -> IMPLEMENTED_IN -> [all performance-focused projects]

IMPORTANT EXAMPLES (ALWAYS CREATE BOTH DIRECTIONS):
✅ wp2md -> DEMONSTRATES -> SSG Ecosystem
✅ SSG Ecosystem -> IMPLEMENTED_IN -> wp2md
✅ Newsletter Engine -> DEMONSTRATES -> AI Automation
✅ AI Automation -> IMPLEMENTED_IN -> Newsletter Engine

PERSON-CONCEPT EXPERTISE:
Create EXPERTISE_IN relationshipships from the person to their main domains:
- Pascal -> EXPERTISE_IN -> AI Automation
- Pascal -> EXPERTISE_IN -> Migration Engineering
- Pascal -> EXPERTISE_IN -> Web Performance

COMPLETENESS OVER BREVITY:
If the CV mentions PHP, extract it. If it mentions 15 skills, extract all 15.
Better to have complete information than filtered/curated content.

QUALITY CHECK BEFORE RETURNING:
✅ Each concept has 2+ IMPLEMENTED_IN edges to projects
✅ Each major project has 1-2 DEMONSTRATES edges to concepts
✅ Person has EXPERTISE_IN to main concept domains
✅ 60+ total relationshipships

Quality over quantity, but PRIORITIZE COMPLETENESS and DENSITY of interconnections.
Do not artificially limit yourself to "top N" items - extract everything relevant."""
                ])
                
                # Nettoyage de la réponse
                clean_json = response.text.replace("```json", "").replace("```", "").strip()
                
                # Parsing et validation
                raw_data = json.loads(clean_json)
                st.session_state.graph_data = validate_and_enhance_graph(raw_data)
                st.session_state.show_uploader = False
                
                st.success("✅ analysis completed!")
                
            except json.JSONDecodeError as e:
                st.error(f"❌ json parsing error : {e}")
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
                    "barnesHut": {
                        "gravitationalConstant": -8000,  # Force de répulsion très élevée
                        "centralGravity": 0.1,           # Faible gravité centrale
                        "springLength": 250,             # Longueur des "ressorts" entre nodes
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

            

            # --- 1. DÉFINITION DE LA CONFIGURATION (après récupération des paramètres) ---
            # Récupérer les paramètres d'espacement
            spacing_params = spacing_configs.get(spacing_level, spacing_configs["Large"])
            
            config = Config(
                width=1600,  # Réduit pour fit tous les écrans
                height=900,  # Réduit pour fit Full HD (1080p)
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
            # Déterminer les nodes et edges actifs si mode focus
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
                    # Couleur grise et taille réduite pour les nodes non connectés
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

            # --- 4. AFFICHAGE SELON LE MODE DE VISUALISATION ---
            
            if viz_mode == "Network Graph":
                # Mode graphe réseau classique
                if st.session_state.focused_node:
                    st.success("✨ focus mode active ! grayed nodes are not directly connected. click 'reset focus' to return.")
                else:
                    st.success("✨ graph ready! ! click un nœud to activate focus mode.")
                
                # Info box
                with st.expander("💡 how to use this graph?"):
                    st.markdown("""
                    - **click un nœud** to activate focus mode (met en arrière-plan tout ce qui n'est pas connecté)
                    - **reset focus** to return à la vue complète
                    - **zoom/pan** the graph with your mouse
                    - **filter** categories in the sidebar
                    - Les **nodes plus gros** are more important
                    - Les **couleurs** represent different categories
                    """)
                
                clicked_node_id = None
                
                # Center the graph using columns
                col_left, col_center, col_right = st.columns([0.5, 9, 0.5])
                with col_center:
                    clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)

                # --- 5. GESTION DU CLIC (Activation du mode focus) ---
                if clicked_node_id and clicked_node_id != st.session_state.focused_node:
                    st.session_state.focused_node = clicked_node_id
                    st.rerun()
                
                # Afficher les détails du nœud en focus
                if st.session_state.focused_node:
                    node_info = next((n for n in data['nodes'] if n['id'] == st.session_state.focused_node), None)
                    
                    if node_info:
                        # Trouver les relationships
                        incoming = [e for e in data['edges'] if e['to'] == st.session_state.focused_node]
                        outgoing = [e for e in data['edges'] if e['from'] == st.session_state.focused_node]
                        
                        with details_container.container():
                            st.markdown(f"### 📄 {node_info['label']}")
                            
                            # Badges
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**Type** : {node_info['type']}")
                            with col2:
                                st.markdown(f"**Importance** : {node_info.get('importance', '?')}/10")
                            with col3:
                                total_connections = len(incoming) + len(outgoing)
                                st.markdown(f"**Connexions** : {total_connections}")
                            
                            if incoming:
                                st.markdown("**⬅️ relationships entrantes** :")
                                for e in incoming:
                                    from_node = next((n for n in data['nodes'] if n['id'] == e['from']), None)
                                    if from_node:
                                        st.markdown(f"- {from_node['label']} **{e.get('label', '→')}** {node_info['label']}")
                            
                            if outgoing:
                                st.markdown("**➡️ relationships sortantes** :")
                                for e in outgoing:
                                    to_node = next((n for n in data['nodes'] if n['id'] == e['to']), None)
                                    if to_node:
                                        st.markdown(f"- {node_info['label']} **{e.get('label', '→')}** {to_node['label']}")
            
            elif viz_mode == "Flow Diagram":
                # Mode Sankey
                st.info("🌊 **flow diagram** : follow your skills journey to your projects et domaines d'expertise")
                
                with st.expander("💡 how to read this diagram?"):
                    st.markdown("""
                    - **the bands** represent connections between entities
                    - **the width** indicates connection importance
                    - **colors** correspond to types (Skills en bleu, Projects en vert, etc.)
                    - **hover over** elements to see details
                    - the flow generally goes from **left to right** : Skills → Projects → Concepts
                    """)
                
                # filterr les données selon les catégories sélectionnées
                filtered_data = {
                    'nodes': [n for n in data['nodes'] if n['type'] in selected_types],
                    'edges': [e for e in data['edges'] 
                             if any(n['id'] == e['from'] and n['type'] in selected_types for n in data['nodes']) and
                                any(n['id'] == e['to'] and n['type'] in selected_types for n in data['nodes'])]
                }
                
                sankey_fig = create_sankey_diagram(filtered_data)
                
                # Center the diagram using columns
                col_left, col_center, col_right = st.columns([0.5, 9, 0.5])
                with col_center:
                    st.plotly_chart(sankey_fig, use_container_width=True)
                
                # Stats rapides
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("nodes", len(filtered_data['nodes']))
                with col2:
                    st.metric("Connexions", len(filtered_data['edges']))
                with col3:
                    density = len(filtered_data['edges']) / len(filtered_data['nodes']) if len(filtered_data['nodes']) > 0 else 0
                    st.metric("density", f"{density:.1f}")
            
            elif viz_mode == "Skills Matrix":
                # Mode Matrix
                st.info("📊 **skills matrix** : quick overview of which projects use which skills")
                
                with st.expander("💡 how to read this matrix?"):
                    st.markdown("""
                    - **rows** = technical skills
                    - **columns** = projects
                    - **intense color** = skill used in project (darker = more important)
                    - **light gray** = skill not used
                    - **value** = skill importance level (0-10)
                    """)
                
                # filterr les données pour la matrix
                filtered_data = {
                    'nodes': [n for n in data['nodes'] if n['type'] in selected_types],
                    'edges': data['edges']
                }
                
                matrix_fig = create_skills_matrix(filtered_data)
                
                if matrix_fig:
                    # Center the matrix using columns
                    col_left, col_center, col_right = st.columns([0.5, 9, 0.5])
                    with col_center:
                        st.plotly_chart(matrix_fig, use_container_width=True)
                    
                    # Insights
                    skills = [n for n in filtered_data['nodes'] if n['type'] == 'Skill']
                    projects = [n for n in filtered_data['nodes'] if n['type'] == 'Project']
                    
                    # Trouver la skill la plus utilisée
                    skill_usage = {}
                    for skill in skills:
                        count = sum(1 for e in data['edges'] 
                                  if e['to'] == skill['id'] and e['label'] == 'USES')
                        skill_usage[skill['label']] = count
                    
                    if skill_usage:
                        most_used_skill = max(skill_usage.items(), key=lambda x: x[1])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.success(f"🏆 **most used skill** : {most_used_skill[0]} ({most_used_skill[1]} projects)")
                        with col2:
                            avg_skills_per_project = sum(skill_usage.values()) / len(projects) if projects else 0
                            st.info(f"📈 **average** : {avg_skills_per_project:.1f} skills per project")
                else:
                    st.warning("⚠️ not enough data to generate matrix. Assurez-vous d'avoir des Skills et Projects dans les filters.")

        except Exception as e:
            st.error(f"❌ display error : {e}")
            st.exception(e)
            
else:
    # Message d'accueil
    if not st.session_state.show_uploader:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3 style='color: #333;'>Ready to visualize your career?</h3>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Get Started: Upload Your CV", use_container_width=True):
            st.session_state.show_uploader = True
            st.rerun()
    else:
        st.info("👆 upload your cv to start analysis")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 Objective")
        st.markdown("""
        Transform your static resume into a **dynamic knowledge graph** 
        that highlights your skills, projects and their interconnections.
        """)
    
    with col2:
        st.markdown("### ⚡ Features")
        st.markdown("""
        - AI-powered automatic extraction (Gemini)
        - Interactive visualization
        - Filter by categories
        - Relationship analysis
        """)
    
    with col3:
        st.markdown("### 🚀 Use Cases")
        st.markdown("""
        - Interactive portfolio
        - Interview preparation
        - Skills gap identification
        - Professional storytelling
        """)

# Footer - Credits and links
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em; padding: 20px 0;'>
    Built with Streamlit, Gemini AI, and iterative refinement<br>
    <a href='https://github.com/pcescato/knowledge-graph-cv' target='_blank' style='color: #0066cc; text-decoration: none;'>📂 View Source</a> | 
    <a href='https://dev.to' target='_blank' style='color: #0066cc; text-decoration: none;'>📝 Read the Story</a>
</div>
""", unsafe_allow_html=True)