# Survey-API

A RESTful API for creating, managing, and collecting responses to surveys, built with **Django** and **Django REST Framework**, secured with **JWT authentication**.

This API is the back-end counterpart to my [DjSurvey](https://github.com/Farzan-79/DJSurvey) project, a server-rendered dynamic survey builder with inline formsets and analytics. Survey-API exposes the same domain over HTTP so it can be consumed by any front-end or third-party client.

> **Live deployment:** <LINK-OR-REMOVE-THIS-LINE>

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [API Reference](#api-reference)
- [Example Requests](#example-requests)
- [Data Model](#data-model)
- [Project Structure](#project-structure)
- [CORS](#cors)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Features

- JWT-based authentication (access and refresh tokens)
- Create and manage surveys with nested questions
- Choose from Multiple Choice and Free Text questions
- Submit and store survey responses
- Survey analytics / aggregated results
- Permission rules so users manage their own surveys
- CORS configured for use with a separate front-end

## Tech Stack

| Layer          | Technology                                   |
| -------------- | -------------------------------------------- |
| Language       | Python 3.14                                  |
| Framework      | Django, Django REST Framework                |
| Authentication | JWT                                          |
| Database       | SQLite (dev) / PostgreSQL (prod)             |
| Other          | django-cors-headers                          |

## Getting Started

### Prerequisites

- Python 3.14
- pip
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Farzan-79/Survey-API

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your environment file (see Configuration below)
cp .env.example .env            

# 5. Apply migrations
python manage.py migrate

# 6. (Optional) Create an admin user
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/`.

## Configuration


| Variable                | Description                                  | Example                        |
| ----------------------- | -------------------------------------------- | ------------------------------ |
| `SECRET_KEY`            | Django secret key                            | `change-me`                    |
| `DEBUG`                 | Enable debug mode (never `True` in production) | `True`                       |
| `ALLOWED_HOSTS`         | Comma-separated list of allowed hosts        | `localhost,127.0.0.1`          |
| `CORS_ALLOWED_ORIGINS`  | Origins permitted to call the API            | `http://localhost:3000`        |
| `DATABASE_URL`          | Database connection string                   |                                |

## Authentication

The API uses JSON Web Tokens. The typical flow:

1. **Obtain a token pair** by sending credentials to the token endpoint.
2. **Send the access token** in the `Authorization` header on protected requests:
   ```
   Authorization: Bearer <access_token>
   ```
3. **Refresh the access token** with the refresh token when it expires.

## API Reference

Base URL: `http://127.0.0.1:8000/api/`
Schema URL: `http://127.0.0.1:8000/api/schema/swagger`
See the full reference in the schema URL

### Auth

| Method | Endpoint           | Description                  | Auth required |
| ------ | ------------------ | ---------------------------- | ------------- |
| POST   | `/auth/register/`  | Create a new user            | No            |
| POST   | `/auth/token/`     | Obtain access/refresh tokens | No            |
| POST   | `/auth/token/refresh/` | Refresh an access token  | No            |

### Surveys

| Method | Endpoint                | Description                    | Auth required |
| ------ | ----------------------- | ------------------------------ | ------------- |
| GET    | `/surveys/`             | List surveys                   | Yes           |
| POST   | `/surveys/`             | Create a survey                | Yes           |
| GET    | `/surveys/{id}/`        | Retrieve a survey              | Yes           |
| PUT    | `/surveys/{id}/`        | Update a survey                | Yes (owner)   |
| DELETE | `/surveys/{id}/`        | Delete a survey                | Yes (owner)   |

### Responses

| Method | Endpoint                          | Description                  | Auth required |
| ------ | --------------------------------- | ---------------------------- | ------------- |
| POST   | `/surveys/{id}/responses/`        | Submit a response            | <TODO>        |
| GET    | `/surveys/{id}/results/`          | Aggregated results           | Yes (owner)   |

## Example Requests

**Obtain a token**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "your-password"}'
```

```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

**Create a survey**

```bash
curl -X POST http://127.0.0.1:8000/api/surveys/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Customer feedback",
        "description": "Tell us how we did",
        "questions": [
          {"text": "How satisfied are you?", "type": "rating"}
        ]
      }'
```

## Data Model


- **User**: account used for authentication
- **Survey**: owned by a user; has a title and description
- **Question**: belongs to a survey
- **Response / Answer**: submitted answers to a survey's questions

## Project Structure


```
<REPO-FOLDER>/
├── manage.py
├── requirements.txt
├── <project_package>/      # settings, root urls
└── <app_name>/             # models, serializers, views, urls
```

## CORS

Cross-Origin Resource Sharing is handled with `django-cors-headers`. To allow a front-end running on a different origin, add it to `CORS_ALLOWED_ORIGINS` in your environment/settings.


## Author

**Farzan**: back-end developer focused on Python and Django.

- GitHub: https://github.com/Farzan-79
- Contact: far.kalantarii@gmail.com
