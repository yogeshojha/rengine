FROM node:22-slim AS build

WORKDIR /app

COPY VERSION ./VERSION

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/scripts/fetch-tech-icons.mjs ./scripts/

RUN node scripts/fetch-tech-icons.mjs

COPY frontend/. .

RUN NODE_OPTIONS=--max-old-space-size=4096 npm run build && npm prune --omit=dev


##################################################################
# Production: the adapter-node build and its runtime deps alone
##################################################################

FROM node:22-slim AS production

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json

USER node

EXPOSE 3000

CMD ["node", "build"]
