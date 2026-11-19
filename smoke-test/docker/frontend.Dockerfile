# syntax=docker/dockerfile:1.7
# Smoke-test build of OpenCEX-frontend (Vue3/vite + the nginx that reverse-proxies everything).
# Same as the installer's frontend/Dockerfile, plus:
#  - optional BuildKit secret "ca" (only needed behind a TLS-intercepting proxy; absent on a normal VPS).
#    It is exported as NODE_EXTRA_CA_CERTS for the yarn install step only, nothing is persisted.
#  - package.json/yarn.lock copied first so the dependency layer is cached across config changes
#  - nginx:1.27-alpine pinned instead of the floating nginx:alpine; unused "ARG localconfig" dropped
# Context: the OpenCEX-frontend checkout, with src/local_config and deploy/{default,nginx}.conf
# rendered by build-frontends.sh (the installer writes the same paths).
FROM node:18 AS build
WORKDIR /app
ENV PATH=/app/node_modules/.bin:$PATH
COPY package.json yarn.lock ./
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca; fi; \
    yarn install --network-timeout 600000
COPY . .
RUN yarn build

FROM nginx:1.27-alpine
COPY deploy/default.conf /etc/nginx/conf.d/default.conf
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
CMD ["nginx", "-g", "daemon off;"]
