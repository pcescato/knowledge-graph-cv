#!/bin/bash
echo "=== Analyse des dernières 24h ==="
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=knowledge-graph-cv" \
  --limit 1000 \
  --freshness=24h \
  --format="csv(httpRequest.status,httpRequest.latency)" | \
  tail -n +2 | grep -v "^,$" | awk -F',' '{
    status=$1; latency=$2
    if (latency != "") {
      gsub(/s/, "", latency)
      total[status] += latency
      count[status]++
    }
  }
  END {
    print "\nStatus | Count | Total Time | Avg Time"
    print "-------|-------|------------|---------"
    for (s in total) {
      printf "%6s | %5d | %10.2fs | %7.3fs\n", s, count[s], total[s], total[s]/count[s]
    }
    print "\nCPU Time total:", total["101"] + total["200"] + total["304"], "secondes"
    print "Coût estimé (24h):", (total["101"] + total["200"] + total["304"]) * 0.024 / 3600, "€"
    print "Projection mois:", (total["101"] + total["200"] + total["304"]) * 0.024 / 3600 * 30, "€"
  }'
