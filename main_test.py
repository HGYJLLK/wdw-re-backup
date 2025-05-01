import requests
import os
import time
import random


def register_user():
    url = "http://localhost:5001/register"
    data = {
        "username": "test_api",
        "password": "password123",
        "security_question": "What is your pet's name?",
        "security_answer": "Fluffy",
    }
    response = requests.post(url, json=data)
    print("Registration response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def login_user():
    url = "http://localhost:5001/login"
    data = {"username": "test_api", "password": "password123"}
    response = requests.post(url, json=data)
    print("Login response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )
    return response.cookies


def test_user_avatars():
    cookies = login_user()
    url_update = "http://localhost:5001/api/user/update"
    data = {
        "username": "test_api",
        "oldPassword": "password123",
        "newPassword": "newpassword456",
        "confirmPassword": "newpassword456",
        "nickname": "UpdatedNickname",
    }
    with open("burger.png", "rb") as avatar_file:
        files = {"avatar": ("burger.png", avatar_file, "image/png")}
        response = requests.post(url_update, data=data, files=files, cookies=cookies)

    assert (
        response.status_code == 200
    ), f"Expected 200 OK, but got {response.status_code}"
    updated_fields = response.json()["data"]["updated_fields"]
    assert "avatar" in updated_fields, "Avatar URL not returned in update response"

    # 从更新的文件路径中提取用户名和文件名
    avatar_url = updated_fields["avatar"]
    avatar_path = avatar_url.replace("http://localhost:5001", "").lstrip(
        "/"
    )  # 移除前导斜杠
    parts = avatar_path.split("/")
    assert len(parts) >= 3, f"Unexpected avatar path format: {avatar_path}"
    username = parts[1]
    filename = parts[2]

    # 测试访问头像文件
    test_url = f"http://localhost:5001/user_avatars/{username}/{filename}"
    response_avatar = requests.get(test_url)
    print("User Avatars response:", response_avatar.status_code)
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )
    assert (
        response_avatar.status_code == 200
    ), f"Expected 200 OK, but got {response_avatar.status_code}"


def delete_user(username):
    url = "http://localhost:5001/api/user/delete"
    data = {"username": username}
    response = requests.post(url, json=data)
    print(f"Delete user response for {username}:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_verify_security():
    url = "http://localhost:5001/verify-security"

    data = {"username": "test_api"}
    response = requests.post(url, json=data)
    print("Verify Security (Get Question) response:", response.json())
    assert (
        response.status_code == 200
    ), f"Expected 200 OK, but got {response.status_code}"
    assert "security_question" in response.json(), "Failed to fetch security question"

    data["security_answer"] = "Fluffy"
    response = requests.post(url, json=data)
    print("Verify Security (Answer Question) response:", response.json())
    assert (
        response.status_code == 200
    ), f"Expected 200 OK, but got {response.status_code}"
    assert (
        response.json().get("verified") is True
    ), "Security answer verification failed"
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def get_audio_files(directory):
    audio_extensions = [".mp3", ".wav", ".flac"]
    audio_files = []
    for filename in os.listdir(directory):
        if filename.endswith(tuple(audio_extensions)):
            audio_files.append(filename)

    return audio_files


def test_upload_audio():
    url = "http://localhost:5001/upload/audio"
    # 检索本地文件夹中的音频文件
    files = get_audio_files("./static/music")
    username = "test_api"
    is_self = True
    playlist_type = 1

    # 文件数据，files 中的每个元素是一个文件对象
    files_data = []
    total_size = 0
    file_objects = []  # 保存文件对象的列表

    for file in files:
        # 构建完整的文件路径
        file_path = os.path.join("./static/music", file)

        try:
            file_obj = open(file_path, "rb")
            file_objects.append(file_obj)  # 保存文件对象

            # 获取文件大小
            file_obj.seek(0, os.SEEK_END)
            file_size = file_obj.tell()
            file_obj.seek(0)
            total_size += file_size

            files_data.append(("audio_files", (file, file_obj)))
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            continue

    # 数据
    data = {"username": username, "is_self": is_self, "playlist_type": playlist_type}

    print(f"Total file size to upload: {total_size / (1024*1024):.2f} MB")
    response = requests.post(url, data=data, files=files_data)
    print("Upload Audio response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )

    # 关闭所有打开的文件
    for file_obj in file_objects:
        file_obj.close()

    # 上传单个音频文件，测试file_size字段
    file_path = "./a1.mp3"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0)
            print(f"Uploading single file with size: {file_size / (1024*1024):.2f} MB")

            files_data = [("audio_files", (os.path.basename(file_path), f))]
            data = {
                "username": username,
                "is_self": is_self,
                "playlist_type": playlist_type,
                "artist": "Test Artist",  # 添加歌手名
            }
            response = requests.post(url, data=data, files=files_data)
            print("Upload one Audio response:", response.json())
            print(
                "----------------------------------------------------------------------------------------------------------------------------------------"
            )


def test_logout():
    url = "http://localhost:5001/logout"
    response = requests.get(url)
    print("Logout response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )
    assert (
        response.status_code == 200
    ), f"Expected 200 OK, but got {response.status_code}"
    assert response.json().get("message") == "Logout successful", "Logout failed"


def test_delete_user_data():
    url = "http://localhost:5001/api/user/delete-data"
    data = {"username": "test_api"}
    response = requests.post(url, json=data)
    print("Delete User Data response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_get_audio():
    url = "http://localhost:5001/api/audio/id"
    response = requests.get(url)
    print("Get Audio response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_add_to_playlist():
    url = "http://localhost:5001/api/playlist/add"
    # 添加自定义音频
    data = {
        "username": "test_api",
        "playlist_type": 2,
        "song_name": "Love with You",
        "is_self": True,
        "music_id": str(int(time.time()))
        + str(random.randint(1000, 9999)),  # 添加随机music_id
        "file_size": 1024 * 1024,  # 添加文件大小 1MB
    }

    response = requests.post(url, json=data)
    print("Add to myself Playlist response:", response.json())

    # 添加api音频
    data = {
        "username": "test_api",
        "playlist_type": 2,
        "song_name": "極私的極彩色アンサー",
        "artist": "トゲナシトゲアリ",
        "duration": 155006,
        "music_id": "1394111226",
        "pic_url": "https://p2.music.126.net/FaNFmGKiQEB5mMmWeDqLhQ==/109951170209243099.jpg",
        "song_size": 2 * 1024 * 1024,  # 添加文件大小 2MB
    }

    response = requests.post(url, json=data)
    print("Add to api Playlist response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_delete_user_songs(music_id):
    url = "http://localhost:5001/api/user/songs/delete"
    data = {"username": "test_api", "playlist_type": 2, "music_id": music_id}

    response = requests.post(url, json=data)
    print("Delete User Songs response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_music_status():
    url = "http://localhost:5001/api/music/status"
    params = {"id": "1394111226"}  # 使用已知的API音乐ID
    response = requests.get(url, params=params)
    print("Music Status response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def test_disabled_music():
    url = "http://localhost:5001/api/disabled-music"
    response = requests.get(url)
    print("Disabled Music response:", response.json())
    print(
        "----------------------------------------------------------------------------------------------------------------------------------------"
    )


def util_get_music_id():
    url = "http://localhost:5001/api/audio/search"
    response = requests.get(url)
    print("Get Music ID response:", response.json())
    return response.json()["data"][0]["music_id"]


def test():
    import time
    import random

    username = "test_api"

    # 检查用户是否存在
    url_check = "http://localhost:5001/api/user/exist"
    data_check = {"username": username}
    response_check = requests.post(url_check, json=data_check)

    if response_check.status_code == 400:  # 用户已存在
        test_delete_user_data()
        delete_user("test_api")

    register_user()
    test_user_avatars()
    test_verify_security()
    test_upload_audio()
    test_get_audio()
    test_add_to_playlist()
    test_music_status()
    test_disabled_music()

    try:
        music_id = util_get_music_id()
        test_delete_user_songs(music_id)
    except:
        print("Warning: Could not get music ID for deletion test")

    test_logout()
    test_delete_user_data()
    delete_user("test_api")


test()
