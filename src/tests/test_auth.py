def test_register_and_login(client):
    # 注册用户
    response = client.post('/register', json={
        'username': 'testuser',
        'password': '123456'
    })
    assert response.status_code == 200
    assert response.json['success'] == True

    # 注册失败：用户名已存在
    response = client.post('/register', json={
        'username': 'testuser',
        'password': 'newpassword'
    })
    assert response.status_code == 400
    assert response.json['message'] == '用户名已存在'
    assert response.json['success'] == False

    # 注册失败：缺少字段
    response = client.post('/register', json={
        'username': 'newuser'
    })
    assert response.status_code == 400
    assert response.json['message'] == '用户名和密码不能为空'
    assert response.json['success'] == False

    # 登录成功
    response = client.post('/login', json={
        'username': 'testuser',
        'password': '123456'
    })
    assert response.status_code == 200
    assert response.json['success'] == True

    # 登录失败：用户名不存在
    response = client.post('/login', json={
        'username': 'nonexistent',
        'password': '123456'
    })
    assert response.status_code == 400
    assert response.json['message'] == '用户名或密码错误'
    assert response.json['success'] == False

    # 登录失败：密码错误
    response = client.post('/login', json={
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    assert response.status_code == 400
    assert response.json['message'] == '用户名或密码错误'
    assert response.json['success'] == False
