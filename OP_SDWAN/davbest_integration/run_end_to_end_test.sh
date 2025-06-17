#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

echo "Starting End-to-End Test for DavBest Integrity Sensor..."

# Define paths
REPO_ROOT=$(pwd) # Assuming script is run from repo root
TEST_ENV_DIR="OP_SDWAN/davbest_integration/test_env"
RESULTS_DIR="OP_SDWAN/davbest_integration/test_results"
SENSOR_LOG_FILE="$RESULTS_DIR/final_sensor_output.log"
ALERTS_FILE="$RESULTS_DIR/final_alerts.txt"
ANALYSIS_SCRIPT="OP_SDWAN/davbest_integration/davbest_sensor_analysis_rules.py"
DOCKERFILE_PATH="$TEST_ENV_DIR/Dockerfile" # Path relative to repo root
IMAGE_NAME="davbest_sensor_test_image_final"
CONTAINER_NAME="davbest_sensor_test_container_final"

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"
echo "Results will be stored in $RESULTS_DIR"

# Step 1: Build the Docker image
# (Using the Dockerfile created in Phase 2. Ensure davbest_sensor.so is in test_env for COPY)
echo "Copying davbest_sensor.so to test_env for Docker build context..."
cp OP_SDWAN/davbest_integration/davbest_sensor.so "$TEST_ENV_DIR/"

echo "Building Docker image '$IMAGE_NAME' from $DOCKERFILE_PATH..."
sudo docker build -t "$IMAGE_NAME" -f "$DOCKERFILE_PATH" "$TEST_ENV_DIR"
# The context for docker build is $TEST_ENV_DIR, so Dockerfile COPY ../davbest_sensor.so should be COPY davbest_sensor.so

echo "Docker image built successfully."

# Step 2: Run the container
echo "Running container '$CONTAINER_NAME'..."
# Mount mock_host_fs from $TEST_ENV_DIR/mock_host_fs to /host_root in container
# LD_PRELOAD is set in the Dockerfile
sudo docker run -d --name "$CONTAINER_NAME" \
    -v "$REPO_ROOT/$TEST_ENV_DIR/mock_host_fs:/host_root:rw" \
    "$IMAGE_NAME"
    # The default CMD in Dockerfile is ["sleep", "10"], changed to 20 by worker previously.
    # This should be enough for the sensor to run.

# Step 3: Wait for sensor execution
echo "Waiting 15 seconds for sensor to execute in container..."
sleep 15

# Step 4: Capture container logs
echo "Capturing logs from '$CONTAINER_NAME' to $SENSOR_LOG_FILE..."
sudo docker logs "$CONTAINER_NAME" > "$SENSOR_LOG_FILE" 2>&1

# Step 5: Stop and remove the container
echo "Stopping and removing container '$CONTAINER_NAME'..."
sudo docker stop "$CONTAINER_NAME"
sudo docker rm "$CONTAINER_NAME"

echo "Container run complete. Logs captured."

# Step 6: Run analysis script
echo "Running analysis script '$ANALYSIS_SCRIPT' on $SENSOR_LOG_FILE..."
# Ensure OP_SDWAN is in PYTHONPATH if running from repo root, or adjust script to handle imports.
# The analysis script was modified to add project root to sys.path, so this should be okay.
python3 "$ANALYSIS_SCRIPT" "$SENSOR_LOG_FILE" > "$ALERTS_FILE" 2>&1

echo "Analysis script finished. Alerts captured in $ALERTS_FILE."

# Step 7: Display results (optional)
echo "--- First 10 lines of Sensor Log ($SENSOR_LOG_FILE): ---"
head -n 10 "$SENSOR_LOG_FILE"
echo "--- End of Sensor Log Snippet ---"

echo "--- Content of Alerts File ($ALERTS_FILE): ---"
cat "$ALERTS_FILE"
echo "--- End of Alerts File ---"


echo "End-to-End Test Script finished successfully."
echo "Sensor logs are in: $SENSOR_LOG_FILE"
echo "Generated alerts are in: $ALERTS_FILE"
