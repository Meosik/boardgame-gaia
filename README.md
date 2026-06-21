# Gaia Project Web

Spring Boot + React 기반 턴제 보드게임 웹 프로젝트 초기 템플릿입니다.

## Stack

### Backend
- Java 17
- Spring Boot 3
- Spring Security
- Spring Data JPA
- PostgreSQL
- Redis
- SSE

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- Axios
- React Router
- Zustand

### Infra
- Docker
- Docker Compose
- Nginx

## Structure

```text
gaia-project-web/
├─ backend/
├─ frontend/
├─ infra/
├─ docs/
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

## Run

### 1. Copy environment file

```bash
cp .env.example .env
```

### 2. Start infra

```bash
docker compose up -d postgres redis
```

### 3. Run backend

```bash
cd backend
./gradlew bootRun
```

Backend:

```text
http://localhost:8080
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## MVP Development Order

```text
1. Auth
2. User
3. Room
4. Game creation
5. Game state
6. Turn action
7. Action log
8. SSE notification
9. Record
10. AI player
```

## API Draft

```text
POST /api/auth/signup
POST /api/auth/login

GET  /api/users/me

POST /api/rooms
GET  /api/rooms
GET  /api/rooms/{roomId}
POST /api/rooms/{roomId}/join
POST /api/rooms/{roomId}/leave
POST /api/rooms/{roomId}/ready
POST /api/rooms/{roomId}/start

GET  /api/games/{gameId}
POST /api/games/{gameId}/actions
GET  /api/games/{gameId}/events
```

## Note

This project is for personal study and portfolio purposes.
