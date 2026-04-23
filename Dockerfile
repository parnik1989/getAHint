# Existing contents of the Dockerfile

# Add the EXPOSE command
EXPOSE 8000

# Improved health check
HEALTHCHECK CMD curl --fail http://localhost:8000/ || exit 1
