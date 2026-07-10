#!/bin/bash
# health_check.sh - Check health of containers and app for local or GCP environments

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi


# Default environment is GCP
ENV="GCP"

# Parse -e argument
while getopts "e:" opt; do
  case $opt in
    e)
      ENV="$OPTARG"
      ;;
    *)
      echo "Usage: $0 [-e local|GCP]"
      exit 1
      ;;
  esac
done

# Detect docker compose command (prefer new, fallback to old)
if command -v "docker compose" &> /dev/null; then
  DC="docker compose"
elif command -v docker-compose &> /dev/null; then
  DC="docker-compose"
else
  # This will be caught by the health check itself, but good to have a clear message
  DC="docker-compose"
fi


# Robust color handling: use colors only if output is a terminal
if [ -t 1 ]; then
  GREEN=$'\033[0;32m'
  RED=$'\033[0;31m'
  YELLOW=$'\033[1;33m'
  LIGHTBLUE=$'\033[1;34m'
  NC=$'\033[0m'
  CHECK="${GREEN}✔${NC}"
  CROSS="${RED}✘${NC}"
else
  GREEN=""
  RED=""
  YELLOW=""
  LIGHTBLUE=""
  NC=""
  CHECK="✔"
  CROSS="✘"
fi

# Test definitions (add to this array for new checks)
TEST_NAMES=()
TEST_RESULTS=()
TEST_DETAILS=()

# Helper to add a test result
do_test() {
  local name="$1"
  shift
  TEST_NAMES+=("$name")
  local output
  if output=$("$@" 2>&1); then
    TEST_RESULTS+=("$CHECK")
    TEST_DETAILS+=("")
  else
    TEST_RESULTS+=("$CROSS")
    TEST_DETAILS+=("$output")
  fi
}

# --- Define checks ---

# Local environment checks
if [ "$ENV" = "local" ]; then
  # Check docker-compose
  do_test "Docker Compose installed" command -v $DC &> /dev/null
  # Check containers are up
  do_test "nginx container running" $DC ps | grep -q 'nginx.*Up'
  do_test "frontend container running" $DC ps | grep -q 'frontend.*Up'
  do_test "api container running" $DC ps | grep -q 'api.*Up'
  do_test "db container running" $DC ps | grep -q 'db.*Up'
  # Check if database tables were created (depends on db container running)
  # We expect 5 tables: user, category, evidence, evidencecategorylink, vote
  do_test "All database tables created" [ "$($DC exec -T db mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "SHOW TABLES;" 2>/dev/null | tail -n +2 | wc -l)" -eq 5 ]
  # Check if database has users (adaptive to preserve vs fresh mode)
  USER_COUNT=$($DC exec -T db mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "SELECT COUNT(*) FROM user;" 2>/dev/null | tail -n +2)
  if [ "$USER_COUNT" -gt 0 ]; then
    # Check if test admin user exists (fresh deployment) or any users exist (preserved data)
    TEST_ADMIN_COUNT=$($DC exec -T db mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "SELECT COUNT(*) FROM user WHERE email='m@test.com';" 2>/dev/null | tail -n +2)
    if [ "$TEST_ADMIN_COUNT" -eq 1 ]; then
      do_test "Test admin user exists" true  # Fresh deployment with test data
    else
      do_test "Database has users" true      # Preserved data mode
    fi
  else
    do_test "Database has users" false       # No users found - something wrong
  fi
  # Test Flask-SQLAlchemy models can query all tables
  MODEL_TEST_RESULT=$($DC exec -T db mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "SELECT 'users:', COUNT(*) FROM user UNION ALL SELECT 'categories:', COUNT(*) FROM category UNION ALL SELECT 'evidence:', COUNT(*) FROM evidence UNION ALL SELECT 'links:', COUNT(*) FROM evidencecategorylink UNION ALL SELECT 'votes:', COUNT(*) FROM vote;" 2>/dev/null | tail -n +2 | wc -l)
  do_test "Flask models can query all tables" [ "$MODEL_TEST_RESULT" -eq 5 ]
  # Check backend health (HTTP 200) through nginx
  do_test "api health endpoint reachable" curl -sf "http://localhost:${BACKEND_PORT}/healthz"
  # Check frontend health (HTTP 200) through nginx proxy
  do_test "frontend reachable" curl -sf "http://localhost:${BACKEND_PORT}/"
  
  # Check admin routes and security endpoints
  echo -e "\n🔒 Testing Security & Admin Routes:"
  echo "-----------------------------------"
  
  # Test API security status endpoint
  do_test "API security status endpoint" curl -sf "http://localhost:${BACKEND_PORT}/api/security/status"
  
  # Test admin login endpoint (should accept POST)
  LOGIN_RESPONSE=$(curl -s -w "%{http_code}" -X POST "http://localhost:${BACKEND_PORT}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' 2>/dev/null)
  LOGIN_STATUS=$(echo "$LOGIN_RESPONSE" | tail -c 4)
  do_test "Admin login endpoint responds" [ "$LOGIN_STATUS" = "200" ]
  
  # Extract token from login response for further testing
  if [ "$LOGIN_STATUS" = "200" ]; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | head -c -4 | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$TOKEN" ]; then
      echo "  ✅ JWT token obtained successfully"
      
      # Test token verification
      do_test "JWT token verification" curl -sf "http://localhost:${BACKEND_PORT}/api/auth/verify" \
        -H "Authorization: Bearer $TOKEN"
      
      # Test admin security dashboard
      do_test "Admin security dashboard" curl -sf "http://localhost:${BACKEND_PORT}/api/admin/security" \
        -H "Authorization: Bearer $TOKEN"
    else
      echo "  ⚠️  Could not extract JWT token from login response"
    fi
  fi
  
  # Test frontend admin routes
  echo -e "\n🖥️  Testing Frontend Admin Routes:"
  echo "-----------------------------------"
  
  # Test admin overview page (should return HTML)
  OVERVIEW_RESPONSE=$(curl -s -w "%{http_code}" "http://localhost:${BACKEND_PORT}/overview" 2>/dev/null)
  OVERVIEW_STATUS=$(echo "$OVERVIEW_RESPONSE" | tail -c 4)
  do_test "Admin overview page loads" [ "$OVERVIEW_STATUS" = "200" ]
  
  # Check if overview page contains expected admin content
  if [ "$OVERVIEW_STATUS" = "200" ]; then
    OVERVIEW_CONTENT=$(echo "$OVERVIEW_RESPONSE" | head -c -4)
    if echo "$OVERVIEW_CONTENT" | grep -q "admin\|overview\|dashboard" -i; then
      echo "  ✅ Overview page contains admin content"
    else
      echo "  ⚠️  Overview page may not contain expected admin content"
    fi
  fi
  
  # Test admin login page
  do_test "Admin login page loads" curl -sf "http://localhost:${BACKEND_PORT}/admin/login"
  
  # Test main home page with security features
  HOME_RESPONSE=$(curl -s "http://localhost:${BACKEND_PORT}/" 2>/dev/null)
  if echo "$HOME_RESPONSE" | grep -q "security\|monitoring\|Town Scryer" -i; then
    echo "  ✅ Home page contains security features"
  else
    echo "  ⚠️  Home page may not contain expected security features"
  fi
else
  # GCP environment checks (stubbed for now)
  do_test "gcloud installed" command -v gcloud &> /dev/null
  # Example: check Cloud Run backend (replace URL as needed)
  # do_test "Cloud Run backend healthy" curl -sf https://<YOUR_CLOUD_RUN_BACKEND_URL>/healthz
  # do_test "Cloud Run frontend reachable" curl -sf https://<YOUR_CLOUD_RUN_FRONTEND_URL>
fi

# --- Container Logs Section ---
echo -e "\nContainer Logs (Last 5 lines each):"
echo "===================================="
echo

# Show recent logs for local environment
if [ "$ENV" = "local" ]; then
  # Define expected containers
  LOG_CONTAINERS=("db" "api" "frontend" "nginx")
  
  for container in "${LOG_CONTAINERS[@]}"; do
    echo -e "${LIGHTBLUE}--- $container logs ---${NC}"
    
    # Check if container exists and is running
    if $DC ps --format "{{.Names}}" | grep -q "^$container$" 2>/dev/null; then
      # Get last 5 lines of logs, suppress warnings
      if recent_logs=$($DC logs --tail=5 "$container" 2>/dev/null); then
        if [ -n "$recent_logs" ]; then
          echo "$recent_logs"
        else
          echo -e "${YELLOW}No recent logs available${NC}"
        fi
      else
        echo -e "${RED}Failed to retrieve logs${NC}"
      fi
    else
      echo -e "${RED}Container not found or not running${NC}"
    fi
    echo  # Add spacing between containers
  done
else
  echo "Container logs not implemented for $ENV environment yet."
  echo
fi

# --- Results Table ---
echo -e "\nHealth Check Results for $ENV environment:"
echo "-----------------------------------"
for i in "${!TEST_NAMES[@]}"; do
  printf "%s %s" "${TEST_RESULTS[$i]}" "${TEST_NAMES[$i]}"
  
  # Add frontend link if this is the frontend reachable test and it passed
  if [ "${TEST_NAMES[$i]}" = "frontend reachable" ] && [ "${TEST_RESULTS[$i]}" = "$CHECK" ]; then
    echo -e " ${LIGHTBLUE}→ http://localhost:${BACKEND_PORT}${NC}"
  else
    echo  # Just add newline for other tests
  fi
  
  if [ "${TEST_RESULTS[$i]}" = "$CROSS" ] && [ -n "${TEST_DETAILS[$i]}" ]; then
    echo -e "  Reason: ${TEST_DETAILS[$i]}"
  fi
done

# --- Container Status Section ---
echo -e "\n\nContainer Status for $ENV environment:"
echo "====================================="
echo

# Get container status for local environment
if [ "$ENV" = "local" ]; then
  # Define expected containers
  EXPECTED_CONTAINERS=("db" "api" "frontend" "nginx")
  
  # Check each container
  for container in "${EXPECTED_CONTAINERS[@]}"; do
    # Check if container exists and get its status
    if container_info=$($DC ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" | grep "$container" 2>/dev/null); then
      container_name=$(echo "$container_info" | awk '{print $1}')
      container_state=$(echo "$container_info" | awk '{print $2}')
      container_status=$(echo "$container_info" | awk '{$1=""; $2=""; print $0}' | sed 's/^ *//')
      
      if [ "$container_state" = "running" ]; then
        echo -e "$CHECK $container_name: ${GREEN}Running${NC}"
        echo -e "  Status: $container_status"
      elif [ "$container_state" = "exited" ]; then
        echo -e "$CROSS $container_name: ${RED}Stopped${NC}"
        echo -e "  Status: $container_status"
      else
        echo -e "${YELLOW}?${NC} $container_name: ${YELLOW}$container_state${NC}"
        echo -e "  Status: $container_status"
      fi
    else
      echo -e "$CROSS $container: ${RED}Not Found${NC}"
      echo -e "  Status: Container does not exist or is not managed by docker-compose"
    fi
    echo  # Add spacing between containers
  done
  
  # Show overall summary
  running_count=$($DC ps --format "{{.State}}" | grep -c "running" 2>/dev/null || echo "0")
  total_expected=${#EXPECTED_CONTAINERS[@]}
  
  echo "-----------------------------------"
  if [ "$running_count" -eq "$total_expected" ]; then
    echo -e "${GREEN}All $total_expected containers are running successfully!${NC}"
  else
    echo -e "${YELLOW}$running_count of $total_expected containers are running${NC}"
  fi
else
  echo "Container status checks not implemented for $ENV environment yet."
fi

echo -e "\nAdd more checks by editing health_check.sh!"
