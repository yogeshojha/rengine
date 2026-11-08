FROM node:22.23-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS build

WORKDIR /app

COPY VERSION ./VERSION

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/scripts/fetch-tech-icons.mjs ./scripts/

RUN node scripts/fetch-tech-icons.mjs

COPY frontend/. .

RUN NODE_OPTIONS=--max-old-space-size=4096 npm run build && npm prune --omit=dev


##################################################################
# Production
##################################################################

FROM node:22.23-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS production

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json

ARG RENGINE_UID=10001
RUN groupadd --gid "$RENGINE_UID" rengine \
    && useradd --uid "$RENGINE_UID" --gid rengine --create-home --shell /usr/sbin/nologin rengine

USER rengine

EXPOSE 3000

CMD ["node", "build"]
