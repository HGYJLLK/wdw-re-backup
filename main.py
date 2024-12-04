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

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',  # 使用本地数据库
    'user': 'root',
    'password': '',  # 替换为你的密码
    'database': 'user_auth',
    'port': 3306
}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            filename = f"{timestamp}_{original_filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 保存文件
            file.save(file_path)

            # 返回相对URL路径
            return f"/uploads/avatars/{filename}"
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return None
    return None


class DatabaseManager:
    @staticmethod
    def get_connection():
        """获取数据库连接"""
        try:
            logger.info("Attempting to connect to database...")
            conn = mysql.connector.connect(**DB_CONFIG)
            logger.info("Database connection successful")
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    @staticmethod
    def execute_query(query, params=None, fetch=False):
        """执行数据库查询"""
        conn = None
        cursor = None
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor(dictionary=True)
            logger.info(f"Executing query: {query} with params: {params}")
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall()
                logger.info(f"Query returned {len(result)} results")
            else:
                conn.commit()
                result = cursor.rowcount
                logger.info(f"Query affected {result} rows")
            return result

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class UserService:
    @staticmethod
    def create_user(username, password, security_question, security_answer):
        """创建新用户"""
        try:
            # 先检查用户是否已存在
            existing_user = UserService.get_user_by_username(username)
            if existing_user:
                logger.error(f"Username {username} already exists")
                return None

            query = """
                INSERT INTO users (username, password, security_question, security_answer)
                VALUES (%s, %s, %s, %s)
            """
            params = (username, password, security_question, security_answer)
            return DatabaseManager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    @staticmethod
    def get_user_by_username(username):
        """通过用户名获取用户信息"""
        try:
            query = "SELECT * FROM users WHERE username = %s"
            params = (username,)
            result = DatabaseManager.execute_query(query, params, fetch=True)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    @staticmethod
    def update_user_profile(username, nickname=None, intro=None):
        """更新用户资料"""
        try:
            updates = []
            params = []

            if nickname is not None:
                updates.append("nickname = %s")
                params.append(nickname)

            if intro is not None:
                updates.append("intro = %s")
                params.append(intro)

            if not updates:
                return True  # 没有要更新的内容，视为成功

            query = f"UPDATE users SET {', '.join(updates)} WHERE username = %s"
            params.append(username)

            return DatabaseManager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return None

    @staticmethod
    def update_password(username, old_password, new_password):
        """更新密码"""
        try:
            user = UserService.get_user_by_username(username)
            if not user or user['password'] != old_password:
                return None

            query = "UPDATE users SET password = %s WHERE username = %s"
            params = (new_password, username)
            return DatabaseManager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return None

    @staticmethod
    def update_avatar(username, avatar_url):
        """更新头像"""
        try:
            query = "UPDATE users SET avatar_url = %s WHERE username = %s"
            params = (avatar_url, username)
            return DatabaseManager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating avatar: {e}")
            return None

@app.route('/uploads/avatars/<filename>')
def uploaded_file(filename):
    """获取上传的文件"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        security_question = data.get('security_question')
        security_answer = data.get('security_answer')

        logger.info(f"Attempting to register user: {username}")

        # 校验输入
        if not all([username, password, security_question, security_answer]):
            logger.error("Missing required registration fields")
            return jsonify({'error': 'Missing required fields'}), 400

        # 创建新用户
        result = UserService.create_user(username, password, security_question, security_answer)
        if result is not None:
            logger.info(f"Successfully registered user: {username}")
            return jsonify({'message': 'User registered successfully'}), 201
        else:
            logger.error("Failed to create user")
            return jsonify({'error': 'Registration failed'}), 500

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500


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

        # 生成简单的 token
        token = f"Bearer_{username}"  # 简化 token 格式

        user_info = {
            'username': user['username'],
            'nickname': user.get('nickname', user['username']),
            'avatarUrl': user.get('avatar_url', ''),
            'intro': user.get('intro', ''),
            'security_question': user.get('security_question', '')
        }

        return jsonify({
            'code': 200,
            'message': 'Login successful',
            'data': {
                'token': token,
                'userInfo': user_info
            }
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/profile', methods=['PUT'])
def update_user():
    """更新用户信息接口"""
    try:
        data = request.get_json()
        username = data.get('username')

        if not username:
            return jsonify({'error': 'Username is required'}), 400

        # 获取当前用户信息
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        updates = {}
        update_made = False

        # 更新昵称
        if 'nickname' in data:
            updates['nickname'] = data['nickname']
            update_made = True

        # 更新简介
        if 'intro' in data:
            updates['intro'] = data['intro']
            update_made = True

        # 如果有需要更新的基本信息
        if update_made:
            profile_result = UserService.update_user_profile(username, updates.get('nickname'), updates.get('intro'))
            if profile_result is None:
                return jsonify({'error': 'Failed to update profile'}), 500

        # 更新密码（如果提供）
        password_updated = False
        if data.get('oldPassword') and data.get('newPassword'):
            password_result = UserService.update_password(username, data['oldPassword'], data['newPassword'])
            if password_result is None:
                return jsonify({'error': 'Failed to update password'}), 401
            password_updated = True

        return jsonify({
            'code': 200,
            'message': 'Update successful',
            'data': {
                'profile_updated': update_made,
                'password_updated': password_updated
            }
        })

    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({'error': str(e)}), 500


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

        # 简化的 token 解析
        username = auth_header.split('Bearer_')[1]  # 直接获取用户名部分

        # 获取用户信息
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 保存新头像
        file_url = save_file(file)
        if not file_url:
            return jsonify({'error': 'Failed to save file'}), 500

        # 更新数据库中的头像URL
        result = UserService.update_avatar(username, file_url)
        if result is None:
            return jsonify({'error': 'Failed to update avatar in database'}), 500

        return jsonify({
            'code': 200,
            'message': '头像上传成功',
            'data': {'url': file_url}
        })

    except Exception as e:
        logger.error(f"Upload avatar error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/verify-security', methods=['POST'])
def verify_security():
    """验证安全问题"""
    try:
        data = request.get_json()
        username = data.get('username')
        security_answer = data.get('security_answer')

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not security_answer:
            return jsonify({
                'security_question': user['security_question']
            }), 200

        if user['security_answer'] != security_answer:
            return jsonify({'error': 'Invalid security answer'}), 401

        return jsonify({
            'message': 'Security answer verified',
            'verified': True
        }), 200

    except Exception as e:
        logger.error(f"Security verification error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)