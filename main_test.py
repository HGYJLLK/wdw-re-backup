import requests
import os

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
    # assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    # assert response.json()['message'] == 'User deleted successfully', f"Failed to delete {username}"

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

def get_audio_files(directory):
    audio_extensions = ['.mp3', '.wav', '.flac']
    audio_files=[]
    for filename in os.listdir(directory):
        if filename.endswith(tuple(audio_extensions)):
            audio_files.append(filename)
    
    return audio_files

def test_upload_audio():
    url = 'http://localhost:5001/upload/audio'
    # 检索本地文件夹中的音频文件
    files = get_audio_files('./static/music')
    username = 'test_api'
    is_self = True
    playlist_type = 1

    # 准备文件数据，确保 files 中的每个元素是一个文件对象
    files_data = []
    for file in files:
         # 构建完整的文件路径
        file_path = os.path.join('./static/music', file)
        
        try:
            # 使用打开文件的路径
            files_data.append(('audio_files', (file, open(file_path, 'rb'))))
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            continue

    # 准备其他数据
    data = {
        'username': username,
        'is_self': is_self,
        'playlist_type': playlist_type
    }

    response = requests.post(url, data=data, files=files_data)
    print("Upload Audio response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    # 上传音频文件
    file_path = './a1.mp3'
    username = 'test_api'
    is_self = True
    playlist_type = 1
    files_data = [('audio_files', (file_path, open(file_path, 'rb')))]
    data = {
        'username': username,
        'is_self': is_self,
        'playlist_type': playlist_type
    }
    response = requests.post(url, data=data, files=files_data)
    print("Upload one Audio response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")

def test_logout():
    url = 'http://localhost:5001/logout'
    response = requests.get(url)
    print("Logout response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert response.json().get('message') == 'Logout successful', "Logout failed"

def test_delete_user_data():
    url = 'http://localhost:5001/api/user/delete-data'
    data = {'username': 'test_api'}
    response = requests.post(url, json=data)
    print("Delete User Data response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")

def test_get_audio():
    url = 'http://localhost:5001/api/audio/id'
    response = requests.get(url)
    print("Get Audio response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")

# def test_get_usernames():
#     url = 'http://localhost:5001/api/user/exist'
#     data = {'username': 'test_api'}
#     response = requests.post(url, json=data)
#     print("Get Usernames response:", response.json())
#     '''
#     if user_exist:
#         return jsonify({'message': 'Username already exists'}), 400
#     else:
#         return jsonify({'message': 'Username is available'}), 200
#     '''
#     # 如果返回400，则用户名已存在；如果返回200，则用户名可用
#     assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
#     assert response.json().get('message') == 'Username is available', "Failed to check username availability"
#     print("----------------------------------------------------------------------------------------------------------------------------------------")

def test_add_to_playlist():
    url = 'http://localhost:5001/api/playlist/add'
    # 添加自定义音频
    data = {
        'username': 'test_api',
        'playlist_type': 2,
        'song_name' : 'Love with You',
        'is_self' : True,
        }
    
    response = requests.post(url, json=data)
    print("Add to myself Playlist response:", response.json())
    
    # 添加api音频
    data = {
        'username': 'test_api',
        'playlist_type': 2,
        'song_name' : '極私的極彩色アンサー',
        'artist': 'トゲナシトゲアリ',
        'duration': 155006,
        'pic_url':'https://p2.music.126.net/FaNFmGKiQEB5mMmWeDqLhQ==/109951170209243099.jpg'
        }
    
    response = requests.post(url, json=data)
    print("Add to api Playlist response:", response.json())
    print("----------------------------------------------------------------------------------------------------------------------------------------")

def test():
    username = 'test_api'
    
    # 检查用户是否存在
    url_check = 'http://localhost:5001/api/user/exist'
    data_check = {'username': username}
    response_check = requests.post(url_check, json=data_check)
    
    if response_check.status_code == 400:  # 用户已存在
        test_delete_user_data()
        delete_user('test_api')

    register_user()
    test_user_avatars()
    # test_verify_security()
    test_upload_audio()
    test_get_audio()
    test_add_to_playlist()
    test_logout()
    test_delete_user_data()
    delete_user('test_api')

test()