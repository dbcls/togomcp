IMAGE=${1:-"localhost/togo-mcp:dev"}
PORT=${2:-"8001"}

echo "Starting container with image: ${IMAGE} and port: ${PORT}"
echo "NCBI_API_KEY: ${NCBI_API_KEY}"

docker container run --rm -d -p ${PORT}:8000 \
    -e NCBI_API_KEY=${NCBI_API_KEY} \
    ${IMAGE} 