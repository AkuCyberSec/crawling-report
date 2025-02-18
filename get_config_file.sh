# Modify this volume:
# -v "$(pwd)/sample_input/test":"/app/in"
#
# Only modify the path on the host (before ":").
# Output files will be generated in the mapped folder that corresponds to /app/out

docker run --rm -v "$(pwd)/sample_output":"/app/out" crawlingreport:latest get-config