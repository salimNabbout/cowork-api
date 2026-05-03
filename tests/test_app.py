def _payload(name="Salim", email="salim@example.com", is_active=True, password=None):
    p = {"name": name, "email": email, "is_active": is_active}
    if password is not None:
        p["password"] = password
    return p


def _register_and_login(client, name="owner", email="owner@example.com", password="pwd123"):
    """Cria um usuario com senha, faz login e retorna (user_id, headers_com_bearer)."""
    r = client.post("/users", json=_payload(name=name, email=email, password=password))
    assert r.status_code == 201
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return uid, {"Authorization": f"Bearer {token}"}


# =====================================================================
# /health
# =====================================================================

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# =====================================================================
# Users (testes legacy - sem senha)
# =====================================================================

def test_create_user(client):
    r = client.post("/users", json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["name"] == "Salim"
    assert body["email"] == "salim@example.com"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "password" not in body


def test_create_user_duplicate_email_returns_409(client):
    assert client.post("/users", json=_payload()).status_code == 201
    r = client.post("/users", json=_payload(name="Outro"))
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already registered"


def test_create_user_invalid_email_returns_422(client):
    r = client.post("/users", json=_payload(email="not-an-email"))
    assert r.status_code == 422


def test_list_users_pagination(client):
    for i in range(1, 6):
        client.post("/users", json=_payload(name=f"u{i}", email=f"u{i}@x.com"))

    r = client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) == 5

    r = client.get("/users?skip=0&limit=2")
    assert [u["id"] for u in r.json()] == [1, 2]

    r = client.get("/users?skip=2&limit=2")
    assert [u["id"] for u in r.json()] == [3, 4]

    r = client.get("/users?skip=4&limit=2")
    assert [u["id"] for u in r.json()] == [5]

    r = client.get("/users?skip=0&limit=100")
    assert len(r.json()) == 5


def test_list_users_limit_above_100_returns_422(client):
    r = client.get("/users?limit=101")
    assert r.status_code == 422


def test_get_user_by_id(client):
    client.post("/users", json=_payload())
    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json()["email"] == "salim@example.com"


def test_get_user_not_found_returns_404(client):
    r = client.get("/users/999")
    assert r.status_code == 404


def test_put_full_update(client):
    client.post("/users", json=_payload())
    r = client.put("/users/1", json=_payload(name="Salim Atualizado", is_active=False))
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Salim Atualizado"
    assert body["is_active"] is False


def test_put_not_found_returns_404(client):
    r = client.put("/users/999", json=_payload())
    assert r.status_code == 404


def test_patch_only_name(client):
    client.post("/users", json=_payload())
    r = client.patch("/users/1", json={"name": "Nome Novo"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Nome Novo"
    assert body["email"] == "salim@example.com"
    assert body["is_active"] is True


def test_patch_only_is_active(client):
    client.post("/users", json=_payload())
    r = client.patch("/users/1", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_patch_only_email(client):
    client.post("/users", json=_payload())
    r = client.patch("/users/1", json={"email": "novo@example.com"})
    assert r.status_code == 200
    assert r.json()["email"] == "novo@example.com"


def test_patch_email_conflict_returns_409(client):
    client.post("/users", json=_payload(name="Ana", email="ana@example.com"))
    client.post("/users", json=_payload(name="Bruno", email="bruno@example.com"))
    r = client.patch("/users/2", json={"email": "ana@example.com"})
    assert r.status_code == 409


def test_patch_not_found_returns_404(client):
    r = client.patch("/users/999", json={"name": "x"})
    assert r.status_code == 404


def test_patch_empty_body_keeps_user_unchanged(client):
    client.post("/users", json=_payload())
    r = client.patch("/users/1", json={})
    assert r.status_code == 200
    assert r.json()["name"] == "Salim"


def test_delete_user(client):
    client.post("/users", json=_payload())
    r = client.delete("/users/1")
    assert r.status_code == 204


def test_get_after_delete_returns_404(client):
    client.post("/users", json=_payload())
    assert client.delete("/users/1").status_code == 204
    r = client.get("/users/1")
    assert r.status_code == 404


def test_delete_not_found_returns_404(client):
    r = client.delete("/users/999")
    assert r.status_code == 404


# =====================================================================
# Auth
# =====================================================================

def test_user_read_does_not_expose_password(client):
    r = client.post("/users", json=_payload(password="secret"))
    assert r.status_code == 201
    body = r.json()
    assert "hashed_password" not in body
    assert "password" not in body


def test_login_with_valid_credentials_returns_token(client):
    client.post("/users", json=_payload(password="pwd123"))
    r = client.post("/auth/login", json={"email": "salim@example.com", "password": "pwd123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20


def test_login_wrong_password_returns_401(client):
    client.post("/users", json=_payload(password="pwd123"))
    r = client.post("/auth/login", json={"email": "salim@example.com", "password": "WRONG"})
    assert r.status_code == 401


def test_login_unknown_email_returns_401(client):
    r = client.post("/auth/login", json={"email": "ninguem@x.com", "password": "x"})
    assert r.status_code == 401


def test_login_user_without_password_returns_401(client):
    client.post("/users", json=_payload())  # criado sem password
    r = client.post("/auth/login", json={"email": "salim@example.com", "password": "anything"})
    assert r.status_code == 401


def test_login_inactive_user_returns_401(client):
    client.post("/users", json=_payload(password="pwd123"))
    client.patch("/users/1", json={"is_active": False})
    r = client.post("/auth/login", json={"email": "salim@example.com", "password": "pwd123"})
    assert r.status_code == 401


def test_password_change_via_patch_works(client):
    client.post("/users", json=_payload(password="old"))
    r = client.patch("/users/1", json={"password": "new"})
    assert r.status_code == 200
    assert client.post("/auth/login", json={"email": "salim@example.com", "password": "old"}).status_code == 401
    assert client.post("/auth/login", json={"email": "salim@example.com", "password": "new"}).status_code == 200


# =====================================================================
# Tasks (todos protegidos por JWT)
# =====================================================================

def test_tasks_endpoints_require_auth(client):
    # POST /users/1/tasks
    assert client.post("/users/1/tasks", json={"title": "x"}).status_code == 401
    # GET /users/1/tasks
    assert client.get("/users/1/tasks").status_code == 401
    # GET /tasks/1
    assert client.get("/tasks/1").status_code == 401
    # PATCH /tasks/1
    assert client.patch("/tasks/1", json={"title": "x"}).status_code == 401
    # DELETE /tasks/1
    assert client.delete("/tasks/1").status_code == 401


def test_tasks_with_invalid_token_returns_401(client):
    headers = {"Authorization": "Bearer not-a-real-jwt"}
    assert client.get("/tasks/1", headers=headers).status_code == 401


def test_create_task(client):
    uid, headers = _register_and_login(client)
    r = client.post(f"/users/{uid}/tasks", json={"title": "Buy milk"}, headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Buy milk"
    assert body["description"] is None
    assert body["completed"] is False
    assert body["user_id"] == uid


def test_create_task_with_all_fields(client):
    uid, headers = _register_and_login(client)
    r = client.post(
        f"/users/{uid}/tasks",
        json={"title": "Write report", "description": "Q4 summary", "completed": False},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["description"] == "Q4 summary"


def test_create_task_for_inexistent_user_returns_404(client):
    _, headers = _register_and_login(client)
    r = client.post("/users/999/tasks", json={"title": "x"}, headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_create_task_for_other_user_returns_404(client):
    # u1 cria conta e tenta criar task para u2
    _u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    u2, _ = _register_and_login(client, name="b", email="b@b.com", password="pb")
    r = client.post(f"/users/{u2}/tasks", json={"title": "x"}, headers=h1)
    assert r.status_code == 404


def test_list_user_tasks(client):
    uid, headers = _register_and_login(client)
    for t in ["t1", "t2", "t3"]:
        client.post(f"/users/{uid}/tasks", json={"title": t}, headers=headers)
    r = client.get(f"/users/{uid}/tasks", headers=headers)
    assert r.status_code == 200
    assert [t["title"] for t in r.json()] == ["t1", "t2", "t3"]


def test_list_tasks_isolated_per_user(client):
    u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    u2, h2 = _register_and_login(client, name="b", email="b@b.com", password="pb")
    client.post(f"/users/{u1}/tasks", json={"title": "u1-task"}, headers=h1)
    client.post(f"/users/{u2}/tasks", json={"title": "u2-task"}, headers=h2)
    assert [t["title"] for t in client.get(f"/users/{u1}/tasks", headers=h1).json()] == ["u1-task"]
    assert [t["title"] for t in client.get(f"/users/{u2}/tasks", headers=h2).json()] == ["u2-task"]


def test_list_tasks_for_other_user_returns_404(client):
    _u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    u2, _ = _register_and_login(client, name="b", email="b@b.com", password="pb")
    r = client.get(f"/users/{u2}/tasks", headers=h1)
    assert r.status_code == 404


def test_list_tasks_for_inexistent_user_returns_404(client):
    _, headers = _register_and_login(client)
    r = client.get("/users/999/tasks", headers=headers)
    assert r.status_code == 404


def test_list_user_tasks_pagination(client):
    uid, headers = _register_and_login(client)
    for i in range(1, 6):
        client.post(f"/users/{uid}/tasks", json={"title": f"t{i}"}, headers=headers)
    r = client.get(f"/users/{uid}/tasks?skip=2&limit=2", headers=headers)
    assert [t["title"] for t in r.json()] == ["t3", "t4"]


def test_get_task_by_id(client):
    uid, headers = _register_and_login(client)
    tid = client.post(f"/users/{uid}/tasks", json={"title": "x"}, headers=headers).json()["id"]
    r = client.get(f"/tasks/{tid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "x"
    assert r.json()["user_id"] == uid


def test_get_task_of_other_user_returns_404(client):
    u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    _u2, h2 = _register_and_login(client, name="b", email="b@b.com", password="pb")
    tid = client.post(f"/users/{u1}/tasks", json={"title": "u1"}, headers=h1).json()["id"]
    r = client.get(f"/tasks/{tid}", headers=h2)
    assert r.status_code == 404
    assert r.json()["detail"] == "Task not found"


def test_get_task_not_found_returns_404(client):
    _, headers = _register_and_login(client)
    r = client.get("/tasks/999", headers=headers)
    assert r.status_code == 404


def test_patch_task_only_completed(client):
    uid, headers = _register_and_login(client)
    tid = client.post(f"/users/{uid}/tasks", json={"title": "x"}, headers=headers).json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"completed": True}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is True
    assert body["title"] == "x"


def test_patch_task_only_title(client):
    uid, headers = _register_and_login(client)
    tid = client.post(f"/users/{uid}/tasks", json={"title": "old", "description": "keep"}, headers=headers).json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"title": "new"}, headers=headers)
    body = r.json()
    assert body["title"] == "new"
    assert body["description"] == "keep"


def test_patch_task_of_other_user_returns_404(client):
    u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    _u2, h2 = _register_and_login(client, name="b", email="b@b.com", password="pb")
    tid = client.post(f"/users/{u1}/tasks", json={"title": "u1"}, headers=h1).json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"title": "hack"}, headers=h2)
    assert r.status_code == 404


def test_patch_task_not_found_returns_404(client):
    _, headers = _register_and_login(client)
    r = client.patch("/tasks/999", json={"title": "x"}, headers=headers)
    assert r.status_code == 404


def test_delete_task(client):
    uid, headers = _register_and_login(client)
    tid = client.post(f"/users/{uid}/tasks", json={"title": "x"}, headers=headers).json()["id"]
    r = client.delete(f"/tasks/{tid}", headers=headers)
    assert r.status_code == 204
    assert client.get(f"/tasks/{tid}", headers=headers).status_code == 404


def test_delete_task_of_other_user_returns_404(client):
    u1, h1 = _register_and_login(client, name="a", email="a@a.com", password="pa")
    _u2, h2 = _register_and_login(client, name="b", email="b@b.com", password="pb")
    tid = client.post(f"/users/{u1}/tasks", json={"title": "u1"}, headers=h1).json()["id"]
    r = client.delete(f"/tasks/{tid}", headers=h2)
    assert r.status_code == 404
    # task ainda existe para o owner
    assert client.get(f"/tasks/{tid}", headers=h1).status_code == 200


def test_delete_task_not_found_returns_404(client):
    _, headers = _register_and_login(client)
    r = client.delete("/tasks/999", headers=headers)
    assert r.status_code == 404
