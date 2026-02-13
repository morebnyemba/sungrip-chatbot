FROM nginx:1.25-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SSL configuration
COPY ssl_custom/options-ssl-nginx.conf /etc/nginx/ssl_custom/options-ssl-nginx.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
