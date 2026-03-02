Create production-ready scaffold for Vue + Node.js + PostgreSQL stack:

## Backend (Node.js + Express)
- Standard folder layout: `src/routes`, `src/controllers`, `src/models`, `src/middleware`, `src/config`
- Express.js REST API with proper error handling
- PostgreSQL integration using `pg` or `sequelize`/`typeorm`
- Database migrations and seed files
- Environment configuration (`.env.example`)
- Health endpoint (`/health`) with DB connection check
- Structured logging (winston or pino)
- OpenAPI/Swagger spec for API documentation
- Unit tests (Jest) and integration tests
- Input validation (joi or express-validator)
- CORS and security middleware (helmet)

## Frontend (Vue 3)
- Vue 3 with Composition API
- Vue Router for navigation
- Pinia for state management
- Axios for API calls with interceptors
- Component structure: `src/components`, `src/views`, `src/composables`, `src/stores`
- TypeScript support (optional but recommended)
- Vite build configuration
- Environment variables (`.env.example`)
- Unit tests (Vitest) and component tests
- ESLint + Prettier configuration

## Infrastructure
- Dockerfile for backend (Node.js)
- Dockerfile for frontend (nginx serving built assets)
- docker-compose.yml with PostgreSQL, backend, and frontend services
- Database initialization scripts
- README with setup instructions

## Follow architecture principles and testing policy from `.ai/policies/`