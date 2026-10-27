# Learning Path Generator - API Documentation

## Overview
RESTful API for the Learning Path Generator. All endpoints require CSRF tokens for POST/DELETE requests.

**Base URL**: `/api`
**Authentication**: Django session-based (login required for most endpoints)
**Response Format**: JSON

---

## Table of Contents
1. [Authentication](#authentication)
2. [Paths](#paths)
3. [Assessment](#assessment)
4. [Portfolio](#portfolio)
5. [Study](#study)
6. [Groups](#groups)
7. [Error Handling](#error-handling)

---

## Authentication

### Register
```
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "password": "securepassword123"
}
```

**Response** (201):
```json
{
  "user": {
    "id": 1,
    "username": "john_doe"
  }
}
```

**Validation**:
- Username: 3-150 chars, alphanumeric + . - _
- Password: minimum 8 characters

### Login
```
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "securepassword123"
}
```

**Response** (200):
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "is_superuser": false
  }
}
```

### Logout
```
POST /auth/logout
```

**Response** (200):
```json
{"ok": true}
```

### Get Current User
```
GET /auth/me
```

**Response** (200):
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "is_superuser": false
  }
}
```

---

## Paths

### Generate Path (Markdown)
```
POST /path/generate
Content-Type: application/json

{
  "goal": "Learn Python for Data Science",
  "current_level": "beginner",
  "hours_per_day": 2,
  "format_preference": "courses and hands-on projects",
  "months": 6,
  "target_date": "2024-12-31"
}
```

**Response** (200):
```json
{
  "output": "# Python for Data Science\n\n## Phase 1: Fundamentals\n...",
  "id": "path_abc123"
}
```

### Generate Structured Path
```
POST /path/structured
Content-Type: application/json

{
  "goal": "Learn Python for Data Science",
  "current_level": "beginner",
  "hours_per_day": 2,
  "format_preference": "courses and hands-on projects",
  "months": 6
}
```

**Response** (200):
```json
{
  "output": {
    "title": "Python for Data Science",
    "summary": "...",
    "total_weeks": 24,
    "phases": [
      {
        "title": "Phase 1: Fundamentals",
        "description": "...",
        "estimated_weeks": 4,
        "topics": [
          {
            "title": "Python Basics",
            "details": "...",
            "resources": [
              {
                "name": "Python Official Tutorial",
                "type": "docs",
                "note": "Official documentation",
                "verified": true
              }
            ]
          }
        ]
      }
    ]
  },
  "id": "path_abc123",
  "catalog_used": 5
}
```

### Get Path History
```
GET /paths/history
```

**Response** (200):
```json
{
  "paths": [
    {
      "id": "path_abc123",
      "goal": "Learn Python for Data Science",
      "created_at": "2024-01-15T10:30:00Z",
      "source": "quick",
      "current_level": "beginner",
      "hours_per_day": 2,
      "months": 6,
      "format": "structured",
      "version": 1,
      "content": "..."
    }
  ]
}
```

### Get Path Workspace
```
GET /paths/{path_id}/workspace
```

**Response** (200):
```json
{
  "id": "path_abc123",
  "goal": "Learn Python for Data Science",
  "format": "structured",
  "hours_per_day": 2,
  "target_date": "2024-12-31",
  "version": 1,
  "title": "Python for Data Science",
  "summary": "...",
  "total_weeks": 24,
  "phases": [
    {
      "index": 0,
      "title": "Phase 1: Fundamentals",
      "description": "...",
      "estimated_weeks": 4,
      "topics": [
        {
          "index": 0,
          "key": "t:0:0",
          "title": "Python Basics",
          "details": "...",
          "resources": [
            {
              "name": "Python Official Tutorial",
              "type": "docs",
              "note": "Official documentation",
              "verified": true
            }
          ]
        }
      ]
    }
  ],
  "done": ["t:0:0", "t:0:1"]
}
```

### Save Progress
```
POST /paths/{path_id}/progress/save
Content-Type: application/json

{
  "item_key": "t:0:0",
  "done": true
}
```

**Response** (200):
```json
{
  "ok": true,
  "done_count": 5
}
```

### Delete Path
```
DELETE /paths/{path_id}/delete
```

**Response** (200):
```json
{
  "deleted": true,
  "id": "path_abc123"
}
```

### Chat with Path
```
POST /paths/{path_id}/chat
Content-Type: application/json

{
  "message": "What's the best way to learn Python?",
  "history": [
    {
      "role": "user",
      "content": "How do I start learning Python?"
    },
    {
      "role": "assistant",
      "content": "Start with the basics..."
    }
  ]
}
```

**Response** (200):
```json
{
  "reply": "The best way is to practice regularly..."
}
```

---

## Assessment

### Placement Test - Start
```
POST /placement/adaptive/start
Content-Type: application/json

{
  "goal": "Learn Python"
}
```

**Response** (200):
```json
{
  "session_id": "sess_abc123",
  "question": {
    "id": "q1",
    "question": "What is Python?",
    "options": [
      "A programming language",
      "A snake",
      "A type of file",
      "None of the above"
    ]
  },
  "done": false
}
```

### Placement Test - Answer
```
POST /placement/adaptive/answer
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "question_id": "q1",
  "answer_index": 0
}
```

**Response** (200):
```json
{
  "done": false,
  "question": {
    "id": "q2",
    "question": "What is a variable?",
    "options": [...]
  }
}
```

**Final Response** (200):
```json
{
  "done": true,
  "summary": {
    "goal": "Learn Python",
    "level": "intermediate",
    "confidence": 0.85,
    "questions_asked": 8,
    "correct": 6
  }
}
```

### Phase Test - Start
```
POST /paths/{path_id}/phases/{phase_idx}/test
Content-Type: application/json

{
  "count": 5,
  "avoid": []
}
```

**Response** (200):
```json
{
  "quiz_id": "quiz_abc123",
  "questions": [
    {
      "id": "q1",
      "question": "What is a list in Python?",
      "options": [...]
    }
  ],
  "phase_title": "Phase 1: Fundamentals"
}
```

### Phase Test - Submit
```
POST /tests/submit
Content-Type: application/json

{
  "quiz_id": "quiz_abc123",
  "answers": {
    "q1": 0,
    "q2": 1,
    "q3": 2
  }
}
```

**Response** (200):
```json
{
  "score": 3,
  "total": 5,
  "percent": 60,
  "results": [
    {
      "id": "q1",
      "correct_index": 0,
      "user_index": 0,
      "correct": true
    }
  ],
  "remediation": {
    "quiz_id": "remed_abc123",
    "phase_title": "Phase 1: Fundamentals",
    "count": 2,
    "questions": [...]
  },
  "badges": [
    {
      "key": "first_test",
      "name": "First Test",
      "earned_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Portfolio

### Get Portfolio
```
GET /portfolio
```

**Response** (200):
```json
{
  "passport": {
    "username": "john_doe",
    "validated_count": 5,
    "developing_count": 3,
    "skills": [
      {
        "name": "Python",
        "slug": "python",
        "domain": "programming",
        "state": "validated",
        "score": 85,
        "evidence_count": 3,
        "last_evidence_at": "2024-01-15T10:30:00Z"
      }
    ],
    "projects": [
      {
        "title": "Data Analysis Project",
        "phase_title": "Phase 2",
        "score": 92,
        "submission_url": "https://github.com/...",
        "reviewed_at": "2024-01-15T10:30:00Z"
      }
    ],
    "test_results": [
      {
        "phase_title": "Phase 1",
        "percent": 85,
        "score": 17,
        "total": 20,
        "date": "2024-01-15"
      }
    ],
    "study_hours": 42.5,
    "generated_at": "2024-01-15T10:30:00Z"
  },
  "settings": {
    "is_public": false,
    "show_projects": true,
    "show_test_scores": true,
    "show_study_hours": true
  }
}
```

### Get Public Portfolio
```
GET /portfolio/{username}
```

**Response** (200):
```json
{
  "passport": {
    "username": "john_doe",
    "validated_count": 5,
    "developing_count": 3,
    "skills": [...],
    "projects": [...],
    "test_results": [...],
    "study_hours": 42.5,
    "generated_at": "2024-01-15T10:30:00Z"
  }
}
```

### Update Portfolio Privacy
```
POST /portfolio/privacy
Content-Type: application/json

{
  "is_public": true,
  "show_projects": true,
  "show_test_scores": true,
  "show_study_hours": false
}
```

**Response** (200):
```json
{
  "settings": {
    "is_public": true,
    "show_projects": true,
    "show_test_scores": true,
    "show_study_hours": false
  }
}
```

### Export Portfolio
```
GET /portfolio/export
```

**Response** (200):
```
Content-Type: text/markdown

# Skill Passport — john_doe
*Generated 2024-01-15*

**5** validated skills · **3** developing

## Validated Skills
- ✅ **Python** (programming) — best score 85%
...
```

---

## Study

### Get Flashcards
```
GET /paths/{path_id}/flashcards
```

**Response** (200):
```json
{
  "cards": [
    {
      "id": 1,
      "front": "What is a variable?",
      "back": "A named container for storing data",
      "topic": "Python Basics",
      "due_at": "2024-01-15T10:30:00Z",
      "ease": 2.5,
      "interval_days": 1,
      "reps": 0
    }
  ]
}
```

### Generate Flashcards
```
POST /paths/{path_id}/flashcards/generate
Content-Type: application/json

{
  "phase_idx": 0,
  "count": 12
}
```

**Response** (200):
```json
{
  "cards": [...]
}
```

### Review Flashcard
```
POST /flashcards/{card_id}/review
Content-Type: application/json

{
  "rating": "good"
}
```

**Response** (200):
```json
{
  "ok": true,
  "next_due": "2024-01-17T10:30:00Z"
}
```

---

## Groups

### Create Group
```
POST /groups/create
Content-Type: application/json

{
  "name": "Python Study Group"
}
```

**Response** (200):
```json
{
  "group": {
    "id": 1,
    "name": "Python Study Group",
    "code": "ABC123",
    "owner_id": 1,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Join Group
```
POST /groups/join
Content-Type: application/json

{
  "code": "ABC123"
}
```

**Response** (200):
```json
{
  "group": {
    "id": 1,
    "name": "Python Study Group",
    "code": "ABC123"
  }
}
```

### Set Group Deadline
```
POST /groups/{group_id}/deadline
Content-Type: application/json

{
  "title": "Complete Phase 1",
  "due_date": "2024-02-15",
  "description": "Finish all Phase 1 topics and pass the test"
}
```

**Response** (200):
```json
{
  "deadline": {
    "id": 1,
    "title": "Complete Phase 1",
    "due_date": "2024-02-15",
    "description": "...",
    "created_by": 1,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Post Check-in
```
POST /groups/{group_id}/checkin
Content-Type: application/json

{
  "message": "Just finished Python basics! Moving to data structures next."
}
```

**Response** (200):
```json
{
  "checkin": {
    "id": 1,
    "user_id": 1,
    "message": "Just finished Python basics!...",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Group Check-ins
```
GET /groups/{group_id}/checkins?limit=20
```

**Response** (200):
```json
{
  "checkins": [
    {
      "id": 1,
      "user": "john_doe",
      "message": "Just finished Python basics!...",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Error Handling

### Error Response Format
```json
{
  "error": "Generic error message"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (login required) |
| 403 | Forbidden (no permission) |
| 404 | Not found |
| 500 | Server error |

### Example Errors

**Validation Error** (400):
```json
{
  "error": "Goal is required"
}
```

**Authentication Error** (401):
```json
{
  "error": "Login required"
}
```

**Not Found** (404):
```json
{
  "error": "Path not found"
}
```

---

## Rate Limiting

Currently no rate limiting. Recommended limits:
- Auth endpoints: 5 requests/minute per IP
- Other endpoints: 60 requests/minute per user

---

## CORS

CORS is configured for:
- `http://localhost:3000` (development)
- `http://localhost:5173` (Vite dev)
- Production domains (configured in settings)

---

## Pagination

Most list endpoints support pagination:
```
GET /paths/history?limit=20&offset=0
```

---

## Webhooks

Not currently implemented. Planned for future release.

---

## SDK/Client Libraries

### JavaScript/TypeScript
```javascript
import * as api from './api/client.js';

// Generate path
const result = await api.pathGenerate({
  goal: "Learn Python",
  current_level: "beginner",
  hours_per_day: 2,
  months: 6
});

// Get workspace
const workspace = await api.getPathWorkspace(result.id);

// Save progress
await api.saveProgress(result.id, "t:0:0", true);
```

---

## Changelog

### v1.0 (Current)
- Initial API release
- Authentication endpoints
- Path generation and management
- Assessment endpoints
- Portfolio endpoints
- Study endpoints
- Group collaboration endpoints

---

## Support

For API issues:
- Check error messages for details
- Review this documentation
- Check GitHub issues
- Contact support@learnpath.com

---

**Last Updated**: 2024
**Version**: 1.0
