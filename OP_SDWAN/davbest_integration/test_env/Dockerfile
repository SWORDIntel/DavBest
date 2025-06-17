FROM ubuntu:22.04

# Install any dependencies needed by the sensor at runtime, if any (OpenSSL usually comes with base images)
# RUN apt-get update && apt-get install -y libssl3 # libssl3 is typical for Ubuntu 22.04

# Copy the sensor library (assuming it's copied into the build context)
COPY davbest_sensor.so /opt/sensor/davbest_sensor.so

# Set LD_PRELOAD to load our sensor
ENV LD_PRELOAD=/opt/sensor/davbest_sensor.so

# Define a user to run as (optional, default is root)
# USER appuser

# Command to run when the container starts.
# The sensor's constructor should run before this command.
# Using sleep to keep the container alive for a bit so logs can be generated.
CMD ["sleep", "20"]
