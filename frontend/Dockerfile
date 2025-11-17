FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Run development server (for local dev)
# For production, use: npm run build && npm start
CMD ["npm", "run", "dev"]

