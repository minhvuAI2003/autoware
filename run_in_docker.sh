#!/bin/bash
#
# Docker Green Traffic Light Publisher Launcher
# Run this from the host machine to execute the publisher in the Autoware Docker container
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Green Traffic Light Publisher Launcher${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Find Autoware container
CONTAINER_ID=$(docker ps --filter "name=autoware" -q 2>/dev/null | head -1)

if [ -z "$CONTAINER_ID" ]; then
    # If not found by name, try by image
    CONTAINER_ID=$(docker ps --filter "ancestor=ghcr.io/autowarefoundation/*" -q 2>/dev/null | head -1)
fi

if [ -z "$CONTAINER_ID" ]; then
    # Try the v-autoware runtime image explicitly
    CONTAINER_ID=$(docker ps --filter "ancestor=v-autoware:runtime-cuda-humble-3.0" -q 2>/dev/null | head -1)
fi

if [ -z "$CONTAINER_ID" ]; then
    # Try to find universe-cuda or other dev containers
    CONTAINER_ID=$(docker ps --filter "name=universe-cuda" -q 2>/dev/null | head -1)
fi

if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}ERROR: No Autoware Docker container found!${NC}"
    echo ""
    echo -e "${YELLOW}Available containers:${NC}"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
    echo ""
    echo -e "${YELLOW}To start Autoware container, run:${NC}"
    echo "  cd /workspace/chinv/autoware_docker/autoware/docker"
    echo "  docker compose up -d"
    exit 1
fi

echo -e "${GREEN}Found Autoware container: ${CONTAINER_ID}${NC}"
echo ""

# Check if container is running
if ! docker ps --quiet --filter "id=$CONTAINER_ID" | grep -q "$CONTAINER_ID"; then
    echo -e "${RED}ERROR: Container is not running!${NC}"
    echo -e "${YELLOW}To start it:${NC}"
    echo "  docker start $CONTAINER_ID"
    exit 1
fi

echo -e "${BLUE}Starting Green Traffic Light Publisher...${NC}"
echo -e "${BLUE}Publishing Rate: 100Hz${NC}"
echo -e "${BLUE}Traffic Light IDs: auto-discover from lanelet2 map${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Detect ROS distro and paths to try
ROS_DISTROS=("jazzy" "humble" "iron")
AUTOWARE_INSTALL_PATHS=(
    "/opt/autoware/setup.bash"
    "/autoware/install/setup.bash"
    "/workspace/chinv/autoware_docker/autoware/install/setup.bash"
    "/root/autoware/install/setup.bash"
    "/home/autoware/autoware/install/setup.bash"
)

# Copy the Python script into the container first
SCRIPT_NAME="green_traffic_light_publisher.py"
HOST_SCRIPT_PATH="$(pwd)/$SCRIPT_NAME"
CONTAINER_SCRIPT_PATH="/tmp/$SCRIPT_NAME"

if [ ! -f "$HOST_SCRIPT_PATH" ]; then
    echo -e "${RED}ERROR: Script not found at $HOST_SCRIPT_PATH${NC}"
    exit 1
fi

echo -e "${YELLOW}Copying script to container...${NC}"
docker cp "$HOST_SCRIPT_PATH" "$CONTAINER_ID:$CONTAINER_SCRIPT_PATH"

DOCKER_EXEC_ENV=()
for var in LANELET2_MAP_PATH MAP_PATH VECTOR_MAP_PATH TRAFFIC_LIGHT_IDS; do
    if [ -n "${!var:-}" ]; then
        DOCKER_EXEC_ENV+=("-e" "$var=${!var}")
    fi
done

if [ ${#DOCKER_EXEC_ENV[@]} -eq 0 ]; then
    CONTAINER_LANELET2_PATH=$(docker exec "$CONTAINER_ID" bash -lc '
        source /opt/ros/humble/setup.bash >/dev/null 2>&1
        if [ -f /root/autoware/install/setup.bash ]; then
            source /root/autoware/install/setup.bash >/dev/null 2>&1
        elif [ -f /autoware/install/setup.bash ]; then
            source /autoware/install/setup.bash >/dev/null 2>&1
        fi
        ros2 param get /map/lanelet2_map_loader lanelet2_map_path 2>/dev/null | awk -F": " "/^String value is:/ {print \$2}"
    ')

    CONTAINER_LANELET2_PATH="${CONTAINER_LANELET2_PATH//$'\r'/}"
    CONTAINER_LANELET2_PATH="${CONTAINER_LANELET2_PATH//\'/}"

    if [ -n "$CONTAINER_LANELET2_PATH" ]; then
        DOCKER_EXEC_ENV+=("-e" "LANELET2_MAP_PATH=$CONTAINER_LANELET2_PATH")
        echo -e "${GREEN}Detected active Lanelet2 map: $CONTAINER_LANELET2_PATH${NC}"
    fi
fi

if [ ${#DOCKER_EXEC_ENV[@]} -eq 0 ]; then
    CONTAINER_MAP_PATH=$(docker exec "$CONTAINER_ID" bash -lc '
        for candidate in \
            /autoware_map/lanelet2_map.osm \
            /autoware_map/map/lanelet2_map.osm \
            /root/autoware_map/carla-autoware-bridge/Town10/lanelet2_map.osm \
            /home/autoware/autoware_map/carla-autoware-bridge/Town10/lanelet2_map.osm \
            /workspace/autoware_map/carla-autoware-bridge/Town10/lanelet2_map.osm \
            /root/autoware_map/lanelet2_map.osm \
            /home/autoware/autoware_map/lanelet2_map.osm \
            /workspace/autoware_map/lanelet2_map.osm; do
            if [ -f "$candidate" ]; then
                echo "$candidate"
                break
            fi
        done
    ')

    if [ -n "$CONTAINER_MAP_PATH" ]; then
        DOCKER_EXEC_ENV+=("-e" "LANELET2_MAP_PATH=$CONTAINER_MAP_PATH")
        echo -e "${GREEN}Detected Lanelet2 map: $CONTAINER_MAP_PATH${NC}"
    elif docker exec "$CONTAINER_ID" test -d /autoware_map 2>/dev/null; then
        DOCKER_EXEC_ENV+=("-e" "MAP_PATH=/autoware_map")
        echo -e "${GREEN}Detected Lanelet2 map directory: /autoware_map${NC}"
    fi
fi

# Build the command
CMD="source /opt/ros/humble/setup.bash"

# Try to source Autoware if available
for path in "${AUTOWARE_INSTALL_PATHS[@]}"; do
    if docker exec "$CONTAINER_ID" test -f "$path" 2>/dev/null; then
        CMD="$CMD && source $path"
        break
    fi
done

CMD="$CMD && python3 -c 'import autoware_perception_msgs; print(\"autoware_perception_msgs available\")'"

# Add the Python command (using the copied file in /tmp)
CMD="$CMD && python3 $CONTAINER_SCRIPT_PATH"

# Run in the container
docker exec -it "${DOCKER_EXEC_ENV[@]}" "$CONTAINER_ID" bash -c "$CMD"
