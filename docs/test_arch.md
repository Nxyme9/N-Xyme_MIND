# REST API Architecture Specification

## 1. Overview

This document defines a production-ready REST API architecture with authentication, rate limiting, and comprehensive error handling.

---

## 2. API Design Principles

| Principle | Implementation |
|-----------|----------------|
| Resource-oriented | Use nouns, not verbs (`/users`, `/orders`) |
| RESTful constraints | Stateless, client-server, cacheable |
| Versioning | URL-based: `/api/v1/` |
| Content negotiation | JSON default, support XML via `Accept` header |
| Pagination | `limit`, `offset` query params |

### Endpoint Patterns
```
GET    /api/v1/{resource}         # List
POST   /api/v1/{resource}         # Create
GET    /api/v1/{resource}/{id}    # Retrieve
PUT    /api/v1/{resource}/{id}    # Update (full)
PATCH  /api/v1/{resource}/{id}    # Update (partial)
DELETE /api/v1/{resource}/{id}    # Delete
```

---

## 3. Authentication

### 3.1 JWT (JSON Web Tokens)
- **Algorithm**: RS256 (asymmetric) or HS256 (symmetric)
- **Payload claims**: `sub`, `exp`, `iat`, `roles`, `scopes`
- **Storage**: HttpOnly cookies or Authorization header
- **Refresh**: `/auth/refresh` endpoint with refresh token

```
Authorization: Bearer <jwt_token>
```

### 3.2 API Keys
- For server-to-server communication
- Header: `X-API-Key: {key}`
- Scoped by permissions
- Rate limit tied to key

### 3.3 OAuth 2.0
- Authorization Code flow for web apps
- Client Credentials for machine-to-machine
- Scope-based permissions

---

## 4. Rate Limiting

### 4.1 Strategy: Token Bucket
| Tier | Requests/min | Burst | Use Case |
|------|-------------|-------|----------|
| Free | 60 | 10 | Development |
| Basic | 300 | 50 | Personal use |
| Pro | 1200 | 200 | Production |
| Enterprise | Unlimited | Custom | SLA customers |

### 4.2 Implementation
- **Algorithm**: Sliding window counter per user/IP
- **Headers**:
  - `X-RateLimit-Limit`: Max requests allowed
  - `X-RateLimit-Remaining`: Requests left
  - `X-RateLimit-Reset`: Unix timestamp when limit resets
- **429 Response**: `Retry-After` header with seconds to wait

### 4.3 Configuration
```yaml
rate_limit:
  enabled: true
  storage: redis
  key_prefix: "rl:"
  window_size: 60  # seconds
  burst_factor: 1.5
```

---

## 5. Error Handling

### 5.1 HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, validation failed |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Auth valid, no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate, state conflict |
| 422 | Unprocessable | Validation errors on entity |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server-side failure |
| 503 | Service Unavailable | Maintenance, overload |

### 5.2 Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### 5.3 Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request body |
| `VALIDATION_ERROR` | 422 | Field validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server failure |
| `SERVICE_UNAVAILABLE` | 503 | Maintenance/overload |

---

## 6. Request/Response Formats

### 6.1 Request Headers
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
X-Request-ID: <uuid>
```

### 6.2 Response Envelope
```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-04-09T12:00:00Z",
    "version": "1.0"
  }
}
```

### 6.3 List Response
```json
{
  "data": [
    { "id": "1", "name": "Item 1" },
    { "id": "2", "name": "Item 2" }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 150,
    "has_more": true
  },
  "meta": { "request_id": "req_abc123" }
}
```

---

## 7. Security Considerations

| Measure | Implementation |
|---------|----------------|
| HTTPS | TLS 1.2+ enforced |
| CORS | Whitelist origins, credentials allowed |
| Input validation | Schema-based, sanitize inputs |
| SQL injection | Parameterized queries |
| XSS | Output encoding, Content-Security-Policy |
| CSRF | SameSite cookies, CSRF tokens |
| DDoS | Rate limiting, CDN, load balancer |

---

## 8. Logging & Monitoring

| Event | Log Level |
|-------|------------|
| Request received | INFO |
| Auth failure | WARN |
| Rate limit exceeded | INFO |
| Validation error | WARN |
| 5xx errors | ERROR |
| Security events | ALERT |

---

## 9. Summary

This architecture provides:
- **Authentication**: JWT, API keys, OAuth 2.0 support
- **Rate Limiting**: Token bucket with tiered quotas
- **Error Handling**: Structured responses with actionable codes
- **Security**: TLS, CORS, input validation, CSRF protection
- **Observability**: Request IDs, structured logging, status codes