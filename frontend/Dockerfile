# NetScope Frontend Dockerfile

FROM nginx:alpine AS production

# Copy pre-built assets from dist folder
COPY dist /usr/share/nginx/html

# Create nginx configuration with API proxy to backend
RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name localhost;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset" always;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # API proxy with CORS and preflight handling
    location /api/ {
        proxy_pass http://backend/api/;
        
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Handle preflight requests
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset" always;
            add_header Content-Length 0;
            return 204;
        }
        
        # CORS headers for all responses
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset" always;
    }

    # Frontend - serve static files directly
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Create directories and set proper permissions for nginx
RUN mkdir -p /var/cache/nginx /var/run && \
    chown -R nginx:nginx /var/cache/nginx /var/run /usr/share/nginx/html && \
    mkdir -p /run && \
    chown -R nginx:nginx /run

USER nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:80/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
