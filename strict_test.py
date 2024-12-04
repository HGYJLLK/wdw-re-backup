import requests
import json
import os
import mysql.connector
from datetime import datetime
import hashlib

BASE_URL = "http://127.0.0.1:5001"
UPLOAD_FOLDER = 'uploads/avatars'

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'user_auth',
    'port': 3306
}


def get_file_hash(filepath):
    """获取文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def verify_db_data(username, expected_data):
    """验证数据库中的数据是否符合预期"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user_data:
            print(f"❌ User {username} not found in database")
            return False

        # 验证每个期望的字段
        for key, value in expected_data.items():
            if key in user_data and user_data[key] != value:
                print(f"❌ Database verification failed for {key}")
                print(f"Expected: {value}")
                print(f"Got: {user_data[key]}")
                return False
        return True
    except Exception as e:
        print(f"❌ Database verification error: {e}")
        return False


def verify_avatar_file(avatar_url):
    """验证头像文件是否存在且可访问"""
    if not avatar_url:
        return False

    file_path = os.path.join(os.getcwd(), avatar_url.lstrip('/'))
    if not os.path.exists(file_path):
        print(f"❌ Avatar file not found at {file_path}")
        return False

    return True


def print_response(response):
    """打印响应信息用于调试"""
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    print(json.dumps(dict(response.headers), indent=4))
    print("Response Body:")
    try:
        print(json.dumps(response.json(), indent=4))
    except:
        print(response.text)
    print("--------------------")


def test_register(username, password):
    """测试用户注册"""
    print("\nTesting Register...")
    url = f"{BASE_URL}/register"
    data = {
        "username": username,
        "password": password,
        "security_question": "What is your favorite color?",
        "security_answer": "Blue"
    }
    response = requests.post(url, json=data)
    print_response(response)

    if response.status_code != 201:
        return False

    # 验证数据库中是否正确创建了用户
    expected_data = {
        "username": username,
        "password": password,
        "security_question": "What is your favorite color?",
        "security_answer": "Blue"
    }
    return verify_db_data(username, expected_data)


def test_avatar_upload(token, username, avatar_path):
    """测试头像上传"""
    print("\nTesting Avatar Upload...")
    url = f"{BASE_URL}/upload/avatar"
    headers = {"Authorization": f"Bearer {token}"}

    # 记录上传前的头像文件（如果有）
    old_avatar = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT avatar_url FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result and result['avatar_url']:
            old_avatar = os.path.join(os.getcwd(), result['avatar_url'].lstrip('/'))
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database query error: {e}")
        return False

    # 记录原始文件的哈希值
    original_hash = get_file_hash(avatar_path)

    # 上传新头像
    try:
        with open(avatar_path, 'rb') as avatar_file:
            files = {'file': ('avatar.jpg', avatar_file, 'image/jpeg')}
            response = requests.post(url, headers=headers, files=files)
        print_response(response)

        if response.status_code != 200:
            return False

        # 获取新头像URL
        new_avatar_url = response.json().get('data', {}).get('url')
        if not new_avatar_url:
            print("❌ No avatar URL in response")
            return False

        # 验证新头像文件是否存在
        if not verify_avatar_file(new_avatar_url):
            return False

        # 验证新头像文件的哈希值
        new_file_path = os.path.join(os.getcwd(), new_avatar_url.lstrip('/'))
        new_hash = get_file_hash(new_file_path)
        if original_hash != new_hash:
            print("❌ Uploaded file does not match original file")
            return False

        # 验证旧头像是否被删除（如果存在）
        if old_avatar and os.path.exists(old_avatar):
            print("❌ Old avatar file not deleted")
            return False

        # 验证数据库是否更新了头像URL
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT avatar_url FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result or result['avatar_url'] != new_avatar_url:
                print("❌ Database avatar_url not updated correctly")
                return False
        except Exception as e:
            print(f"❌ Database verification error: {e}")
            return False

        return True
    except Exception as e:
        print(f"❌ Avatar upload error: {e}")
        return False


def test_profile_update(token, username, update_data):
    """测试更新用户资料"""
    print("\nTesting Profile Update...")
    url = f"{BASE_URL}/api/user/profile"
    headers = {"Authorization": f"Bearer {token}"}

    # 记录更新前的数据
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        old_data = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database query error: {e}")
        return False

    # 发送更新请求
    update_data['username'] = username
    response = requests.put(url, json=update_data, headers=headers)
    print_response(response)

    if response.status_code != 200:
        return False

    # 验证数据库中的更新
    expected_data = {k: v for k, v in update_data.items() if k != 'oldPassword'}
    if 'newPassword' in update_data:
        expected_data['password'] = update_data['newPassword']
        del expected_data['newPassword']

    return verify_db_data(username, expected_data)


def run_strict_test():
    """运行严格的测试流程"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    username = f"test_user_{timestamp}"
    password = "testpassword123"
    avatar_path = "burger.jpg"

    print("\n=== Starting Strict Test ===")

    # 确保测试文件存在
    if not os.path.exists(avatar_path):
        print(f"❌ Test avatar file not found: {avatar_path}")
        return

    # 1. 注册测试
    if not test_register(username, password):
        print("❌ Registration verification failed")
        return

    # 2. 登录测试
    print("\nTesting Login...")
    response = requests.post(f"{BASE_URL}/login", json={
        "username": username,
        "password": password
    })
    if response.status_code != 200:
        print("❌ Login failed")
        return
    token = response.json().get('data', {}).get('token')

    # 3. 头像上传测试
    if not test_avatar_upload(token, username, avatar_path):
        print("❌ Avatar upload verification failed")
        return

    # 4. 资料更新测试
    new_nickname = f"Tester_{timestamp}"
    new_intro = f"Test intro {timestamp}"
    if not test_profile_update(token, username, {
        "nickname": new_nickname,
        "intro": new_intro
    }):
        print("❌ Profile update verification failed")
        return

    # 5. 密码更新测试
    if not test_profile_update(token, username, {
        "oldPassword": password,
        "newPassword": "newpassword123"
    }):
        print("❌ Password update verification failed")
        return

    print("\n✅ SUCCESS: All strict tests passed successfully!")
    print("All data verified in database and file system")


if __name__ == "__main__":
    run_strict_test()