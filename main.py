from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import logging
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database configuration
DB_CONFIG = {
    'host': '47.119.119.114',
    'user': 'root',
    # 'password': '2333',
    'password': 'your_password',
    'port': 3306,
    'database': 'user_auth'
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file):
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = secure_filename(file.filename)
        filename = f"{timestamp}_{original_filename}"

        # 保存文件
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # 返回文件URL
        return f"/uploads/avatars/{filename}"
    return None


class DatabaseManager:
    @staticmethod
    def get_connection():
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    @staticmethod
    def execute_query(query, params=None, fetch=False):
        conn = None
        cursor = None
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount

            return result
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class UserService:
    @staticmethod
    def create_user(username, password, security_question, security_answer):
        query = """
            INSERT INTO users (username, password, security_question, security_answer)
            VALUES (%s, %s, %s, %s)
        """
        params = (username, password, security_question, security_answer)
        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def get_user_by_username(username):
        query = "SELECT * FROM users WHERE username = %s"
        params = (username,)
        result = DatabaseManager.execute_query(query, params, fetch=True)
        return result[0] if result else None

    @staticmethod
    def update_password(username, new_password):
        query = "UPDATE users SET password = %s WHERE username = %s"
        params = (new_password, username)
        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def update_avatar(username, avatar_url):
        query = "UPDATE users SET avatar_url = %s WHERE username = %s"
        params = (avatar_url, username)
        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def update_user_profile(username, nickname, intro):
        query = "UPDATE users SET nickname = %s, intro = %s WHERE username = %s"
        params = (nickname, intro, username)
        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def update_password(username, old_password, new_password):
        # 首先验证旧密码
        user = UserService.get_user_by_username(username)
        if not user or user['password'] != old_password:
            return None
        
        query = "UPDATE users SET password = %s WHERE username = %s"
        params = (new_password, username)
        return DatabaseManager.execute_query(query, params)



    


@app.route('/uploads/avatars/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/upload/avatar', methods=['POST'])
def upload_avatar():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # 从请求头获取用户名
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.split(' ')[1]
        username = token.split('_')[0]

        # 保存文件
        file_url = save_file(file)
        if not file_url:
            return jsonify({'error': 'Failed to save file'}), 500

        # 更新数据库
        result = UserService.update_avatar(username, file_url)
        if result is None:
            return jsonify({'error': 'Failed to update avatar'}), 500

        return jsonify({
            'code': 200,
            'message': '头像上传成功',
            'data': {
                'url': file_url
            }
        })

    except Exception as e:
        logger.error(f"Upload avatar error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        security_question = data.get('security_question')
        security_answer = data.get('security_answer')

        # Validate input
        if not all([username, password, security_question, security_answer]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if username already exists
        existing_user = UserService.get_user_by_username(username)
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409

        # Create new user
        result = UserService.create_user(username, password, security_question, security_answer)
        if result is not None:
            return jsonify({'message': 'User registered successfully'}), 201
        else:
            return jsonify({'error': 'Registration failed'}), 500

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return jsonify({'error': 'Missing credentials'}), 400

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user['password'] != password:
            return jsonify({'error': 'Invalid password'}), 401

        # 检查user字典中是否存在所有必要的键
        required_keys = ['username', 'nickname', 'avatar_url', 'intro', 'security_question']
        for key in required_keys:
            if key not in user:
                user[key] = ''  # 如果键不存在，设置一个默认值

        return jsonify({
            'code': 200,
            'message': 'Login successful',
            'data': {
                'token': f"{username}_token",
                'userInfo': {
                    'username': user['username'],
                    'nickname': user.get('nickname') or user['username'],
                    'avatarUrl': user.get('avatar_url') or '',
                    'intro': user.get('intro') or '',
                    'security_question': user.get('security_question') or ''
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500



@app.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        username = data.get('username')
        new_password = data.get('new_password')

        # Validate input
        if not all([username, new_password]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Get user
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update password
        result = UserService.update_password(username, new_password)
        if result is not None:
            return jsonify({'message': 'Password reset successful'}), 200
        else:
            return jsonify({'error': 'Password reset failed'}), 500

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/verify-security', methods=['POST'])
def verify_security():
    try:
        data = request.get_json()
        username = data.get('username')
        security_answer = data.get('security_answer')

        # Get user and return security question
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 如果没有提供security_answer,说明只是获取密保问题
        if not security_answer:
            return jsonify({
                'security_question': user['security_question']
            }), 200

        # 如果提供了security_answer,则验证答案
        if user['security_answer'] != security_answer:
            return jsonify({'error': 'Invalid security answer'}), 401

        return jsonify({
            'message': 'Security answer verified',
            'verified': True
        }), 200

    except Exception as e:
        logger.error(f"Security verification error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/logout', methods=['GET'])
def logout():
    try:
        return jsonify({
            'code': 200,
            'message': 'Logout successful'
        })
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500



@app.route('/api/user/profile', methods=['PUT'])
def update_user():
    try:
        data = request.get_json()
        username = data.get('username')
        action = data.get('action')

        if not username or not action:
            return jsonify({'error': 'Missing required fields'}), 400

        if action == 'profile':
            nickname = data.get('nickname')
            intro = data.get('intro')

            if not nickname:
                return jsonify({'error': 'Missing required fields'}), 400

            result = UserService.update_user_profile(username, nickname, intro)
            if result is not None:
                return jsonify({'message': 'Profile updated successfully'}), 200
            else:
                return jsonify({'error': 'Profile update failed'}), 500

        elif action == 'password':
            old_password = data.get('oldPassword')
            new_password = data.get('newPassword')

            if not old_password or not new_password:
                return jsonify({'error': 'Missing required fields'}), 400

            result = UserService.update_password(username, old_password, new_password)
            if result is not None:
                return jsonify({'message': 'Password changed successfully'}), 200
            else:
                return jsonify({'error': 'Password change failed'}), 401

        else:
            return jsonify({'error': 'Invalid action'}), 400

    except Exception as e:
        logger.error(f"User update error: {e}")
        return jsonify({'error': 'Internal server error'}), 500





if __name__ == '__main__':
    app.run(debug=True, port=5001)
