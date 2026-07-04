# Development image — runs the craco/webpack dev server with hot reload.
# The compose file bind-mounts ./frontend over /app and keeps node_modules
# in an anonymous volume so host and container deps never mix.
FROM node:20-alpine

WORKDIR /app
RUN chown node:node /app
USER node

# No yarn.lock is committed; resolve fresh at build time.
COPY --chown=node:node package.json ./
RUN yarn install && yarn cache clean

COPY --chown=node:node . .

ENV WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    BROWSER=none

EXPOSE 3000
CMD ["yarn", "start"]
