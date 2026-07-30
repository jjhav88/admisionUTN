"""Pruebas críticas de autenticación, roles, CRUD de usuarios y permisos finos."""

import uuid

from fastapi.testclient import TestClient

from main import app


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login/json", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, 'admin', 'admin123')}"}


def _create_specialist(client: TestClient, headers: dict, label: str = "esp") -> dict:
    suffix = f"{label}_{uuid.uuid4().hex[:8]}"
    payload = {
        "username": f"u_{suffix}",
        "email": f"{suffix}@admitomi.com",
        "full_name": f"Especialista {label}",
        "password": "especialista123",
        "role": "specialist",
        "is_active": True,
    }
    response = client.post("/api/admin/users", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_login_and_me():
    with TestClient(app) as client:
        token = _login(client, "admin", "admin123")
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["role"] == "admin"


def test_user_can_update_own_profile():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        specialist = _create_specialist(client, headers, "prof")
        stoken = _login(client, specialist["username"], "especialista123")
        sheaders = {"Authorization": f"Bearer {stoken}"}

        updated = client.put(
            "/api/auth/me",
            headers=sheaders,
            json={"full_name": "Nombre Actualizado", "email": f"new_{specialist['username']}@admitomi.com"},
        )
        assert updated.status_code == 200
        assert updated.json()["full_name"] == "Nombre Actualizado"

        page = client.get("/profile", cookies={"access_token": stoken})
        assert page.status_code == 200
        assert "Mi perfil" in page.text


def test_admin_user_crud_search_edit_delete():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        created = _create_specialist(client, headers, "crud")

        listed = client.get(f"/api/admin/users?q={created['username']}", headers=headers)
        assert listed.status_code == 200
        assert any(u["id"] == created["id"] for u in listed.json())

        updated = client.put(
            f"/api/admin/users/{created['id']}",
            headers=headers,
            json={"full_name": "Especialista Editado", "is_active": True},
        )
        assert updated.status_code == 200
        assert updated.json()["full_name"] == "Especialista Editado"

        deleted = client.delete(f"/api/admin/users/{created['id']}", headers=headers)
        assert deleted.status_code == 204


def test_admin_cannot_delete_self_or_last_admin():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        me = client.get("/api/auth/me", headers=headers).json()
        denied = client.delete(f"/api/admin/users/{me['id']}", headers=headers)
        assert denied.status_code == 403


def test_specialist_cannot_access_admin_users():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        specialist = _create_specialist(client, headers, "deny")
        stoken = _login(client, specialist["username"], "especialista123")
        denied = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {stoken}"},
        )
        assert denied.status_code == 403


def test_specialist_edit_requires_permission():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        specialist = _create_specialist(client, headers, "perm")

        career = client.post(
            "/api/admin/careers",
            headers=headers,
            json={"name": f"Carrera Perm {uuid.uuid4().hex[:6]}", "description": "Test", "is_active": True},
        )
        assert career.status_code == 201, career.text
        career_id = career.json()["id"]

        editable = client.post(
            "/api/admin/categories",
            headers=headers,
            json={"name": f"Requisitos {uuid.uuid4().hex[:6]}", "description": "Docs", "is_editable": True},
        )
        assert editable.status_code == 201, editable.text
        editable_cat = editable.json()

        locked = client.post(
            "/api/admin/categories",
            headers=headers,
            json={"name": f"Becas {uuid.uuid4().hex[:6]}", "description": "Apoyos", "is_editable": True},
        )
        assert locked.status_code == 201, locked.text
        locked_cat = locked.json()

        client.post(
            "/api/admin/permissions",
            headers=headers,
            json={
                "user_id": specialist["id"],
                "career_id": career_id,
                "category_id": editable_cat["id"],
                "can_edit": True,
            },
        )

        stoken = _login(client, specialist["username"], "especialista123")
        sheaders = {"Authorization": f"Bearer {stoken}"}

        put_ok = client.put(
            f"/api/specialist/careers/{career_id}/info/{editable_cat['id']}",
            headers=sheaders,
            json={"content": "<p>Actualizado por prueba</p>"},
        )
        assert put_ok.status_code == 200

        put_denied = client.put(
            f"/api/specialist/careers/{career_id}/info/{locked_cat['id']}",
            headers=sheaders,
            json={"content": "no permitido"},
        )
        assert put_denied.status_code == 403


def test_admin_careers_crud_search_reorder():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        suffix = uuid.uuid4().hex[:6]
        c1 = client.post(
            "/api/admin/careers",
            headers=headers,
            json={
                "name": f"Carrera A {suffix}",
                "level": "licenciatura",
                "is_active": True,
            },
        ).json()
        c2 = client.post(
            "/api/admin/careers",
            headers=headers,
            json={
                "name": f"Carrera B {suffix}",
                "level": "maestria",
                "is_active": True,
            },
        ).json()

        assert c1["level"] == "licenciatura"
        assert c2["level"] == "maestria"

        listed = client.get(f"/api/admin/careers?q={suffix}", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 2

        by_level = client.get(
            f"/api/admin/careers?q={suffix}&level=maestria",
            headers=headers,
        )
        assert by_level.status_code == 200
        assert all(item["level"] == "maestria" for item in by_level.json())

        reordered = client.put(
            "/api/admin/careers/reorder",
            headers=headers,
            json={"ids": [c2["id"], c1["id"]]},
        )
        assert reordered.status_code == 200

        updated = client.put(
            f"/api/admin/careers/{c1['id']}",
            headers=headers,
            json={"description": "Editada", "level": "curso_posgrado"},
        )
        assert updated.status_code == 200
        assert updated.json()["description"] == "Editada"
        assert updated.json()["level"] == "curso_posgrado"

        deleted = client.delete(f"/api/admin/careers/{c2['id']}", headers=headers)
        assert deleted.status_code == 204
        client.delete(f"/api/admin/careers/{c1['id']}", headers=headers)


def test_admin_categories_crud_search_reorder():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        suffix = uuid.uuid4().hex[:6]
        c1 = client.post(
            "/api/admin/categories",
            headers=headers,
            json={"name": f"Cat A {suffix}", "description": "Primera", "is_editable": True},
        )
        assert c1.status_code == 201, c1.text
        c1 = c1.json()
        c2 = client.post(
            "/api/admin/categories",
            headers=headers,
            json={"name": f"Cat B {suffix}", "description": "Segunda", "is_editable": False},
        )
        assert c2.status_code == 201, c2.text
        c2 = c2.json()

        listed = client.get(f"/api/admin/categories?q={suffix}", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 2

        reordered = client.put(
            "/api/admin/categories/reorder",
            headers=headers,
            json={"ids": [c2["id"], c1["id"]]},
        )
        assert reordered.status_code == 200
        order_ids = [item["id"] for item in reordered.json() if item["id"] in {c1["id"], c2["id"]}]
        assert order_ids[:2] == [c2["id"], c1["id"]]

        updated = client.put(
            f"/api/admin/categories/{c1['id']}",
            headers=headers,
            json={"description": "Editada", "is_editable": False},
        )
        assert updated.status_code == 200
        assert updated.json()["description"] == "Editada"
        assert updated.json()["is_editable"] is False

        deleted = client.delete(f"/api/admin/categories/{c2['id']}", headers=headers)
        assert deleted.status_code == 204
        client.delete(f"/api/admin/categories/{c1['id']}", headers=headers)


def test_category_allows_document_flag():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        suffix = uuid.uuid4().hex[:6]
        created = client.post(
            "/api/admin/categories",
            headers=headers,
            json={
                "name": f"Plan de estudios {suffix}",
                "description": "Documento del plan",
                "allows_document": True,
            },
        )
        assert created.status_code == 201, created.text
        data = created.json()
        assert data["allows_document"] is True

        updated = client.put(
            f"/api/admin/categories/{data['id']}",
            headers=headers,
            json={"allows_document": False},
        )
        assert updated.status_code == 200
        assert updated.json()["allows_document"] is False
        client.delete(f"/api/admin/categories/{data['id']}", headers=headers)


def test_specialist_discounts_endpoint():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        specialist = _create_specialist(client, headers, "disc")
        stoken = _login(client, specialist["username"], "especialista123")
        response = client.get(
            "/api/specialist/discounts",
            headers={"Authorization": f"Bearer {stoken}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
