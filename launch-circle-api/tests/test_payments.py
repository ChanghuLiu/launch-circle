import hashlib
import json
from datetime import datetime, timezone

from app.api import phase0 as phase0_api
from app.core.database import SessionLocal
from app.models.launch import (
    AdditionalAppPurchase,
    App,
    DeveloperAccount,
    ManagedCheckout,
    ManagedCredit,
    PilotEvent,
)
from app.models.user import User
from app.schemas.phase0 import AppCreate, AdditionalAppCheckoutCreate, GooglePlayPurchaseVerify
from app.services.commercial import managed_offer_snapshot
from app.services.circles import ensure_owner_circle


def buyer_with_app(package_suffix: str):
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    user = User(
        email=f"buyer-{package_suffix}@example.com",
        login_email=f"buyer-{package_suffix}@example.com",
        display_name="Buyer",
        country="CA",
    )
    db.add(user)
    db.flush()
    circle = ensure_owner_circle(db, user)
    account = DeveloperAccount(
        play_developer_account_id="1234567890123456789",
        identity_method="PUBLIC_PUBLISHER",
        verification_status="VERIFIED",
        first_free_claimed_at=now,
    )
    db.add(account)
    db.flush()
    app = App(
        owner_id=user.id,
        developer_account_id=account.id,
        circle_id=circle.id,
        entitlement_status="FIRST_APP_FREE",
        name="Payment Test App",
        package_name=f"com.example.{package_suffix}",
        opt_in_url=f"https://play.google.com/apps/testing/com.example.{package_suffix}",
    )
    db.add(app)
    db.commit()
    return db, user, app


def binding(purchase_id: str) -> str:
    return hashlib.sha256(f"launch-circle:{purchase_id}".encode()).hexdigest()


def catalog_product(product_id: str, cents: int) -> dict:
    return {
        "productId": product_id,
        "purchaseOptions": [
            {
                "state": "ACTIVE",
                "buyOption": {},
                "regionalPricingAndAvailabilityConfigs": [
                    {
                        "regionCode": "US",
                        "availability": "AVAILABLE",
                        "price": {
                            "currencyCode": "USD",
                            "units": str(cents // 100),
                            "nanos": (cents % 100) * 10_000_000,
                        },
                    }
                ],
            }
        ],
    }


def fake_catalog(_settings, product_id: str) -> dict:
    cents = {
        "additional_app_1": 100,
        "managed_launch_14": 1400,
        "managed_launch_15": 1500,
    }[product_id]
    return catalog_product(product_id, cents)


def test_additional_app_grants_one_credit_tied_to_google_order_and_retry_is_idempotent(monkeypatch):
    db, user, app = buyer_with_app("paymentone")
    try:
        intent = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        assert intent.product_id == "additional_app_1"
        assert intent.amount_total == 100
        assert intent.currency == "USD"
        calls = []
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-additional-1",
                "obfuscatedExternalAccountId": binding(intent.id),
            },
        )
        monkeypatch.setattr(phase0_api, "get_one_time_product", fake_catalog)
        monkeypatch.setattr(
            phase0_api, "consume_product_purchase", lambda *_args: calls.append("consume")
        )
        request = GooglePlayPurchaseVerify(
            purchase_id=intent.id,
            purchase_type="ADDITIONAL_APP",
            purchase_token="fake-play-token-additional-12345",
        )
        first = phase0_api.verify_google_play_purchase(
            request, user, db, datetime.now(timezone.utc)
        )
        second = phase0_api.verify_google_play_purchase(
            request, user, db, datetime.now(timezone.utc)
        )
        assert first["status"] == second["status"] == "PAID"
        db.expire_all()
        saved_purchase = db.get(phase0_api.AdditionalAppPurchase, intent.id)
        assert saved_purchase.app_id is None
        assert saved_purchase.google_play_order_id == "GPA.test-additional-1"
        assert saved_purchase.google_play_purchase_token == request.purchase_token
        credit = db.query(ManagedCredit).one()
        assert credit.source_additional_app_purchase_id == saved_purchase.id
        assert credit.source_google_play_order_id == "GPA.test-additional-1"
        assert credit.status == "AVAILABLE"
        assert len(calls) == 2
        assert app.entitlement_status == "FIRST_APP_FREE"
    finally:
        db.close()


def test_pilot_accepts_bound_play_test_purchase_without_region_or_order_id(monkeypatch):
    db, user, _app = buyer_with_app("play-test-order")
    try:
        intent = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        monkeypatch.setattr(phase0_api.settings, "app_env", "pilot")
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "purchaseType": 0,
                "quantity": 1,
                "obfuscatedExternalAccountId": binding(intent.id),
            },
        )
        monkeypatch.setattr(
            phase0_api,
            "get_one_time_product",
            lambda _settings, product_id: {"productId": product_id},
        )
        monkeypatch.setattr(phase0_api, "consume_product_purchase", lambda *_args: None)

        response = phase0_api.verify_google_play_purchase(
            GooglePlayPurchaseVerify(
                purchase_id=intent.id,
                purchase_type="ADDITIONAL_APP",
                purchase_token="fake-play-test-token-without-order-123",
            ),
            user,
            db,
            datetime.now(timezone.utc),
        )

        assert response["status"] == "PAID"
        db.expire_all()
        saved = db.get(AdditionalAppPurchase, intent.id)
        assert saved.status == "PAID"
        assert saved.google_play_order_id == (
            "TEST-GPLAY-"
            + hashlib.sha256("fake-play-test-token-without-order-123".encode()).hexdigest()
        )
        assert saved.google_play_purchase_token == "fake-play-test-token-without-order-123"
    finally:
        db.close()


def test_production_rejects_license_test_purchase(monkeypatch):
    db, user, _app = buyer_with_app("play-test-production")
    try:
        intent = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        monkeypatch.setattr(phase0_api.settings, "app_env", "production")
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "purchaseType": 0,
                "quantity": 1,
                "obfuscatedExternalAccountId": binding(intent.id),
            },
        )
        try:
            phase0_api.verify_google_play_purchase(
                GooglePlayPurchaseVerify(
                    purchase_id=intent.id,
                    purchase_type="ADDITIONAL_APP",
                    purchase_token="fake-play-test-token-production-123",
                ),
                user,
                db,
                datetime.now(timezone.utc),
            )
            assert False, "production must not grant an entitlement for a test purchase"
        except phase0_api.HTTPException as error:
            assert error.status_code == 403
        db.expire_all()
        assert db.get(AdditionalAppPurchase, intent.id).status == "PENDING"
    finally:
        db.close()


def test_managed_price_uses_credit_sku_and_redeems_once(monkeypatch):
    monkeypatch.setattr(phase0_api, "verify_app_package_ownership", lambda *_args: None)
    db, user, app = buyer_with_app("paymentmanaged")
    try:
        additional = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-credit-source",
                "obfuscatedExternalAccountId": binding(additional.id),
            },
        )
        monkeypatch.setattr(phase0_api, "get_one_time_product", fake_catalog)
        monkeypatch.setattr(phase0_api, "consume_product_purchase", lambda *_args: None)
        phase0_api.verify_google_play_purchase(
            GooglePlayPurchaseVerify(
                purchase_id=additional.id,
                purchase_type="ADDITIONAL_APP",
                purchase_token="fake-play-token-credit-source-123",
            ),
            user,
            db,
            datetime.now(timezone.utc),
        )
        full_price = phase0_api.start_managed_checkout(
            app.id, user, db, datetime.now(timezone.utc)
        )
        assert full_price.product_id == "managed_launch_15"
        assert full_price.amount_total == 1500

        paid_app = phase0_api.create_app(
            AppCreate(
                name="Additional payment test app",
                package_name="com.example.paymentmanaged.additional",
                opt_in_url="https://play.google.com/apps/testing/com.example.paymentmanaged.additional",
                play_developer_account_id="1234567890123456789",
            ),
            user,
            db,
            datetime.now(timezone.utc),
        )
        assert paid_app.entitlement_status == "ADDITIONAL_PAID"
        assert managed_offer_snapshot(db, db.get(App, paid_app.id))["managed_credit_amount_cents"] == 100
        assert managed_offer_snapshot(db, app)["managed_credit_amount_cents"] == 0
        checkout = phase0_api.start_managed_checkout(
            paid_app.id, user, db, datetime.now(timezone.utc)
        )
        assert checkout.product_id == "managed_launch_14"
        assert checkout.list_product_id == "managed_launch_15"
        assert checkout.list_price_total == 1500
        assert checkout.credit_amount == 100
        assert checkout.amount_total == 1400
        assert checkout.currency == "USD"
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-managed-1",
                "obfuscatedExternalAccountId": binding(checkout.id),
            },
        )
        monkeypatch.setattr(phase0_api, "get_one_time_product", fake_catalog)
        response = phase0_api.verify_google_play_purchase(
            GooglePlayPurchaseVerify(
                purchase_id=checkout.id,
                purchase_type="MANAGED_LAUNCH",
                purchase_token="fake-play-token-managed-12345",
            ),
            user,
            db,
            datetime.now(timezone.utc),
        )
        assert response["status"] == "PAID"
        db.expire_all()
        credit = db.query(ManagedCredit).one()
        managed = db.get(ManagedCheckout, checkout.id)
        assert credit.status == "REDEEMED"
        assert credit.redeemed_app_id == paid_app.id
        assert managed.status == "PAID"
        assert managed.amount_total == 1400
        assert managed.google_play_order_id == "GPA.test-managed-1"
        assert db.get(App, paid_app.id).entitlement_status == "MANAGED"
        assert db.get(App, app.id).entitlement_status == "FIRST_APP_FREE"
        managed_event = db.query(PilotEvent).filter_by(event_type="managed_payment_success").one()
        assert json.loads(managed_event.payload_json)[
            "same_app_additional_app_purchase_applied"
        ] is True
        retry = phase0_api.verify_google_play_purchase(
            GooglePlayPurchaseVerify(
                purchase_id=checkout.id,
                purchase_type="MANAGED_LAUNCH",
                purchase_token="fake-play-token-managed-12345",
            ),
            user,
            db,
            datetime.now(timezone.utc),
        )
        db.expire_all()
        assert retry["status"] == "PAID"
        assert db.query(ManagedCredit).one().status == "REDEEMED"
        assert db.query(PilotEvent).filter_by(event_type="managed_payment_success").count() == 1
        assert db.get(App, paid_app.id).entitlement_status == "MANAGED"
        assert db.get(App, app.id).entitlement_status == "FIRST_APP_FREE"
    finally:
        db.close()


def test_unverified_managed_purchase_does_not_set_app_entitlement(monkeypatch):
    db, user, app = buyer_with_app("managed-unverified")
    try:
        checkout = phase0_api.start_managed_checkout(
            app.id, user, db, datetime.now(timezone.utc)
        )
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, _product_id, _token: {
                "productId": "additional_app_1",
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-wrong-managed-product",
                "obfuscatedExternalAccountId": binding(checkout.id),
            },
        )
        try:
            phase0_api.verify_google_play_purchase(
                GooglePlayPurchaseVerify(
                    purchase_id=checkout.id,
                    purchase_type="MANAGED_LAUNCH",
                    purchase_token="fake-play-token-wrong-managed-123",
                ),
                user,
                db,
                datetime.now(timezone.utc),
            )
            assert False, "wrong Google Play SKU must not activate Managed Launch"
        except phase0_api.HTTPException as error:
            assert error.status_code == 400
        db.expire_all()
        assert db.get(App, app.id).entitlement_status == "FIRST_APP_FREE"
        assert db.get(ManagedCheckout, checkout.id).status == "PENDING"
        assert db.query(PilotEvent).filter_by(event_type="managed_payment_success").count() == 0
    finally:
        db.close()


def test_wrong_play_product_does_not_grant_purchase_or_credit(monkeypatch):
    db, user, _app = buyer_with_app("paymentinvalid")
    try:
        intent = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda *_args: {
                "productId": "managed_launch_15",
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-wrong-product",
                "obfuscatedExternalAccountId": binding(intent.id),
            },
        )
        try:
            phase0_api.verify_google_play_purchase(
                GooglePlayPurchaseVerify(
                    purchase_id=intent.id,
                    purchase_type="ADDITIONAL_APP",
                    purchase_token="fake-play-token-wrong-product-1",
                ),
                user,
                db,
                datetime.now(timezone.utc),
            )
            assert False, "wrong Google Play SKU must not be accepted"
        except phase0_api.HTTPException as error:
            assert error.status_code == 400
        db.expire_all()
        assert db.get(phase0_api.AdditionalAppPurchase, intent.id).status == "PENDING"
        assert db.query(ManagedCredit).count() == 0
    finally:
        db.close()


def test_play_console_us_base_price_mismatch_rejects_purchase(monkeypatch):
    db, user, _app = buyer_with_app("price-mismatch")
    try:
        intent = phase0_api.start_additional_app_checkout(
            AdditionalAppCheckoutCreate(play_developer_account_id="1234567890123456789"), user, db
        )
        monkeypatch.setattr(
            phase0_api,
            "get_product_purchase",
            lambda _settings, product_id, _token: {
                "productId": product_id,
                "purchaseState": 0,
                "quantity": 1,
                "regionCode": "US",
                "orderId": "GPA.test-price-mismatch",
                "obfuscatedExternalAccountId": binding(intent.id),
            },
        )
        monkeypatch.setattr(
            phase0_api,
            "get_one_time_product",
            lambda _settings, product_id: catalog_product(product_id, 200),
        )
        try:
            phase0_api.verify_google_play_purchase(
                GooglePlayPurchaseVerify(
                    purchase_id=intent.id,
                    purchase_type="ADDITIONAL_APP",
                    purchase_token="fake-play-token-price-mismatch-1",
                ),
                user,
                db,
                datetime.now(timezone.utc),
            )
            assert False, "a Play Console base-price mismatch must not grant the purchase"
        except phase0_api.HTTPException as error:
            assert error.status_code == 503
        db.expire_all()
        assert db.get(phase0_api.AdditionalAppPurchase, intent.id).status == "PENDING"
        assert db.query(ManagedCredit).count() == 0
    finally:
        db.close()


def test_legacy_provider_paid_rows_are_not_treated_as_google_play_payments():
    db, user, app = buyer_with_app("legacyprovider")
    try:
        source = AdditionalAppPurchase(
            owner_id=user.id,
            developer_account_id=app.developer_account_id,
            status="PAID",
            amount_total=100,
            currency="usd",
        )
        db.add(source)
        db.flush()
        db.add(
            ManagedCredit(
                owner_id=user.id,
                developer_account_id=app.developer_account_id,
                source_additional_app_purchase_id=source.id,
                status="AVAILABLE",
            )
        )
        legacy_managed = ManagedCheckout(
            app_id=app.id,
            status="PAID",
            list_price_total=1500,
            amount_total=1500,
            credit_amount=0,
            currency="usd",
        )
        db.add(legacy_managed)
        db.commit()

        assert phase0_api.additional_app_checkout_read(source).status == "EXPIRED"
        assert phase0_api.managed_checkout_read(legacy_managed).status == "EXPIRED"
        fresh = phase0_api.start_managed_checkout(app.id, user, db, datetime.now(timezone.utc))
        assert fresh.product_id == "managed_launch_15"
        assert fresh.amount_total == 1500
        assert fresh.credit_amount == 0
    finally:
        db.close()


def test_google_play_billing_uses_application_default_credentials_for_wif(monkeypatch):
    from app.services import google_play_billing

    expected = object()
    calls = []

    def fake_default(*, scopes):
        calls.append(scopes)
        return expected, None

    google_play_billing._credentials.cache_clear()
    monkeypatch.setattr(google_play_billing.google.auth, "default", fake_default)
    try:
        assert google_play_billing._credentials("") is expected
        assert calls == [[google_play_billing.PUBLISHER_SCOPE]]
    finally:
        google_play_billing._credentials.cache_clear()
