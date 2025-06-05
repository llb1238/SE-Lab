def assert_json_response(response, expected_success=True, expected_status=200):
    """
    通用断言函数:检查HTTP响应的状态码与JSON中的success字段是否符合预期。

    参数：
        response: Flask 测试客户端返回的 Response 对象
        expected_success: 预期的 success 字段的值（默认 True)
        expected_status: 预期的 HTTP 状态码（默认 200)
    """
    print(response.json)
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}"

    assert response.json.get('success') == expected_success, \
        f"Expected success={expected_success}, got: {response.json.get('success')}"

#测试注册功能
def test_register_and_login(client):
    # 学生注册
    # 注册学生用户：成功
    response = client.post('/register', json={
        'username': 'studentuser',
        'password': '123456',
        'role': 'student'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

    # for i in range(10000):
    #     username = str(i)
    #     response = client.post('/register', json={
    #         'username': username,
    #         'password': '123456',
    #         'role': 'student'
    #     })
    #     assert_json_response(response, expected_success=True, expected_status=200)

    # 注册失败：用户名已存在
    response = client.post('/register', json={
        'username': 'studentuser',
        'password': 'newpassword',
        'role': 'student'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 注册失败：缺少字段
    response = client.post('/register', json={
        'username': 'studentuser2'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    #教师注册
    #注册教师用户：成功
    response = client.post('/register', json={
        'username': 'teacheruser',
        'password': '123456',
        'role': 'teacher'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

    # 注册失败：教师用户名已存在
    response = client.post('/register', json={
        'username': 'teacheruser',
        'password': 'newpassword',
        'role': 'teacher'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 注册失败：学生用户名已存在
    response = client.post('/register', json={
        'username': 'studentuser',
        'password': 'newpassword',
        'role': 'teacher'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 管理员注册
    # 注册管理员：成功
    response = client.post('/register', json={
        'username': 'adminuser',
        'password': '123456',
        'role': 'admin',
        'admin_code': '1'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

    # 注册失败：缺少管理员验证码
    response = client.post('/register', json={
        'username': 'adminuser2',
        'password': '123456',
        'role': 'admin'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 注册失败：管理员验证码错误
    response = client.post('/register', json={
        'username': 'adminuser2',
        'password': '123456',
        'role': 'admin',
        'admin_code': 'wrong'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 注册失败：重复管理员用户名
    response = client.post('/register', json={
        'username': 'adminuser',
        'password': 'newpass',
        'role': 'admin',
        'admin_code': '1'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    response = client.post('/register', json={
        'username': 'studentuser',
        'password': 'newpass',
        'role': 'admin',
        'admin_code': '1'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    response = client.post('/register', json={
        'username': 'teacheruser',
        'password': 'newpass',
        'role': 'admin',
        'admin_code': '1'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    #------------------------------------------------------------------
    # 测试登录功能
    # 学生登录成功
    response = client.post('/login', json={
        'username': 'studentuser',
        'password': '123456',
        'role': 'student'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

    # 老师账号以学生身份登陆
    response = client.post('/login', json={
        'username': 'teacheruser',
        'password': '123456',
        'role': 'student'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 学生登录失败：密码错误
    response = client.post('/login', json={
        'username': 'studentuser',
        'password': 'wrong',
        'role': 'student'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 学生登录失败：用户名不存在
    response = client.post('/login', json={
        'username': 'nouser',
        'password': '123456',
        'role': 'student'
    })
    assert_json_response(response, expected_success=False, expected_status=400)

    # 教师登录成功
    response = client.post('/login', json={
        'username': 'teacheruser',
        'password': '123456',
        'role': 'teacher'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

    # 管理员登录成功
    response = client.post('/login', json={
        'username': 'adminuser',
        'password': '123456',
        'role': 'admin'
    })
    assert_json_response(response, expected_success=True, expected_status=200)

