# Modify these volumes:
# -v "$(pwd)/sample_input":"/app/in"
# -v "$(pwd)/sample_output":"/app/out"
#
# Only modify the path on the host (before ":").
# Put input files in the mapped folder that corresponds to /app/in 
# Output files will be generated in the mapped folder that corresponds to /app/out

docker run --rm -v "$(pwd)/config.yaml":"/app/config.yaml" -v "$(pwd)/sample_input":"/app/in" -v "$(pwd)/sample_output":"/app/out" crawlingreport:latest create-report