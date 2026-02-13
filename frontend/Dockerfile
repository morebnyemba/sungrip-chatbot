# Stage 1: Build the React app
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json ./
COPY package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve the built app with Nginx
FROM nginx:1.25-alpine

# Remove default Nginx config that might conflict
RUN rm /etc/nginx/conf.d/default.conf

# Copy the built app's static files from the 'build' stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy our custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
