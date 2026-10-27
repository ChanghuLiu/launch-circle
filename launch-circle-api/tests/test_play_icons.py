from types import SimpleNamespace
from unittest.mock import Mock
import requests
from app.services import play_icons as icons

URL = "https://play-lh.googleusercontent.com/example"

def test_metadata_attribute_order_and_entities():
    p = icons.IconMetadata()
    p.feed('<meta content="' + URL + '?a=1&amp;b=2" property="og:image">')
    assert p.url == URL + "?a=1&b=2"
    assert not icons.trusted_icon("https://play-lh.googleusercontent.com.evil.test/icon")
    assert not icons.trusted_icon("https://user@play-lh.googleusercontent.com/icon")

def test_closed_listing_uses_authorized_publisher_and_discards_edit(monkeypatch):
    monkeypatch.setattr(icons.requests, "get", Mock(side_effect=requests.HTTPError()))
    monkeypatch.setattr(icons, "_credentials", lambda _: object())
    session = Mock()
    session.post.return_value.json.return_value = {"id": "temporary-edit"}
    listing = Mock()
    listing.json.return_value = {"listings": [{"language": "en-US"}]}
    image = Mock()
    image.json.return_value = {"images": [{"url": URL}]}
    session.get.side_effect = [listing, image]
    monkeypatch.setattr(icons, "AuthorizedSession", lambda _: session)
    assert icons.resolve_play_icon("com.example.app", SimpleNamespace(google_play_service_account_json="")) == URL
    session.delete.assert_called_once()
    session.close.assert_called_once()
    assert session.get.call_args_list[-1].args[0].endswith("/listings/en-US/icon")
