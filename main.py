# pip install flask flask-cors mysql-connector-python pydub pymediainfo ffmpeg-python librosa
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import logging
import os
from werkzeug.utils import secure_filename
# 获取音频时长
from pydub.utils import mediainfo
import ffmpeg
import librosa
import time
import random
import urllib.parse
import shutil

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
    """检查文件是否是允许的音频文件类型"""
    allowed_extensions = {'mp3', 'wav', 'flac', 'aac'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

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
        print("保存音频文件：", file, file.filename, username)
        try:
            # 如果文件名有'/'，则以'/'为分隔符，取后面的部分作为文件名
            original_filename = file.filename.split('/')[-1]
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
    duration = librosa.get_duration(filename=file_path)
    duration_ms = duration * 1000  # 转换为毫秒
    return int(duration_ms)

def get_audio_music_url():
    """获取音频文件url"""
    try:
        query = """
            SELECT a.file_path 
            FROM users u
            JOIN audio_files a ON u.id = a.user_id
            WHERE u.username = 'test_api'
            LIMIT 1
        """
        params = ()
        result = DatabaseManager.execute_query(query, params, fetch=True)
        print("查询结果：", result)
        if result:
            file_path = result[0]['file_path']
            # 构建完整的 HTTP URL
            host = request.host_url.rstrip('/')  # 获取主机地址
            file_url = f"{host}/static/{os.path.relpath(file_path, start='static')}"
            return file_url
        else:
            return None  # 没有找到相关音频文件

    except Exception as e:
        print(f"Error occurred: {e}")
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
            print("删除用户：", result)
            if result:
                logger.info(f"User {username} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete user {username}")
                return False
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}")
            return False

    @staticmethod
    def delete_user_data(username):
        """删除用户数据"""
        try:
            # 确保用户存在
            user = UserService.get_user_by_username(username)
            if not user:
                return False

            user_id = user['id']

            # 删除用户头像
            folder_path = './user_avatars/test_api'
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)

            # 删除用户数据
            query = "DELETE FROM audio_files WHERE user_id = %s"
            params = (user_id,)
            result = DatabaseManager.execute_query(query, params)
            if result:
                logger.info(f"User data for {user_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete user data for {user_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
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
    '''
    1、检索文件夹音频：上传多个音频 / 没有音频（可前端处理）
    2、上传音频：上传单个音频
    '''
    try:
        username = request.form.get('username')
        files = request.files.getlist('audio_files')
        is_self = request.form.get('is_self')

        # 歌手名
        artist = request.form.get('artist') or '未知歌手'
        # song_name = request.form.get('song_name') or ''
        # 歌单，云歌单：1，本地歌单：2，喜欢的歌单：3
        playlist_type = request.form.get('playlist_type')
        # pic_url = request.form.get('pic_url') or 'burger.jpg'
        pic_url = 'burger.jpg'

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

            # 处理filename,test.mp3 -> test
            print("filename:",filename)
            filename = os.path.splitext(filename)[0]

            # 获取音频时长
            duration = get_audio_duration(file_path)
            print("音频时长：",duration)

            # 生成唯一音频id，当前时间戳 + 随机数
            musics_id = int(time.time()) + random.randint(1000, 9999)
            # 保存到数据库
            query = """
                INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)
            """
            params = (user_id, filename, duration, file_path, artist, playlist_type,pic_url,is_self,musics_id)
            DatabaseManager.execute_query(query, params)

        # # 如果files数组为空和存在歌名和is_self为true，在云歌单查找这首歌的music_id，复制一份数据，并且更改playlist_type为playlist_type
        # if not files and song_name and is_self == 'true':
        #     query = "SELECT * FROM audio_files WHERE song_name = %s AND playlist_type = 1"
        #     params = (song_name,)
        #     existing_files = DatabaseManager.execute_query(query, params, fetch=True)
        #     if existing_files:
        #         music_id = existing_files[0]['music_id']
        #         query = """
        #             INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
        #             VALUES (%s, %s, %s,%s)
        #         """
        #         params = (user_id, existing_files[0]['filename'], existing_files[0]['duration'], existing_files[0]['file_path'], artist, playlist_type,pic_url,is_self,music_id)
        #         DatabaseManager.execute_query(query, params)
                

        return jsonify({'message': 'Audio files processed successfully'}), 200

    except Exception as e:
        logger.error(f"Error uploading audio files: {e}")
        return jsonify({'error': str(e)}), 500

'''
添加音频到歌单
'''
@app.route('/api/playlist/add', methods=['POST'])
def add_to_playlist():
    try:
        # 音频两种
        '''
        1、api音频，包含用户名、添加歌单类型、歌曲名、歌手名、歌曲时长、歌曲封面路径
        2、自定义音频：包含用户名、添加歌单类型、歌曲名、自定义歌曲声明
        '''
        data = request.get_json()
        username = data.get('username')
        # music_id = data.get('music_id')
        playlist_type = data.get('playlist_type')
        song_name = data.get('song_name')
        artist = data.get('artist')
        duration = data.get('duration')
        pic_url = data.get('pic_url')
        is_self = data.get('is_self')

        print(data,"data")

        if not all([username, playlist_type]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # 获取用户id
        user_id = UserService.get_user_by_username(username)['id']
        if not user_id:
            return jsonify({'error': 'User not found'}), 404

        # 查询是否已存在该歌曲
        query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s AND playlist_type = %s"
        params = (user_id, song_name, playlist_type)
        existing_files = DatabaseManager.execute_query(query, params, fetch=True)

        if existing_files:
            return jsonify({'message': 'Audio already exists in playlist'}), 400
        
        if not is_self:
            # api音频，直接添加到歌单
            query = "insert into audio_files (user_id, filename, duration,artist, playlist_type,pic_url) values (%s, %s, %s, %s, %s, %s)"
            params = (user_id, song_name, duration, artist, playlist_type,pic_url)
            DatabaseManager.execute_query(query, params)
        else:
            # 自定义音频
            # 在audio_files表中查找该歌名
            query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s"
            params = (user_id, song_name)
            existing_files = DatabaseManager.execute_query(query, params, fetch=True)

            if existing_files:
                # 歌名存在，复制一份该数据，并且更改playlist_type
                # music_id = existing_files[0]['music_id']
                query = """
                    INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (user_id, existing_files[0]['filename'], existing_files[0]['duration'], existing_files[0]['file_path'], existing_files[0]['artist'], playlist_type,existing_files[0]['pic_url'],is_self,existing_files[0]['music_id'])
                DatabaseManager.execute_query(query, params)

        return jsonify({'message': 'Audio added to playlist successfully'}), 200

    except Exception as e:
        logger.error(f"Error adding audio to playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/audio', methods=['GET'])
def get_audio():
    """根据音频ID生成音频链接"""
    try:
        audio_id = request.args.get('id')
        # conn = DatabaseManager.get_connection()
        # cursor = conn.cursor(dictionary=True)
        query = "SELECT file_path FROM audio_files WHERE music_id = %s"
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

    user_deleted = UserService.delete_user_from_db(username)
    print("user_deleted:", user_deleted)
    if user_deleted:

        # 删除static/audio/test_api文件夹
        folder_path = './static/audio/test_api'
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

        return jsonify({'message': 'User deleted successfully'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404
    
# 删除用户数据
@app.route('/api/user/delete-data', methods=['POST'])
def delete_user_data():
    username = request.json.get('username')
    if not username:
        return jsonify({'message': 'Username is required'}), 400

    user_data_deleted = UserService.delete_user_data(username)
    if user_data_deleted:
        return jsonify({'message': 'User data deleted successfully'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404
    
"""获取音频文件ID"""
@app.route('/api/audio/id', methods=['GET'])
def get_audio_id():
    result = get_audio_music_url()
    if not result:
        return jsonify({'error': 'Audio ID not found'}), 404
    return jsonify({'message': 'Audio ID fetched successfully'}), 200

"""查询用户名是否存在"""
@app.route('/api/user/exist', methods=['POST'])
def check_username_exist():
    username = request.json.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    user_exist = UserService.get_user_by_username(username)
    if user_exist:
        return jsonify({'message': 'Username already exists'}), 400
    else:
        return jsonify({'message': 'Username is available'}), 200

"""删除用户歌曲"""
@app.route('/api/user/songs/delete', methods=['POST'])
def delete_user_songs():
    data = request.get_json()
    username = data.get('username')
    music_id = data.get('music_id')
    playlist_type = data.get('playlist_type')

    if not all([username, music_id, playlist_type]):
        return jsonify({'error': 'Missing required fields'}), 400

    # 获取用户id
    user_id = UserService.get_user_by_username(username)['id']
    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    # 删除歌曲
    query = "DELETE FROM audio_files WHERE user_id = %s AND music_id = %s AND playlist_type = %s"
    params = (user_id, music_id, playlist_type)
    DatabaseManager.execute_query(query, params)

    return jsonify({'message': 'Song deleted successfully'}), 200

@app.route('/api/audio/search', methods=['GET'])
def get_music_id():
    query = """
    SELECT af.music_id
    FROM users u
    JOIN audio_files af ON u.id = af.user_id
    WHERE u.username = 'test_api' AND af.playlist_type = 1
    LIMIT 1
    """
    result = DatabaseManager.execute_query(query, fetch=True)
    if not result:
        return jsonify({'error': 'Audio ID not found','data': []}), 404
    return jsonify({'message': 'Audio ID fetched successfully', 'data': result}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)
