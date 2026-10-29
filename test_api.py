from tests.conftest import SENT, auth, login_as

API = "/api/v1"


def admin_tokens(client):
    return login_as(client, "admin", "Admin12345!", "admin@luvvix.local")


def test_health_and_docs(client):
    assert client.get("/health").json()["status"] == "ok"
    schema = client.get("/openapi.json").json()
    assert "/api/v1/items" in schema["paths"]
    assert client.get("/docs").status_code == 200


def test_register_verify_and_me(client):
    r = client.post(f"{API}/auth/register", json={
        "username": "petrov", "email": "petrov@example.com", "full_name": "Петров П.", "password": "Secret123"})
    assert r.status_code == 201, r.text
    ch = r.json()
    assert ch["purpose"] == "register"
    # неверный код
    r = client.post(f"{API}/auth/verify", json={"challenge_id": ch["challenge_id"], "code": "000000"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_code"
    r = client.post(f"{API}/auth/verify", json={"challenge_id": ch["challenge_id"],
                                                "code": SENT["petrov@example.com"]})
    assert r.status_code == 200
    tokens = r.json()
    me = client.get(f"{API}/auth/me", headers=auth(tokens)).json()
    assert me["role"]["name"] == "storekeeper"
    assert "items:delete" not in me["permissions"]


def test_register_conflict_and_validation(client):
    r = client.post(f"{API}/auth/register", json={
        "username": "petrov", "email": "x@example.com", "password": "Secret123"})
    assert r.status_code == 409
    r = client.post(f"{API}/auth/register", json={"username": "a", "email": "bad", "password": "short"})
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "validation_error" and len(body["errors"]) >= 2


def test_401_without_token_and_bad_token(client):
    assert client.get(f"{API}/items").status_code == 401
    r = client.get(f"{API}/items", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_token"


def test_wrong_password_and_lockout(client):
    client.post(f"{API}/auth/register", json={"username": "lockme", "email": "lock@example.com",
                                              "password": "Secret123"})
    for _ in range(5):
        r = client.post(f"{API}/auth/login", json={"login": "lockme", "password": "Wrong1234"})
        assert r.status_code == 401
    r = client.post(f"{API}/auth/login", json={"login": "lockme", "password": "Secret123"})
    assert r.status_code == 423


def test_items_full_crud_search_filter(client):
    t = admin_tokens(client)
    h = auth(t)
    cats = client.get(f"{API}/categories", headers=h).json()
    cat_id = cats[0]["id"]

    r = client.post(f"{API}/items", headers=h, json={
        "name": "Ноутбук Lenovo", "inventory_number": "INV-001", "quantity": 3, "price": "55000.50",
        "category_id": cat_id, "location": "Кабинет 101"})
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["category"]["id"] == cat_id

    client.post(f"{API}/items", headers=h, json={"name": "Стул", "inventory_number": "INV-002"})

    # дубликат номера → 409
    r = client.post(f"{API}/items", headers=h, json={"name": "X", "inventory_number": "inv-001"})
    assert r.status_code == 409
    # несуществующая категория → 400
    r = client.post(f"{API}/items", headers=h, json={"name": "X", "inventory_number": "INV-9", "category_id": 999})
    assert r.status_code == 400

    # список, поиск, фильтр, сортировка
    lst = client.get(f"{API}/items", headers=h).json()
    assert lst["total"] == 2
    assert client.get(f"{API}/items?search=ноут", headers=h).json()["total"] == 1
    assert client.get(f"{API}/items?category_id={cat_id}", headers=h).json()["total"] == 1
    names = [i["name"] for i in client.get(f"{API}/items?sort=name&order=asc", headers=h).json()["items"]]
    assert names == sorted(names)
    assert client.get(f"{API}/items?sort=hack", headers=h).status_code == 400

    # get one / 404
    assert client.get(f"{API}/items/{item['id']}", headers=h).json()["name"] == "Ноутбук Lenovo"
    assert client.get(f"{API}/items/99999", headers=h).status_code == 404

    # patch + история
    r = client.patch(f"{API}/items/{item['id']}", headers=h, json={"quantity": 5, "name": "Ноутбук Lenovo T14"})
    assert r.status_code == 200 and r.json()["quantity"] == 5
    hist = client.get(f"{API}/items/{item['id']}/history", headers=h).json()
    assert hist[0]["action"] == "update" and "quantity: 3 → 5" in hist[0]["changes"]
    assert client.patch(f"{API}/items/{item['id']}", headers=h, json={}).status_code == 400

    # delete
    assert client.delete(f"{API}/items/{item['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/items/{item['id']}", headers=h).status_code == 404
    assert client.delete(f"{API}/items/{item['id']}", headers=h).status_code == 404


def test_role_model(client):
    admin = auth(admin_tokens(client))
    store = auth(login_as(client, "petrov", "Secret123", "petrov@example.com"))
    item = client.post(f"{API}/items", headers=admin, json={"name": "Шкаф", "inventory_number": "INV-100"}).json()

    # кладовщик: читать — да, создавать/удалять — нет, менять только факт. поля
    assert client.get(f"{API}/items", headers=store).status_code == 200
    assert client.post(f"{API}/items", headers=store, json={"name": "a", "inventory_number": "b"}).status_code == 403
    assert client.delete(f"{API}/items/{item['id']}", headers=store).status_code == 403
    assert client.patch(f"{API}/items/{item['id']}", headers=store, json={"quantity": 7}).status_code == 200
    assert client.patch(f"{API}/items/{item['id']}", headers=store, json={"name": "Новый"}).status_code == 403
    assert client.get(f"{API}/users", headers=store).status_code == 403

    # админ повышает до бухгалтера → права меняются сразу
    users = client.get(f"{API}/users", headers=admin).json()
    petrov = next(u for u in users if u["username"] == "petrov")
    r = client.patch(f"{API}/users/{petrov['id']}", headers=admin, json={"role": "accountant"})
    assert r.status_code == 200 and r.json()["role"]["name"] == "accountant"
    assert client.delete(f"{API}/items/{item['id']}", headers=store).status_code == 204

    # блокировка → токен перестаёт работать
    client.patch(f"{API}/users/{petrov['id']}", headers=admin, json={"is_active": False})
    assert client.get(f"{API}/items", headers=store).status_code == 401
    client.patch(f"{API}/users/{petrov['id']}", headers=admin, json={"is_active": True, "role": "storekeeper"})

    # админ не может менять себя
    me = client.get(f"{API}/auth/me", headers=admin).json()
    assert client.patch(f"{API}/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 400
    assert client.patch(f"{API}/users/9999", headers=admin, json={"is_active": False}).status_code == 404


def test_refresh_rotation_and_reuse_detection(client):
    t = admin_tokens(client)
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200
    t2 = r.json()
    # повторное использование старого → 401 и отзыв всей цепочки
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 401 and r.json()["code"] == "refresh_reused"
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401


def test_logout(client):
    t = admin_tokens(client)
    assert client.post(f"{API}/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_oauth2_token_endpoint(client):
    r = client.post(f"{API}/auth/token", data={"username": "admin", "password": "Admin12345!"})
    assert r.status_code == 401 and r.json()["code"] == "2fa_required"
    r = client.post(f"{API}/auth/token", data={"username": "admin", "password": "Admin12345!",
                                               "client_secret": SENT["admin@luvvix.local"]})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_unknown_route_and_security_headers(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.json()["code"] == "http_404"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_500_is_json(client):
    from app.main import app

    @app.get("/boom-test")
    def boom():
        raise RuntimeError("boom")

    r = client.get("/boom-test")
    assert r.status_code == 500 and r.json()["code"] == "internal_error"
