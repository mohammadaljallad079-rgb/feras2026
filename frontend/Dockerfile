FROM node:22-slim AS deps
WORKDIR /srv/frontend
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS build
WORKDIR /srv/frontend
COPY --from=deps /srv/frontend/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /srv/frontend
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
RUN useradd --create-home --uid 10001 safir
COPY --from=build --chown=safir:safir /srv/frontend ./
USER safir
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
