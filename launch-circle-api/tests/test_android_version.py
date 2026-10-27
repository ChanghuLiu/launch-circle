from app.api.phase0 import settings


def test_public_version_policy_is_not_cached(client, monkeypatch):
    monkeypatch.setattr(settings, 'android_latest_version_code', 15)
    monkeypatch.setattr(settings, 'android_latest_version_name', '1.0.13')
    monkeypatch.setattr(settings, 'android_apk_path', '')
    response = client.get('/android-version')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.json()['latest_version_code'] == 15
    assert response.json()['apk_url'] is None


def test_apk_endpoint_serves_only_configured_file(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'android_apk_path', '')
    assert client.get('/android-update.apk').status_code == 404
    apk = tmp_path / 'test.apk'
    apk.write_bytes(b'APK test bytes')
    monkeypatch.setattr(settings, 'android_apk_path', str(apk))
    response = client.get('/android-update.apk')
    assert response.status_code == 200 and response.content == b'APK test bytes'
    assert response.headers['content-type'] == 'application/vnd.android.package-archive'
    assert client.get('/android-version').json()['apk_url'] == '/android-update.apk'


def test_play_and_direct_channels_are_separate(client, monkeypatch):
    monkeypatch.setattr(settings, 'android_latest_version_code', 14)
    monkeypatch.setattr(settings, 'android_direct_latest_version_code', 15)
    assert client.get('/android-version').json()['latest_version_code'] == 14
    assert client.get('/android-version?channel=direct').json()['latest_version_code'] == 15
    assert client.get('/android-version?channel=invalid').status_code == 422
