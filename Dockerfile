# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Copy frontend build output
COPY --from=frontend-build /frontend/dist /app/frontend/dist

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
