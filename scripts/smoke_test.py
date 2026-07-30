"""Smoke test rápido de endpoints principales."""

from io import BytesIO

from fastapi.testclient import TestClient

from main import app

TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

with TestClient(app) as client:
    r = client.get("/health")
    print("health", r.status_code, r.json())

    r2 = client.post("/api/auth/login/json", json={"username": "admin", "password": "admin123"})
    print("admin login", r2.status_code)
    token = r2.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r3 = client.get("/api/auth/me", headers=headers)
    print("me", r3.status_code, r3.json()["role"], "avatar", r3.json().get("avatar_url"))

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "tmp_avatar_user",
            "email": "tmp_avatar_user@admitomi.com",
            "password": "test1234",
            "role": "specialist",
            "full_name": "Tmp Avatar",
        },
    )
    # puede existir de una corrida previa
    if created.status_code == 409:
        users = client.get("/api/admin/users?q=tmp_avatar_user", headers=headers).json()
        user_id = users[0]["id"]
    else:
        print("create user", created.status_code)
        user_id = created.json()["id"]

    avatar = client.post(
        f"/api/admin/users/{user_id}/avatar",
        headers=headers,
        files={"file": ("avatar.png", BytesIO(TINY_PNG), "image/png")},
    )
    print("avatar upload", avatar.status_code, avatar.json().get("avatar_url"))

    r9 = client.get("/admin", cookies={"access_token": token})
    print("admin dashboard", r9.status_code)
