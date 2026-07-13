FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 3000
# API_BASE is read at container start, not baked in at build time — see docker-entrypoint.sh.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["serve", "-s", "dist", "-l", "3000"]
