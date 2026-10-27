"""Resolve a public Play icon or an icon accessible to our authorized publisher."""
from html.parser import HTMLParser
from urllib.parse import urlparse
import requests
from google.auth.transport.requests import AuthorizedSession
from app.services.google_play_billing import _credentials

def trusted_icon(url):
    p = urlparse(url)
    return p.scheme == "https" and not p.username and not p.password and p.port in (None, 443) and (p.hostname or "").endswith(".googleusercontent.com")

class IconMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.url = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") == "og:image" or a.get("itemprop") == "image"):
            candidate = a.get("content", "")
            if trusted_icon(candidate):
                self.url = candidate

def resolve_play_icon(package, settings):
    try:
        r = requests.get("https://play.google.com/store/apps/details", params={"id": package, "hl": "en"}, timeout=10, allow_redirects=False)
        r.raise_for_status()
        parser = IconMetadata()
        parser.feed(r.text)
        if parser.url:
            return parser.url
    except (requests.RequestException, ValueError):
        pass
    # A closed-test listing may be invisible to public web requests.
    session = AuthorizedSession(_credentials(settings.google_play_service_account_json))
    root = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/" + package + "/edits"
    edit = None
    try:
        r = session.post(root, json={}, timeout=15)
        r.raise_for_status()
        edit = r.json()["id"]
        r = session.get(root + "/" + edit + "/listings", timeout=15)
        r.raise_for_status()
        for listing in sorted(r.json().get("listings", []), key=lambda x: x["language"] != "en-US"):
            r = session.get(root + "/" + edit + "/listings/" + listing["language"] + "/icon", timeout=15)
            r.raise_for_status()
            for icon in r.json().get("images", []):
                if trusted_icon(icon.get("url", "")):
                    return icon["url"]
        raise ValueError("No published icon")
    finally:
        if edit:
            try:
                session.delete(root + "/" + edit, timeout=10)
            except requests.RequestException:
                pass
        session.close()
