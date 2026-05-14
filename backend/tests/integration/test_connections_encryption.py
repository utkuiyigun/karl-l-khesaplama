"""
Integration test: PlatformConnection oluşturulduğunda API key/secret'ın
Fernet ile DB'de şifreli saklandığını ve API response'unda asla
döndürülmediğini doğrular (ADR-006).

Bu testler `melon_kar_test` DB'sine karşı koşar (conftest.py).
"""
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret, encrypt_secret
from app.models.platform_connection import PlatformConnection


async def test_api_key_stored_encrypted_in_db(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # 1) Müşteri oluştur
    cust = await client.post(
        "/api/v1/customers",
        json={"email": "enc-test@example.com", "name": "Enc Test"},
    )
    assert cust.status_code == 201
    customer_id = cust.json()["id"]

    # 2) Bağlantı oluştur — plain key gönder
    plain_key = "PLAIN_API_KEY_VERY_SECRET_xyz"
    plain_secret = "PLAIN_API_SECRET_abc_123"
    conn_resp = await client.post(
        f"/api/v1/customers/{customer_id}/connections",
        json={
            "platform": "trendyol",
            "seller_id": "999999",
            "api_key": plain_key,
            "api_secret": plain_secret,
        },
    )
    assert conn_resp.status_code == 201

    # 3) Response body'sinde plain text OLMAMALI ve key alanları gizli
    body_text = conn_resp.text
    assert plain_key not in body_text, "API response plain api_key sızdırdı"
    assert plain_secret not in body_text, "API response plain api_secret sızdırdı"

    body_json = conn_resp.json()
    assert "api_key" not in body_json
    assert "api_secret" not in body_json
    assert "api_key_encrypted" not in body_json
    assert "api_secret_encrypted" not in body_json

    # 4) DB'deki raw değer Fernet token'ı olmalı (gAAAAA prefix'i Fernet'in imzası)
    result = await db_session.execute(
        select(PlatformConnection).where(PlatformConnection.customer_id == customer_id)
    )
    db_conn = result.scalar_one()
    assert db_conn.api_key_encrypted.startswith("gAAAAA"), "API key Fernet ile şifrelenmemiş"
    assert db_conn.api_secret_encrypted.startswith("gAAAAA"), "API secret Fernet ile şifrelenmemiş"
    assert plain_key not in db_conn.api_key_encrypted
    assert plain_secret not in db_conn.api_secret_encrypted

    # 5) Round-trip: şifreli değer doğru çözülebiliyor mu?
    assert decrypt_secret(db_conn.api_key_encrypted) == plain_key
    assert decrypt_secret(db_conn.api_secret_encrypted) == plain_secret


async def test_list_connections_does_not_leak_secrets(client: AsyncClient) -> None:
    cust = await client.post(
        "/api/v1/customers",
        json={"email": "list-test@example.com", "name": "List Test"},
    )
    customer_id = cust.json()["id"]

    secret_marker = "DO_NOT_LEAK_THIS_SECRET_ABC123"
    await client.post(
        f"/api/v1/customers/{customer_id}/connections",
        json={
            "platform": "trendyol",
            "seller_id": "1",
            "api_key": secret_marker,
            "api_secret": secret_marker + "_secret",
        },
    )

    list_resp = await client.get(f"/api/v1/customers/{customer_id}/connections")
    assert list_resp.status_code == 200
    assert secret_marker not in list_resp.text, "List endpoint plain secret sızdırdı"
    for conn in list_resp.json():
        assert "api_key" not in conn
        assert "api_secret" not in conn
        assert "api_key_encrypted" not in conn


def test_encrypt_decrypt_roundtrip() -> None:
    """Birim test: encrypt → decrypt orijinal değeri verir."""
    secret = "trendyol-api-key-xyz-123"
    token = encrypt_secret(secret)
    assert token != secret
    assert decrypt_secret(token) == secret


def test_encrypt_is_non_deterministic() -> None:
    """Fernet aynı input için farklı token üretmeli (nonce + timestamp).
    Bu, rainbow-table tarzı saldırılara karşı koruma sağlar."""
    secret = "same-input-twice"
    a = encrypt_secret(secret)
    b = encrypt_secret(secret)
    assert a != b
    assert decrypt_secret(a) == decrypt_secret(b) == secret
