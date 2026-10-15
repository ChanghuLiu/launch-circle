"""Server-side validation and consumption for Google Play one-time products."""

import json
from functools import lru_cache

import google.auth
import google.auth.transport.requests

from app.core.config import Settings

PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
PUBLISHER_ROOT = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class GooglePlayBillingUnavailable(RuntimeError):
    pass


class GooglePlayPackageNotOwned(RuntimeError):
    pass


def product_for(
    settings: Settings, purchase_kind: str, has_credit: bool = False
) -> tuple[str, int]:
    if purchase_kind == "ADDITIONAL_APP":
        return settings.google_play_additional_app_product_id, 100
    if purchase_kind == "MANAGED_LAUNCH":
        if has_credit:
            return settings.google_play_managed_credit_product_id, 1400
        return settings.google_play_managed_product_id, 1500
    raise ValueError("Unknown Google Play purchase kind")


@lru_cache(maxsize=4)
def _credentials(credentials_json: str):
    """Load inline credentials or Application Default Credentials (including WIF)."""
    try:
        if credentials_json.strip():
            info = json.loads(credentials_json)
            credentials, _ = google.auth.load_credentials_from_dict(
                info,
                scopes=[PUBLISHER_SCOPE],
            )
            return credentials
        credentials, _ = google.auth.default(scopes=[PUBLISHER_SCOPE])
        return credentials
    except (
        ValueError,
        TypeError,
        KeyError,
        google.auth.exceptions.GoogleAuthError,
    ) as error:
        raise GooglePlayBillingUnavailable("Google Play verification is not configured.") from error


def _request(settings: Settings, method: str, path: str) -> dict:
    return _request_for_package(settings, settings.google_play_package_name, method, path)


def _request_for_package(settings: Settings, package_name: str, method: str, path: str) -> dict:
    credentials = _credentials(settings.google_play_service_account_json)
    session = google.auth.transport.requests.AuthorizedSession(credentials)
    url = f"{PUBLISHER_ROOT}/applications/{package_name}/{path}"
    try:
        response = session.request(method, url, timeout=15)
        if response.status_code in {400, 403, 404}:
            raise GooglePlayPackageNotOwned(
                "The package is not accessible through the configured Play developer account."
            )
        response.raise_for_status()
        return response.json() if response.content else {}
    except GooglePlayPackageNotOwned:
        raise
    except Exception as error:
        raise GooglePlayBillingUnavailable(
            "Google Play purchase verification is unavailable."
        ) from error


def verify_app_package_ownership(settings: Settings, package_name: str) -> None:
    """Prove the configured publisher account can read this app's Play record."""
    _request_for_package(settings, package_name, "GET", "reviews")


def get_product_purchase(settings: Settings, product_id: str, purchase_token: str) -> dict:
    # ProductPurchaseV2 is the current verification resource for one-time
    # products. It also identifies license-test purchases explicitly, which
    # lets the pilot accept test-card orders without treating them as live
    # production payments.
    purchase = _request(
        settings,
        "GET",
        f"purchases/productsv2/tokens/{purchase_token}",
    )
    line_items = purchase.get("productLineItem") or []
    line_item = next(
        (item for item in line_items if item.get("productId") == product_id),
        line_items[0] if line_items else {},
    )
    purchase_state = (purchase.get("purchaseStateContext") or {}).get("purchaseState")
    state = {"PURCHASED": 0, "CANCELLED": 1, "PENDING": 2}.get(purchase_state, -1)
    consumption_state = purchase.get("consumptionState")
    offer_details = line_item.get("productOfferDetails") or {}
    test_purchase = (purchase.get("testPurchaseContext") or {}).get("fopType") == "TEST"
    return {
        "productId": line_item.get("productId"),
        "purchaseState": state,
        "consumptionState": 1 if consumption_state == "CONSUMPTION_STATE_CONSUMED" else 0,
        "quantity": offer_details.get("quantity", 1),
        "regionCode": purchase.get("regionCode"),
        "orderId": purchase.get("orderId"),
        "obfuscatedExternalAccountId": purchase.get("obfuscatedExternalAccountId"),
        "purchaseType": 0 if test_purchase else None,
    }


def get_one_time_product(settings: Settings, product_id: str) -> dict:
    return _request(settings, "GET", f"oneTimeProducts/{product_id}")


def validate_catalog_product(product: dict, region_code: str, expected_usd_cents: int) -> bool:
    buy_options = [
        option
        for option in product.get("purchaseOptions", [])
        if option.get("state") == "ACTIVE" and option.get("buyOption") is not None
    ]
    if len(buy_options) != 1:
        return False
    region_price = next(
        (
            item
            for item in buy_options[0].get("regionalPricingAndAvailabilityConfigs", [])
            if item.get("regionCode") == region_code and item.get("availability") == "AVAILABLE"
        ),
        None,
    )
    if region_price is None:
        return False
    money = region_price.get("price") or {}
    if region_code == "US":
        try:
            actual_cents = (
                int(money.get("units", 0)) * 100 + int(money.get("nanos", 0)) // 10_000_000
            )
        except (TypeError, ValueError):
            return False
        return money.get("currencyCode") == "USD" and actual_cents == expected_usd_cents
    currency_code = money.get("currencyCode")
    return isinstance(currency_code, str) and len(currency_code) == 3


def consume_product_purchase(settings: Settings, product_id: str, purchase_token: str) -> None:
    _request(
        settings,
        "POST",
        f"purchases/products/{product_id}/tokens/{purchase_token}:consume",
    )
