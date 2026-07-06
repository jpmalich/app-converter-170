# ---- Build stage: compile the CRA/craco app to static files ----
FROM node:20-bookworm-slim AS build

WORKDIR /app

# API calls are made to `${REACT_APP_BACKEND_URL}/api`. Left empty so the
# calls are same-origin relative paths (/api/...) which nginx proxies to the
# backend — this keeps the Secure;SameSite=None auth cookie first-party.
ENV REACT_APP_BACKEND_URL=""

# No yarn.lock is checked in, so resolve from package.json ranges.
COPY package.json ./
RUN yarn install --network-timeout 600000

COPY . .
RUN yarn build

# ---- Serve stage: nginx serves the build + reverse-proxies /api ----
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
