FROM node:22-slim
WORKDIR /app
COPY package.json .
RUN npm install --omit=dev=false
COPY agent.ts server.ts ./
COPY docs ./docs
ENV PORT=8000
EXPOSE 8000
# Run as the unprivileged node user and give the container no secrets except the API key.
RUN chown -R node /app
USER node
CMD ["npx", "tsx", "server.ts"]
