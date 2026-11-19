# syntax=docker/dockerfile:1.7
# Smoke-test build of OpenCEX-static (Nuxt 2 landing page, SSR on :3000).
# Same as the installer's nuxt/Dockerfile, plus:
#  - optional BuildKit secret "ca" (only needed behind a TLS-intercepting proxy; absent on a normal VPS).
#    It is exported as NODE_EXTRA_CA_CERTS for the yarn install step only, nothing is persisted
#    (no `yarn config set cafile`, so no ~/.yarnrc pointing at a missing file in the final image).
#  - package.json/yarn.lock copied first so the dependency layer is cached across config changes
# Context: the OpenCEX-static checkout, with .env rendered by build-frontends.sh (the installer
# writes the same path). Nuxt 2 loads .env itself at build and at `nuxt start`; variables passed
# with `docker run -e` take precedence over it.
FROM node:14.18.1
WORKDIR /app
COPY package.json yarn.lock ./
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca; fi; \
    yarn install --network-timeout 600000
COPY . .
RUN yarn build
RUN yarn generate
ENV HOST=0.0.0.0
EXPOSE 3000
CMD [ "yarn", "start" ]
