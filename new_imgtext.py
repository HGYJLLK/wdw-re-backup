import requests


# Registration
def register_user():
    url = 'http://localhost:5001/register'
    data = {
        'username': 'testuser1231231',
        'password': 'password123',
        'security_question': 'What is your pet\'s name?',
        'security_answer': 'Fluffy'
    }
    response = requests.post(url, json=data)
    print("Registration response:", response.json())


# Login
def login_user():
    url = 'http://localhost:5001/login'
    data = {
        'username': 'testuser1231231',
        'password': 'password123'
    }
    response = requests.post(url, json=data)
    print("Login response:", response.json())
    return response.cookies  # Assuming the server sets cookies for session management


# Update User
def update_user(cookies):
    url = 'http://localhost:5001/api/user/update'
    # Data to update
    data = {
        'username': 'testuser123',  # Ensure the username matches what was registered
        'nickname': 'NewNickname',
        'intro': 'Updated intro text.',
        'oldPassword': 'password123',
        'newPassword': 'newpassword456',
        'confirmPassword': 'newpassword456',
    }
    # If you want to upload an avatar, you'd include a file
    # Adjust the path to the image you want to upload
    files = {
        'avatar': ('avatar.jpg', open('burger.jpg', 'rb'), 'image/jpeg')  # Ensure the file exists at this path
    }

    response = requests.post(url, data=data, files=files, cookies=cookies)
    print("Update response:", response.json())

    # You can assert if needed (e.g., checking for success code, profile updates, etc.)
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    assert 'avatar' in response.json()['data']['updated_fields'], "Avatar update failed"
    assert response.json()['data']['profile_updated'] is True, "Profile update failed"


# Main test function
def test():
    # First, register and login
    register_user()
    cookies = login_user()  # Store cookies returned after login

    # Now update the user data
    update_user(cookies)


test()
