FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite with host flag for Docker container network accessibility
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
