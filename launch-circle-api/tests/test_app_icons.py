from tests.test_entitlements import register, create_app

def test_icon_upload_is_owner_only_and_rejects_invalid_content(client):
    owner = register(client, 'icon-owner@example.com', 'Owner')
    other = register(client, 'icon-other@example.com', 'Other')
    result = create_app(client, owner, 'com.example.icon', '12345')
    assert result.status_code == 201
    app_id = result.json()['id']
    assert client.post(f'/apps/{app_id}/icon', headers=other['headers'], json={'data': 'invalid'}).status_code == 403
    assert client.post(f'/apps/{app_id}/icon', headers=owner['headers'], json={'data': 'invalid'}).status_code == 422
    assert client.post(f'/apps/{app_id}/icon/google-play', headers=other['headers']).status_code == 403
