# pip install flask flask-cors mysql-connector-python pydub
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import logging
import os
from werkzeug.utils import secure_filename
# 获取音频时长
from pydub.utils import mediainfo

app = Flask(__name__)
CORS(app)

# 配置上传文件夹
UPLOAD_FOLDER = 'user_avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_AUDIO_FOLDER = 'static/audio'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac'}

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(UPLOAD_AUDIO_FOLDER):
    os.makedirs(UPLOAD_AUDIO_FOLDER)

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',  # 使用本地数据库
    'user': 'root',
    'password': '123qweQWE!',  # 替换为你的密码
    # 'password': 'loveat2024a+.',
    # 'password': '',
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


def allowed_audio_file(filename):
    """检查音频文件类型是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS


def save_file(file, folder, filename):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(folder, filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 保存文件
            file.save(file_path)

            # 返回相对URL路径
            return f"/{folder}/{filename}"
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return None
    return None

def save_audio_file(file, username):
    """保存上传的音频文件"""
    if file and allowed_audio_file(file.filename):
        try:
            original_filename = secure_filename(file.filename)
            user_folder = os.path.join(UPLOAD_AUDIO_FOLDER, username)
            file_path = os.path.join(user_folder, original_filename)

            # 确保用户目录存在
            os.makedirs(user_folder, exist_ok=True)

            # 如果文件已存在，则跳过保存
            if os.path.exists(file_path):
                logger.info(f"File {original_filename} already exists for user {username}. Skipping save.")
                return None, None

            # 保存文件
            file.save(file_path)
            return file_path, original_filename
        except Exception as e:
            logger.error(f"Error saving audio file for user {username}: {e}")
            return None, None
    return None, None

def get_audio_duration(file_path):
    """获取音频时长（毫秒）"""
    try:
        info = mediainfo(file_path)
        duration = float(info['duration']) * 1000  # 转换为毫秒
        return int(duration)
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
        return 0


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
                return True

            query = f"UPDATE users SET {', '.join(updates)} WHERE username = %s"
            params.append(username)

            return DatabaseManager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return None

    @staticmethod
    def update_password(username, new_password, old_password=None):
        """
        更新密码，兼容直接重置密码和验证旧密码的更新操作。
        :param username: 用户名
        :param new_password: 新密码
        :param old_password: 旧密码（可选）
        :return: 更新结果
        """
        try:
            user = UserService.get_user_by_username(username)
            if not user:
                return None

            # 如果提供了旧密码，则验证旧密码
            if old_password and user['password'] != old_password:
                return None

            # 更新密码
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
    
    @staticmethod
    def delete_user_from_db(username):
        """从数据库中删除用户"""
        try:
            # 确保用户存在
            user = UserService.get_user_by_username(username)
            if not user:
                logger.error(f"User {username} not found")
                return False

            # 删除用户
            query = "DELETE FROM users WHERE username = %s"
            params = (username,)
            result = DatabaseManager.execute_query(query, params)
            if result:
                logger.info(f"User {username} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete user {username}")
                return False
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}")
            return False

@app.route('/user_avatars/<username>/<filename>')
def uploaded_file(username, filename):
    """根据用户名获取头像"""
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    try:
        return send_from_directory(user_folder, filename)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


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

         # 构建头像 HTTP 链接
        avatar_url = user.get('avatar_url', '')
        if avatar_url:
            avatar_url = f"http://localhost:5001/user_avatars/{username}/{os.path.basename(avatar_url)}"

        user_info = {
            'username': user['username'],
            'nickname': user.get('nickname', user['username']),
            'avatar': avatar_url,  # 返回完整的头像 HTTP 链接
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


@app.route('/api/user/update', methods=['POST'])
def update_user():
    """更新用户信息和密码接口"""
    try:
        data = request.form.to_dict()  # 支持表单数据（包括文件）
        username = data.get('username')

        if not username:
            return jsonify({'error': 'Username is required'}), 400

        # 获取当前用户信息
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 初始化更新状态
        profile_updated = False
        password_updated = False
        updates = {}

        # 更新基本信息
        if 'nickname' in data:
            updates['nickname'] = data['nickname']
        if 'intro' in data:
            updates['intro'] = data['intro']

        if updates:
            profile_result = UserService.update_user_profile(username, updates.get('nickname'), updates.get('intro'))
            if profile_result is None:
                return jsonify({'error': 'Failed to update profile'}), 500
            profile_updated = True

        # 更新头像（文件上传）
        if 'avatar' in request.files:
            file = request.files['avatar']
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type'}), 400

            # 头像文件名与用户名关联（用用户名作为文件名的一部分）
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            avatar_filename = f"{username}_avatar.{file_extension}"

            # 保存文件（文件路径与用户名相关联，存储到用户文件夹下）
            file_url = save_file(file, folder=f"user_avatars/{username}", filename=avatar_filename)
            if not file_url:
                return jsonify({'error': 'Failed to save avatar'}), 500

            # 将头像的 URL 转换为完整的 HTTP 链接
            full_avatar_url = f"http://localhost:5001{file_url}"

            # # 将头像的 URL 更新到用户信息中
            avatar_result = UserService.update_avatar(username, full_avatar_url)
            if avatar_result is None:
                return jsonify({'error': 'Failed to update avatar'}), 500
            updates['avatar'] = full_avatar_url
            profile_updated = True

        # 更新密码
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')

        if old_password or new_password or confirm_password:
            if not old_password or not new_password or not confirm_password:
                return jsonify({'error': 'All password fields are required'}), 400
            if new_password != confirm_password:
                return jsonify({'error': 'New password and confirmation do not match'}), 400

            password_result = UserService.update_password(username, new_password,old_password)
            if password_result is None:
                return jsonify({'error': 'Failed to update password'}), 401
            password_updated = True

        return jsonify({
            'code': 200,
            'message': 'Update successful',
            'data': {
                'profile_updated': profile_updated,
                'password_updated': password_updated,
                'updated_fields': updates
            }
        })

    except Exception as e:
        logger.error(f"Update user error: {e}")
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


@app.route('/upload/audio', methods=['POST'])
def upload_audio():
    try:
        username = request.form.get('username')
        files = request.files.getlist('audio_files') or []
        is_self = request.form.get('is_self')

        # 歌手名
        artist = request.form.get('artist') or '未知歌手'
        song_name = request.form.get('song_name') or ''
        # 歌单，云歌单：1，本地歌单：2，喜欢的歌单：3
        playlist_type = request.form.get('playlist_type')
        pic_url = request.form.get('pic_url') or 'burger.jpg'

        if not username:
            return jsonify({'error': 'Missing username'}), 400

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_id = user['id']

        for file in files:
            if not allowed_audio_file(file.filename):
                continue

            # 检查是否存在同名文件
            query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s AND playlist_type = %s"
            params = (user_id, file.filename, playlist_type)
            existing_files = DatabaseManager.execute_query(query, params, fetch=True)

            if existing_files:
                logger.info(f"User {username} already has a file named {file.filename}. Skipping save.")
                continue

            # 保存音频文件
            file_path, filename = save_audio_file(file, username)
            if not file_path:
                continue

            # 获取音频时长
            duration = get_audio_duration(file_path)

            # 生成唯一音频id，当前时间戳 + 随机数
            musics_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

            # 保存到数据库
            query = """
                INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)
            """
            params = (user_id, filename, duration, file_path, artist, playlist_type,pic_url,is_self,musics_id)
            DatabaseManager.execute_query(query, params)

        # 如果files数组为空和存在歌名和is_self为true，在云歌单查找这首歌的music_id，复制一份数据，并且更改playlist_type为playlist_type
        if not files and song_name and is_self == 'true':
            query = "SELECT * FROM audio_files WHERE song_name = %s AND playlist_type = 1"
            params = (song_name,)
            existing_files = DatabaseManager.execute_query(query, params, fetch=True)
            if existing_files:
                music_id = existing_files[0]['music_id']
                query = """
                    INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
                    VALUES (%s, %s, %s,%s)
                """
                params = (user_id, existing_files[0]['filename'], existing_files[0]['duration'], existing_files[0]['file_path'], artist, playlist_type,pic_url,is_self,music_id)
                DatabaseManager.execute_query(query, params)
                

        return jsonify({'message': 'Audio files processed successfully'}), 200

    except Exception as e:
        logger.error(f"Error uploading audio files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/audio', methods=['GET'])
def get_audio():
    """根据音频ID生成音频链接"""
    try:
        audio_id = request.args.get('id')
        # conn = DatabaseManager.get_connection()
        # cursor = conn.cursor(dictionary=True)
        query = "SELECT file_path FROM audio_files WHERE id = %s"
        # cursor.execute(query, (audio_id,))
        # result = cursor.fetchone()
        # cursor.close()
        # conn.close()

        result = DatabaseManager.execute_query(query, (audio_id,), fetch=True)

        if not result:
            return jsonify({'error': 'Audio not found'}), 404

        # 获取文件路径
        file_path = result[0]['file_path']

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on server'}), 404

        # 构建完整的 HTTP URL
        host = request.host_url.rstrip('/')  # 获取主机地址
        file_url = f"{host}/static/{os.path.relpath(file_path, start='static')}"

        return jsonify({'musicUrl': file_url}), 200
    except Exception as e:
        logger.error(f"Error fetching audio file URL: {e}")
        return jsonify({'error': str(e)}), 500

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

# 根据用户、歌单获取歌曲
@app.route('/api/user/songs', methods=['GET'])
def get_user_songs():
    try:
        username = request.args.get('username')
        # 云歌单：1 本地歌单：2 我的最爱歌单：3
        playlist_type = request.args.get('playlist_type')
        print("/api/user/songs：",username, playlist_type)

        if not username or not playlist_type:
            return jsonify({'error': 'Missing username or playlist_type'}), 400

        # 获取用户id
        # user_id = UserService.get_user_by_username(username)['id']
        # if not user_id:
        #     return jsonify({'error': 'User not found'}), 404

        # 获取用户 id
        with DatabaseManager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = "SELECT id FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                user = cursor.fetchone()

                if not user:
                    return jsonify({'error': 'User not found'}), 404
                user_id = user[0]
        
        print("user_id:", user_id)

        # 获取歌单信息
        '''
        # 添加到已保存文件列表
            saved_files.append({
                'id': audio_id,
                'name': filename,
                'ar': [{'name': '未知歌手'}],
                'al': {'picUrl': ''},  # 固定的图片 URL
                'dt': duration,
                'mv': 0,
                'alia': [],
                'self': True,
                'fee': 8,
                'st': 0
            })

        # 返回结果
        response = {
            'songsDetail': {
                'songs': saved_files,
                'privileges': [{'chargeInfoList': [{'chargeType': 0}], 'st': 0} for _ in saved_files]
            }
        }
        '''

        # conn = DatabaseManager.get_connection()
        # cursor = conn.cursor()
        query = """
            SELECT music_id, filename, duration, artist, playlist_type,pic_url,is_self
            FROM audio_files
            WHERE user_id = %s AND playlist_type = %s
        """
        # cursor.execute(query, (user_id, playlist_type))
        # conn.commit()
        # result = cursor.fetchall()
        # cursor.close()
        # conn.close()

        result = DatabaseManager.execute_query(query, (user_id, playlist_type), fetch=True)

        # 构建完整的 HTTP 链接
        host = request.host_url.rstrip('/')  # 获取当前主机地址
        for row in result:
            # 去掉 filename 的后缀
            row['filename'] = os.path.splitext(row['filename'])[0]

            # 如果 pic_url 存在，构建 HTTP 链接
            if row['pic_url']:
                row['pic_url'] = f"{host}/static/images/{row['pic_url']}"  # 假设图片存储在 /static/images 目录下

        songs = []
        for row in result:
            songs.append({
                'id': row['music_id'],
                'name': row['filename'],
                'ar': [{'name': row['artist']}],
                'al': {'picUrl': row['pic_url']},
                'dt': row['duration'],
                'mv': 0,
                'alia': [],
                'self': row['is_self'],
                'fee': 8,
                'st': 0
            })

        if songs.__len__() == 0:
            response = {
                'songsDetail': {}
            }
        else:
            response = {
                'songsDetail': {
                    'songs': songs,
                    'privileges': [{'chargeInfoList': [{'chargeType': 0}], 'st': 0} for _ in songs]
                }
            }
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting user songs: {e}")
        return jsonify({'error': str(e)}), 500


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

@app.route('/api/user/delete', methods=['POST'])
def delete_user():
    username = request.json.get('username')
    if not username:
        return jsonify({'message': 'Username is required'}), 400

    # Assume we have a function that deletes the user from the database
    # Example: delete_user_from_db(username)
    user_deleted = UserService.delete_user_from_db(username)
    if user_deleted:
        return jsonify({'message': 'User deleted successfully'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)
