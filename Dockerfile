# Use a base image with Java support
FROM openjdk:17

# Set working directory
WORKDIR /app

# Download and extract JDT Language Server
RUN apt-get update && apt-get install -y wget \
    && wget -O jdt-language-server.tar.gz http://download.eclipse.org/jdtls/milestones/1.23.0/jdt-language-server-1.23.0.tar.gz \
    && mkdir jdt-language-server \
    && tar -xvzf jdt-language-server.tar.gz -C jdt-language-server --strip-components=1 \
    && rm jdt-language-server.tar.gz

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port for LSP
EXPOSE 5007

# Start the Java Language Server
CMD ["/app/start.sh"]
