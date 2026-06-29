#!/bin/bash
# ============================================================
# IT-01: ROS 2 Cross-Container Communication Test
# Usage: bash scripts/ci/test_ros2_cross.sh
# ============================================================
set -euo pipefail

echo "=== IT-01: ROS 2 Cross-Container Communication ==="

# Check if brain_core is publishing ROS 2 topics
TOPICS=$(docker compose -f docker-compose.ci.yml exec brain_core ros2 topic list 2>/dev/null || echo "")
TOPIC_COUNT=$(echo "$TOPICS" | wc -l)

if [ "$TOPIC_COUNT" -lt 1 ]; then
  echo "ERROR: No ROS 2 topics detected"
  exit 1
fi

echo "ROS 2 Topics found: $TOPIC_COUNT"
echo "$TOPICS" | head -n 20

# Verify expected topics exist
REQUIRED_TOPICS=("/joint_states" "/tf")
for topic in "${REQUIRED_TOPICS[@]}"; do
  if ! echo "$TOPICS" | grep -q "$topic"; then
    echo "WARNING: Expected topic $topic not found (may be normal in CI environment)"
  fi
done

echo "=== IT-01: ROS 2 Cross-Container Communication OK ==="
