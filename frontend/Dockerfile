# The published frontend image: a SvelteKit adapter-node build run as the node
# user. Dockerfile.dev is the vite dev server compose runs for development.

##################################################################
# Build
##################################################################

FROM node:22-slim AS build

WORKDIR /app

# src/lib/version.ts imports ../../VERSION
COPY VERSION ./VERSION

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/scripts/fetch-tech-icons.mjs ./scripts/

RUN node scripts/fetch-tech-icons.mjs

COPY frontend/. .

RUN npm run build


##################################################################
# Runtime: the build and the runtime dependencies, nothing else
##################################################################

FROM node:22-slim AS production

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    API_ORIGIN=http://api:8000

WORKDIR /app

# adapter-node bundles devDependencies; `dependencies` stay imports at runtime
COPY frontend/package*.json ./

RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force

COPY --from=build /app/build ./build
COPY frontend/scripts/serve.mjs ./scripts/serve.mjs

USER node

EXPOSE 3000

# the build's handler behind a server that also forwards /api to API_ORIGIN
CMD ["node", "scripts/serve.mjs"]
