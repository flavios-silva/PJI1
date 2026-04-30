
├── venv/                     # Shared virtual environment
├── backend/
│   ├── run.py                # Entry point (Windows selector-loop fix here)
│   ├── .env                  # Config (DATABASE_URL, SECRET_KEY, etc.)
│   └── app/
│       ├── main.py           # FastAPI app + lifespan + CORS + static files
│       ├── core/
│       │   ├── config.py     # Pydantic Settings
│       │   ├── security.py   # JWT + password hashing
│       │   └── deps.py       # get_current_user (loads User.department eagerly)
│       ├── db/
│       │   ├── session.py    # Async engine (psycopg), get_db()
│       │   └── init_db.py    # Seeds departments, templates, admin/manager users
│       ├── models/           # SQLAlchemy ORM models
│       ├── schemas/          # Pydantic schemas (DailyChecklistOut uses TemplateSummaryOut)
│       └── routers/
│           ├── auth.py       # POST /auth/login, GET /auth/me
│           ├── users.py      # CRUD users (manager only)
│           ├── checklists.py # Full checklist lifecycle
│           └── ws.py         # WebSocket /ws/notifications
└── frontend/
    ├── main.py               # Route-based navigation, WS lifecycle
    └── app/
        ├── state.py          # AppState (token, user, unread_count, media_base)
        ├── api_client.py     # httpx async HTTP client
        ├── ws_client.py      # websockets auto-reconnect listener
        ├── theme.py          # Colors, cards, snackbars, status chips
        └── pages/
            ├── login_page.py
            ├── notifications_page.py
            ├── employee/
            │   ├── home_page.py        # Today's checklists + history
            │   └── checklist_page.py   # Item toggle + photo upload
            └── manager/
                ├── dashboard_page.py   # Pending / All / Team tabs
                ├── review_page.py      # Approve / Reject checklist
                └── new_user_page.py    # Create employee
