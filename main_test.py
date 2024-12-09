import requests

def register_user():
    url = 'http://localhost:5001/register'
    data = {
        'username': 'test_api',
        'password': 'password123',
        'security_question': 'What is your pet\'s name?',
        'security_answer': 'Fluffy'
    }
    response = requests.post(url, json=data)
    print("Registration response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")

def login_user():
    url = 'http://localhost:5001/login'
    data = {
        'username': 'test_api',
        'password': 'password123'
    }
    response = requests.post(url, json=data)
    print("Login response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    return response.cookies

def test_user_avatars():
    cookies = login_user()
    url_update = 'http://localhost:5001/api/user/update'
    data = {
        'username': 'test_api',
        'oldPassword': 'password123',
        'newPassword': 'newpassword456',
        'confirmPassword': 'newpassword456',
        'nickname': 'UpdatedNickname'
    }
    with open('burger.jpg', 'rb') as avatar_file:
        files = {'avatar': ('burger.jpg', avatar_file, 'image/jpeg')}
        response = requests.post(url_update, data=data, files=files, cookies=cookies)

    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    updated_fields = response.json()['data']['updated_fields']
    assert 'avatar' in updated_fields, "Avatar URL not returned in update response"

    # 从更新的文件路径中提取用户名和文件名
    avatar_url = updated_fields['avatar']
    avatar_path = avatar_url.replace("http://localhost:5001", "").lstrip('/')  # 移除前导斜杠
    parts = avatar_path.split('/')

    # 确保路径格式正确
    assert len(parts) >= 3, f"Unexpected avatar path format: {avatar_path}"
    username = parts[1]
    filename = parts[2]

    # 测试访问头像文件
    test_url = f"http://localhost:5001/user_avatars/{username}/{filename}"
    response_avatar = requests.get(test_url)
    print("User Avatars response:", response_avatar.status_code)
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    assert response_avatar.status_code == 200, f"Expected 200 OK, but got {response_avatar.status_code}"


def delete_user(username):
    url = 'http://localhost:5001/api/user/delete'
    data = {'username': username}
    response = requests.post(url, json=data)
    print(f"Delete user response for {username}:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert response.json()['message'] == 'User deleted successfully', f"Failed to delete {username}"

def test_verify_security():
    url = 'http://localhost:5001/verify-security'
    
    data = {'username': 'test_api'}
    response = requests.post(url, json=data)
    print("Verify Security (Get Question) response:", response.json())
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert 'security_question' in response.json(), "Failed to fetch security question"

    data['security_answer'] = 'Fluffy'
    response = requests.post(url, json=data)
    print("Verify Security (Answer Question) response:", response.json())
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert response.json().get('verified') is True, "Security answer verification failed"
    print("----------------------------------------------------------------------------------------------------------------------------------------")

def test_logout():
    url = 'http://localhost:5001/logout'
    response = requests.get(url)
    print("Logout response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert response.json().get('message') == 'Logout successful', "Logout failed"


def test():
    register_user()
    test_user_avatars()
    test_verify_security()
    test_logout()
    delete_user('test_api')

test()