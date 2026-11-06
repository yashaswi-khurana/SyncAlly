FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.9-alpine

COPY --from=build /app/dist /srv
COPY infra/deploy/Caddyfile /etc/caddy/Caddyfile

EXPOSE 80 443
