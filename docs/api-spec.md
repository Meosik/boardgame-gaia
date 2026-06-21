# API Spec

## Auth

```http
POST /api/auth/signup
POST /api/auth/login
```

## Room

```http
POST /api/rooms
GET /api/rooms
GET /api/rooms/{roomId}
POST /api/rooms/{roomId}/start
```

## Game

```http
GET /api/games/{gameId}
POST /api/games/{gameId}/actions
GET /api/games/{gameId}/events
```
