from app.api.phase0 import settings


def test_public_version_policy_is_not_cached(client, monkeypatch):
    monkeypatch.setattr(settings, 'android_latest_version_code', 15)
    monkeypatch.setattr(settings, 'android_latest_version_name', '1.0.13')
    response = client.get('/android-version')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.json() == {
        'latest_version_code': 15,
        'latest_version_name': '1.0.13',
        'play_url': 'https://play.google.com/store/apps/details?id=com.launchcircle.testers',
    }
    assert client.get('/android-update.apk').status_code == 404


def test_only_play_update_policy_is_available(client, monkeypatch):
    monkeypatch.setattr(settings, 'android_latest_version_code', 14)
    assert client.get('/android-version').json()['latest_version_code'] == 14
    for channel in ('play', 'direct', 'invalid'):
        response = client.get(f'/android-version?channel={channel}')
        assert response.status_code == 200
        assert response.json() == client.get('/android-version').json()
