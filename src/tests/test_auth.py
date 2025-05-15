def test_register_and_login(client):
    # 注册用户
    response = client.post('/register', json={
        'username': 'testuser',
        'password': '123456'
    })
    assert response.status_code == 200
    assert response.json['success'] == True

    # 登录
    response = client.post('/login', json={
        'username': 'testuser',
        'password': '123456'
    })
    assert response.status_code == 200
    assert response.json['success'] == True
