# Use Python base image
FROM python:3.9-slim

# Install git and sqlite3
RUN apt-get update && apt-get install -y \
    git \
    sqlite3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/riboseqorg/Metadata /app/Metadata 

# Set working directory
WORKDIR /app/Metadata

# Add scripts directory to PATH
ENV PATH="/app/Metadata/scripts:${PATH}"

# Install Python dependencies
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    requests \
    argparse \
    biopython

# Set default command
CMD ["bash"]