import requests
import json
import os

BASE_URL = "http://127.0.0.1:5001"

def print_response(response):
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    print(json.dumps(dict(response.headers), indent=4))
    print("Response Body:")
    print(json.dumps(response.json(), indent=4))
    print("--------------------")

def test_register(username, password):
    print("Testing Register...")
    url = f"{BASE_URL}/register"
    data = {
        "username": username,
        "password": password,
        "security_question": "What is your favorite color?",
        "security_answer": "Blue"
    }
    response = requests.post(url, json=data)
    print_response(response)
    return response.status_code == 201

def test_login(username, password):
    print("Testing Login...")
    url = f"{BASE_URL}/login"
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(url, json=data)
    print_response(response)
    if response.status_code == 200:
        return response.json().get('data', {}).get('token')
    return None

def test_upload_avatar(token, avatar_path):
    print("Testing Upload Avatar...")
    url = f"{BASE_URL}/upload/avatar"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with open(avatar_path, 'rb') as avatar_file:
            files = {'file': ('avatar.jpg', avatar_file, 'image/jpeg')}
            response = requests.post(url, headers=headers, files=files)
        print_response(response)
        return response.status_code == 200
    except FileNotFoundError:
        print(f"Avatar file not found: {avatar_path}")
        return False
    except Exception as e:
        print(f"Error uploading avatar: {str(e)}")
        return False

def test_update_user(token, username, action, **kwargs):
    print(f"Testing Update User ({action})...")
    url = f"{BASE_URL}/api/user/profile"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "username": username,
        "action": action,
        **kwargs
    }
    response = requests.put(url, json=data, headers=headers)
    print_response(response)
    return response.status_code == 200

def run_test():
    username = "4444"
    password = "testpassword123"
    new_password = "newtestpassword123"
    avatar_path = "burger.jpg"  # 请替换为实际的头像文件路径
    nickname = "Test Nickname"
    intro = "This is a test introduction"

    if not test_register(username, password):
        print("Registration failed. Exiting test.")
        return

    token = test_login(username, password)
    if not token:
        print("Login failed. Exiting test.")
        return

    if not test_upload_avatar(token, avatar_path):
        print("Avatar upload failed.")
        return

    if not test_update_user(token, username, "profile", nickname=nickname, intro=intro):
        print("Profile update failed.")
        return

    if not test_update_user(token, username, "password", oldPassword=password, newPassword=new_password):
        print("Password change failed.")
        return

    new_token = test_login(username, new_password)
    if not new_token:
        print("Login with new password failed.")
        return

    print("SUCCESS: All tests passed successfully!")

if __name__ == "__main__":
    run_test()
