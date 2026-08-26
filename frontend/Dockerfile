FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --include=dev

COPY . .

# Real production build (tsc typecheck + vite build) — Phase 8 section 59.
# The prior Dockerfile ran `npm run dev` (the Vite dev/HMR server) as the
# long-running container command, which is unminified and not meant to serve
# real traffic. `vite preview` here serves the built, minified bundle instead.
RUN npm run build

RUN chown -R node:node /app
USER node

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
