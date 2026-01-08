import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict

# Bots confirmés à bloquer
BLOCKED_IPS = [
    "185.136.92.136",    # Iguane Solutions - Bot IA
    "103.197.153.253",   # Asie - Comportement suspect
    "190.44.117.142",    # Amérique du Sud - Trop de requêtes
    "103.167.135.173",   # Asie - Comportement suspect
    "119.111.248.104",   # Pakistan - Trop de requêtes
]

# Rate limiting pour les autres
if 'ip_requests' not in st.session_state:
    st.session_state.ip_requests = defaultdict(list)

def get_client_ip():
    """Récupère l'IP réelle du client via headers Cloud Run"""
    try:
        headers = st.context.headers
        # Cloud Run utilise X-Forwarded-For
        ip = headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip:
            ip = headers.get("X-Real-IP", "unknown")
        return ip
    except:
        return "unknown"

def check_access():
    """Filtre d'accès : Bloque les bots + rate limiting"""
    client_ip = get_client_ip()
    
    # 1. BLOCAGE TOTAL des bots identifiés
    if client_ip in BLOCKED_IPS:
        st.error("🚫 **Accès refusé**")
        st.info("Votre IP a été identifiée comme bot automatisé.")
        st.caption(f"IP: {client_ip}")
        st.stop()
    
    # 2. RATE LIMITING pour les autres (15 requêtes / 5 minutes)
    now = datetime.now()
    cutoff = now - timedelta(minutes=5)
    
    # Nettoie les anciennes requêtes
    st.session_state.ip_requests[client_ip] = [
        t for t in st.session_state.ip_requests[client_ip] if t > cutoff
    ]
    
    # Vérifie la limite
    if len(st.session_state.ip_requests[client_ip]) >= 15:
        st.warning("⚠️ **Trop de requêtes**")
        st.info("Limite : 15 requêtes par 5 minutes. Patientez un instant.")
        st.caption(f"IP: {client_ip}")
        st.stop()
    
    # Enregistre cette requête
    st.session_state.ip_requests[client_ip].append(now)
    
    return client_ip