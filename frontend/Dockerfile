# Stage 1: Build stage
FROM node:20-alpine AS build-stage

WORKDIR /app

# Copy package descriptors and install dependencies
COPY package.json ./
RUN npm install

# Copy source assets and build
COPY . .
RUN npm run build

# Stage 2: Production serve stage
FROM nginx:1.25-alpine AS production-stage

# Copy Nginx server settings config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled build assets from previous stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
