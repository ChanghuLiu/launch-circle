import pytest

from app.core.config import Settings
from app.services import google_play_billing


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = b"{}" if payload is not None else b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP failure")

    def json(self):
        return self._payload


def test_package_verification_reads_play_reviews_without_mutating_play(monkeypatch):
    requested = []

    class FakeSession:
        def request(self, method, url, timeout):
            requested.append((method, url, timeout))
            return FakeResponse(200, {"reviews": []})

    monkeypatch.setattr(google_play_billing, "_credentials", lambda _credentials_json: object())
    monkeypatch.setattr(
        google_play_billing.google.auth.transport.requests,
        "AuthorizedSession",
        lambda _credentials: FakeSession(),
    )

    google_play_billing.verify_app_package_ownership(
        Settings(google_play_service_account_json="{}"), "com.example.owned"
    )

    assert [request[0] for request in requested] == ["GET"]
    assert all("com.example.owned" in request[1] for request in requested)
    assert requested[0][1].endswith("/reviews")


def test_package_verification_rejects_inaccessible_app(monkeypatch):
    class FakeSession:
        def request(self, *_args, **_kwargs):
            return FakeResponse(403)

    monkeypatch.setattr(google_play_billing, "_credentials", lambda _credentials_json: object())
    monkeypatch.setattr(
        google_play_billing.google.auth.transport.requests,
        "AuthorizedSession",
        lambda _credentials: FakeSession(),
    )

    with pytest.raises(google_play_billing.GooglePlayPackageNotOwned):
        google_play_billing.verify_app_package_ownership(
            Settings(google_play_service_account_json="{}"), "com.example.notowned"
        )


def test_one_time_purchase_uses_productsv2_and_normalizes_test_order(monkeypatch):
    requested = []

    class FakeSession:
        def request(self, method, url, timeout):
            requested.append((method, url, timeout))
            return FakeResponse(
                200,
                {
                    "productLineItem": [
                        {
                            "productId": "additional_app_1",
                            "productOfferDetails": {"quantity": 1},
                        }
                    ],
                    "purchaseStateContext": {"purchaseState": "PURCHASED"},
                    "consumptionState": "CONSUMPTION_STATE_CONSUMED",
                    "testPurchaseContext": {"fopType": "TEST"},
                    "obfuscatedExternalAccountId": "bound-intent",
                },
            )

    monkeypatch.setattr(google_play_billing, "_credentials", lambda _credentials_json: object())
    monkeypatch.setattr(
        google_play_billing.google.auth.transport.requests,
        "AuthorizedSession",
        lambda _credentials: FakeSession(),
    )

    result = google_play_billing.get_product_purchase(
        Settings(google_play_service_account_json="{}"),
        "additional_app_1",
        "fake-token",
    )

    assert requested[0][0] == "GET"
    assert requested[0][1].endswith(
        "/purchases/productsv2/tokens/fake-token"
    )
    assert result == {
        "productId": "additional_app_1",
        "purchaseState": 0,
        "consumptionState": 1,
        "quantity": 1,
        "regionCode": None,
        "orderId": None,
        "obfuscatedExternalAccountId": "bound-intent",
        "purchaseType": 0,
    }
