# NetScope Docker Build

FROM python:3.12-slim as backend-base

WORKDIR /app/backend

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

FROM node:20-alpine as frontend-base

WORKDIR /app/frontend

# Install Node dependencies
COPY frontend/package*.json .
RUN npm install --production=false

# Copy frontend code
COPY frontend/ .

FROM rust:1-slim as builder-base

WORKDIR /app/desktop/src-tauri

# Install dependencies
RUN apt-get update && apt-get install -y \
    libwebkit2gtk-4.1-dev \
    build-essential \
    curl \
    ca-certificates

# Copy desktop code
COPY desktop/src-tauri/ .

FROM ubuntu:22.04 as final

WORKDIR /app

# Copy compiled binaries
COPY --from=builder-base /app/desktop/src-tauri/target/debug/netscope /usr/local/bin/

# Copy backend
COPY --from=backend-base /app/backend/ ./backend/

# Copy frontend
COPY --from=frontend-base /app/frontend/dist ./frontend/dist

EXPOSE 8000 3000

CMD ["python", "backend/app/main.py"]
