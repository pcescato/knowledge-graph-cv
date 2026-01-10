#!/bin/bash

SERVICE_NAME="knowledge-graph-cv"
REGION="europe-west1"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     SURVEILLANCE ANTI-BOT - Knowledge Graph CV            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "1️⃣  VÉRIFICATION : Bots bloqués par Caddy (403)"
echo "═══════════════════════════════════════════════════════════"

BLOCKED=$(gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=$SERVICE_NAME \
  AND httpRequest.status=403" \
  --limit=100 \
  --freshness=10m \
  --format="csv(httpRequest.remoteIp)" 2>/dev/null | \
  tail -n +2 | sort | uniq -c | sort -rn)

if [ -z "$BLOCKED" ]; then
    echo "⚠️  AUCUN bot bloqué (encore) - Attendre 10 min de plus"
else
    echo "✅ Bots bloqués (IP → Nombre de requêtes) :"
    echo "$BLOCKED"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "2️⃣  VÉRIFICATION : WebSocket actifs (101)"
echo "═══════════════════════════════════════════════════════════"

WS_COUNT=$(gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=$SERVICE_NAME \
  AND httpRequest.status=101" \
  --limit=200 \
  --freshness=10m \
  --format="csv(httpRequest.latency)" 2>/dev/null | \
  tail -n +2 | wc -l)

echo "Nombre de WebSocket sur 10 min : $WS_COUNT"

if [ "$WS_COUNT" -lt 10 ]; then
    echo "✅ Excellent ! Très peu de WebSocket"
elif [ "$WS_COUNT" -lt 50 ]; then
    echo "⚠️  Correct, mais surveiller"
else
    echo "❌ Trop de WebSocket - Problème !"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "3️⃣  VÉRIFICATION : Temps moyen WebSocket"
echo "═══════════════════════════════════════════════════════════"

gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=$SERVICE_NAME \
  AND httpRequest.status=101" \
  --limit=100 \
  --freshness=10m \
  --format="csv(httpRequest.latency)" 2>/dev/null | \
  tail -n +2 | awk -F',' '{
    gsub(/s/, "", $1)
    if ($1 > 0) {
      sum += $1
      count++
    }
  }
  END {
    if (count > 0) {
      avg = sum / count
      printf "Temps moyen : %.2f secondes (%d échantillons)\n", avg, count
      if (avg < 10) {
        print "✅ SUCCÈS - Bots tués rapidement par Caddy !"
      } else if (avg < 25) {
        print "⚠️  MOYEN - Certains bots passent encore"
      } else {
        print "❌ ÉCHEC - Les bots ne sont pas bloqués"
      }
    } else {
      print "Aucun WebSocket détecté"
      print "✅ PARFAIT - Tous les bots sont bloqués en 403 !"
    }
  }'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "4️⃣  ANALYSE DES COÛTS (dernière heure)"
echo "═══════════════════════════════════════════════════════════"

gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=$SERVICE_NAME" \
  --limit=2000 \
  --freshness=1h \
  --format="csv(httpRequest.status,httpRequest.latency)" 2>/dev/null | \
  tail -n +2 | grep -v "^,$" | awk -F',' '{
    status=$1
    gsub(/s/, "", $2)
    latency=$2
    if (latency > 0) {
      total[status] += latency
      count[status]++
    }
  }
  END {
    printf "%-8s | %6s | %10s | %10s\n", "Status", "Count", "CPU Time", "€/mois"
    print "---------|--------|------------|----------"
    
    grand_total = 0
    for (s in total) {
      cost_month = (total[s] * 0.024 / 3600) * 24 * 30
      printf "%-8s | %6d | %9.2fs | €%.2f\n", s, count[s], total[s], cost_month
      grand_total += total[s]
    }
    
    print "---------|--------|------------|----------"
    total_cost_month = (grand_total * 0.024 / 3600) * 24 * 30
    printf "%-8s | %6s | %9.2fs | €%.2f\n", "TOTAL", "", grand_total, total_cost_month
    
    print ""
    if (total_cost_month < 3) {
      print "💰 ✅ VICTOIRE ! Coût projeté : €" total_cost_month "/mois"
      print "   Hémorragie STOPPÉE !"
    } else if (total_cost_month < 8) {
      print "💰 ⚠️  Correct : €" total_cost_month "/mois"
      print "   Acceptable mais peut mieux faire"
    } else {
      print "💰 ❌ PROBLÈME : €" total_cost_month "/mois"
      print "   Encore trop cher, vérifier la config"
    }
  }'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "5️⃣  TOP 10 IPs (dernière heure)"
echo "═══════════════════════════════════════════════════════════"

gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=$SERVICE_NAME" \
  --limit=2000 \
  --freshness=1h \
  --format="csv(httpRequest.remoteIp,httpRequest.status)" 2>/dev/null | \
  tail -n +2 | awk -F',' '{
    if ($1 != "") {
      print $1, $2
    }
  }' | sort | uniq -c | sort -rn | head -10 | awk '{
    printf "%4d × %-40s (Status: %s)\n", $1, $2, $3
  }'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 RÉSUMÉ"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "✅ = Succès | ⚠️ = Surveiller | ❌ = Problème"
echo ""
echo "Prochaine vérification : Lance ce script dans 1h"
echo "  ./monitor_caddy.sh"
echo ""

