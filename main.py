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

import time

app = Flask(__name__)
CORS(app)

# 配置上传文件夹
UPLOAD_FOLDER = "user_avatars"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
UPLOAD_AUDIO_FOLDER = "static/audio"
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "flac"}

# 检查上传文件夹是否存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(UPLOAD_AUDIO_FOLDER):
    os.makedirs(UPLOAD_AUDIO_FOLDER)

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",  # 使用本地数据库
    "user": "root",
    "password": "123qweQWE!",  # 替换为你的密码
    "database": "user_auth",
    "port": 3306,
}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    """检查文件类型是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_audio_file(filename):
    """检查文件是否是允许的音频文件类型"""
    allowed_extensions = {"mp3", "wav", "flac", "aac"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_file(file, folder, filename):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = secure_filename(file.filename)
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(folder, filename)

            # 检查目录是否存在
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
            # 如果文件名有'/'，则以'/'为分隔符，取后面的部分作为文件名
            original_filename = file.filename.split("/")[-1]
            user_folder = os.path.join(UPLOAD_AUDIO_FOLDER, username)
            file_path = os.path.join(user_folder, original_filename)

            # 检查目录是否存在
            os.makedirs(user_folder, exist_ok=True)

            # 如果文件已存在，则跳过保存
            if os.path.exists(file_path):
                logger.info(
                    f"File {original_filename} already exists for user {username}. Skipping save."
                )
                return None, None

            # 保存文件
            file.save(file_path)
            return file_path, original_filename
        except Exception as e:
            logger.error(f"Error saving audio file for user {username}: {e}")
            return None, None
    return None, None


def delete_audio_file(file_path, username):
    """删除音频文件"""
    try:
        # 文件夹路径
        user_folder = os.path.join(UPLOAD_AUDIO_FOLDER, username)
        print(user_folder, "delete_audio_file")
        # 查找文件夹下所有文件
        files = os.listdir(user_folder)
        print(os.path.basename(file_path), "delete_audio_file+++")
        for file in files:
            # 去除file的后缀名
            filename = os.path.splitext(file)[0]
            print(filename, "delete_audio_file")
            if filename == os.path.basename(file_path):
                os.remove(os.path.join(user_folder, file))

        return True
    except Exception as e:
        logger.error(f"Error deleting audio file: {e}")
        return False


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
        if result:
            file_path = result[0]["file_path"]
            # 构建完整的 HTTP URL
            host = request.host_url.rstrip("/")  # 获取主机地址
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
            # 检查用户是否已存在
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
        更新密码，重置密码和验证旧密码。
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
            if old_password and user["password"] != old_password:
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
        """删除用户"""
        try:
            # 检查用户是否存在
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

    @staticmethod
    def delete_user_data(username):
        """删除用户数据"""
        try:
            # 检查用户是否存在
            user = UserService.get_user_by_username(username)
            if not user:
                return False

            user_id = user["id"]

            # 删除用户头像
            folder_path = "./user_avatars/test_api"
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


@app.route("/user_avatars/<username>/<filename>")
def uploaded_file(username, filename):
    """根据用户名获取头像"""
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    try:
        return send_from_directory(user_folder, filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@app.route("/register", methods=["POST"])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        security_question = data.get("security_question")
        security_answer = data.get("security_answer")

        logger.info(f"Attempting to register user: {username}")

        # 校验输入
        if not all([username, password, security_question, security_answer]):
            logger.error("Missing required registration fields")
            return jsonify({"error": "Missing required fields"}), 400

        # 创建新用户
        result = UserService.create_user(
            username, password, security_question, security_answer
        )
        if result is not None:
            # 检查static/audio/<username>是否存在，如果存在，则删除
            user_folder = os.path.join(UPLOAD_AUDIO_FOLDER, username)
            if os.path.exists(user_folder):
                shutil.rmtree(user_folder)

            # 检查user_avatars/<username>是否存在，如果存在，则删除
            user_avatar_folder = os.path.join(UPLOAD_FOLDER, username)
            if os.path.exists(user_avatar_folder):
                shutil.rmtree(user_avatar_folder)

            logger.info(f"Successfully registered user: {username}")
            return jsonify({"message": "User registered successfully"}), 201
        else:
            logger.error("Failed to create user")
            return jsonify({"error": "Registration failed"}), 500

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not all([username, password]):
            return jsonify({"error": "Missing credentials"}), 400

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        if user["password"] != password:
            return jsonify({"error": "Invalid password"}), 401

        # 生成token
        token = f"Bearer_{username}"

        # 构建头像 HTTP 链接
        avatar_url = user.get("avatar_url", "")
        if avatar_url:
            avatar_url = f"http://localhost:5001/user_avatars/{username}/{os.path.basename(avatar_url)}"

        user_info = {
            "username": user["username"],
            "nickname": user.get("nickname", user["username"]),
            "avatar": avatar_url,  # 返回完整的头像 HTTP 链接
            "intro": user.get("intro", ""),
            "security_question": user.get("security_question", ""),
        }

        return (
            jsonify(
                {
                    "code": 200,
                    "message": "Login successful",
                    "data": {"token": token, "userInfo": user_info},
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500


# 管理员登录接口
@app.route("/admin/login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        admin_username = "admin"
        admin_password = "admin"

        if username != admin_username or password != admin_password:
            return jsonify({"error": "用户名或密码错误"}), 401

        # 生成管理员token
        admin_token = f"Admin_{username}_{int(time.time())}"

        return jsonify({"message": "登录成功", "token": admin_token}), 200

    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({"error": "服务器内部错误"}), 500


# 管理员获取统计数据接口
@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 获取用户总数
        users_query = "SELECT COUNT(*) as total FROM users"
        users_result = DatabaseManager.execute_query(users_query, fetch=True)
        total_users = users_result[0]["total"] if users_result else 0

        # 获取音乐总数
        songs_query = "SELECT COUNT(*) as total FROM audio_files"
        songs_result = DatabaseManager.execute_query(songs_query, fetch=True)
        total_songs = songs_result[0]["total"] if songs_result else 0

        # 获取存储空间使用情况
        storage_query = "SELECT SUM(file_size) as total FROM audio_files"
        storage_result = DatabaseManager.execute_query(storage_query, fetch=True)
        storage_used = (
            storage_result[0]["total"]
            if storage_result and storage_result[0]["total"]
            else 0
        )

        return (
            jsonify(
                {
                    "totalUsers": total_users,
                    "totalSongs": total_songs,
                    "storageUsed": storage_used,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        return jsonify({"error": "获取统计数据失败"}), 500


# 获取用户列表
@app.route("/admin/users", methods=["GET"])
def admin_get_users():
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 获取分页参数
        page = int(request.args.get("page", 1))
        search = request.args.get("search", "")

        # 每页显示数量
        per_page = 10
        offset = (page - 1) * per_page

        if search:
            query = "SELECT * FROM users WHERE username LIKE %s ORDER BY id DESC LIMIT %s OFFSET %s"
            params = (f"%{search}%", per_page, offset)
        else:
            query = "SELECT * FROM users ORDER BY id DESC LIMIT %s OFFSET %s"
            params = (per_page, offset)

        result = DatabaseManager.execute_query(query, params, fetch=True)

        return jsonify({"users": result}), 200

    except Exception as e:
        logger.error(f"Admin get users error: {e}")
        return jsonify({"error": "获取用户列表失败"}), 500


# 获取单个用户详情
@app.route("/admin/users/<int:user_id>", methods=["GET"])
def admin_get_user(user_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 获取用户信息
        query = "SELECT id, username, nickname, avatar_url, intro, created_at, security_question, security_answer FROM users WHERE id = %s"
        params = (user_id,)
        user_result = DatabaseManager.execute_query(query, params, fetch=True)

        if not user_result:
            return jsonify({"error": "用户不存在"}), 404

        user = user_result[0]

        # 获取用户统计信息
        stats_query = """
            SELECT 
                COUNT(*) as song_count,
                COALESCE(SUM(file_size), 0) as storage_used
            FROM audio_files
            WHERE user_id = %s
        """
        stats_result = DatabaseManager.execute_query(
            stats_query, (user_id,), fetch=True
        )

        # 头像处理
        if user.get("avatar_url"):
            host = request.host_url.rstrip("/")
            user["avatar_url"] = f"{host}{user['avatar_url']}"

        return (
            jsonify(
                {"user": user, "statistics": stats_result[0] if stats_result else None}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Admin get user error: {e}")
        return jsonify({"error": "获取用户信息失败"}), 500


# 删除用户
@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 检查用户是否存在
        query = "SELECT username FROM users WHERE id = %s"
        params = (user_id,)
        user_result = DatabaseManager.execute_query(query, params, fetch=True)

        if not user_result:
            return jsonify({"error": "用户不存在"}), 404

        username = user_result[0]["username"]

        # 删除用户的音频文件
        query = "SELECT file_path FROM audio_files WHERE user_id = %s"
        params = (user_id,)
        files_result = DatabaseManager.execute_query(query, params, fetch=True)

        for file in files_result:
            file_path = file["file_path"]
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    logger.warning(f"Failed to delete file: {file_path}")

        # 删除用户的头像目录
        avatar_dir = os.path.join(UPLOAD_FOLDER, username)
        if os.path.exists(avatar_dir):
            try:
                shutil.rmtree(avatar_dir)
            except:
                logger.warning(f"Failed to delete avatar directory: {avatar_dir}")

        # 删除用户的音频目录
        audio_dir = os.path.join(UPLOAD_AUDIO_FOLDER, username)
        if os.path.exists(audio_dir):
            try:
                shutil.rmtree(audio_dir)
            except:
                logger.warning(f"Failed to delete audio directory: {audio_dir}")

        # 删除用户的音频记录
        query = "DELETE FROM audio_files WHERE user_id = %s"
        params = (user_id,)
        DatabaseManager.execute_query(query, params)
        query = "DELETE FROM global_music WHERE user_id = %s"
        params = (user_id,)
        DatabaseManager.execute_query(query, params)

        # 最后删除用户
        query = "DELETE FROM users WHERE id = %s"
        params = (user_id,)
        DatabaseManager.execute_query(query, params)

        return jsonify({"success": True, "message": "用户删除成功"}), 200

    except Exception as e:
        logger.error(f"Admin delete user error: {e}")
        return jsonify({"error": "删除用户失败"}), 500


# 获取所有用户
@app.route("/admin/users/all", methods=["GET"])
def admin_get_all_users():
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        query = "SELECT id, username FROM users ORDER BY username"
        result = DatabaseManager.execute_query(query, fetch=True)

        return jsonify({"users": result}), 200

    except Exception as e:
        logger.error(f"Admin get all users error: {e}")
        return jsonify({"error": "获取用户列表失败"}), 500


# 重置用户密码
@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_user_password(user_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        data = request.get_json()
        new_password = data.get("new_password")

        if not new_password:
            return jsonify({"error": "新密码不能为空"}), 400

        # 检查用户是否存在
        query = "SELECT * FROM users WHERE id = %s"
        params = (user_id,)
        user_result = DatabaseManager.execute_query(query, params, fetch=True)

        if not user_result:
            return jsonify({"error": "用户不存在"}), 404

        # 更新密码
        query = "UPDATE users SET password = %s WHERE id = %s"
        params = (new_password, user_id)
        DatabaseManager.execute_query(query, params)

        return jsonify({"success": True, "message": "密码重置成功"}), 200

    except Exception as e:
        logger.error(f"Admin reset user password error: {e}")
        return jsonify({"error": "密码重置失败"}), 500


# 获取音乐列表
@app.route("/admin/music", methods=["GET"])
def get_admin_music():
    try:
        # token = request.headers.get("Authorization")
        page = int(request.args.get("page", 1))
        search = request.args.get("search", "")
        user_id = request.args.get("user_id", "")

        limit = 10
        offset = (page - 1) * limit

        conditions = []
        params = []

        if search:
            conditions.append("(gm.name LIKE %s OR gm.artist LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        if user_id:
            conditions.append("gm.user_id = %s")
            params.append(user_id)

        # 构建完整查询
        query = """
            SELECT gm.*, u.username 
            FROM global_music gm
            LEFT JOIN users u ON gm.user_id = u.id
        """

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY gm.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        result = DatabaseManager.execute_query(query, tuple(params), fetch=True)

        return jsonify({"music": result}), 200
    except Exception as e:
        logger.error(f"Error getting music list: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 获取单个音乐详情
@app.route("/admin/music/<music_id>", methods=["GET"])
def get_admin_music_detail(music_id):
    try:
        query = """
            SELECT gm.*, u.username 
            FROM global_music gm
            LEFT JOIN users u ON gm.user_id = u.id
            WHERE gm.music_id = %s
        """

        result = DatabaseManager.execute_query(query, (music_id,), fetch=True)

        if not result:
            return jsonify({"error": "Music not found"}), 404

        return jsonify({"music": result[0]}), 200
    except Exception as e:
        logger.error(f"Error getting music detail: {e}")
        return jsonify({"error": str(e)}), 500


# 删除音乐
@app.route("/admin/music/<int:music_id>", methods=["DELETE"])
def admin_delete_music(music_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 先获取音乐信息
        query = "SELECT * FROM audio_files WHERE music_id = %s"
        params = (music_id,)
        result = DatabaseManager.execute_query(query, params, fetch=True)

        if not result:
            return jsonify({"error": "音乐不存在"}), 404

        music = result[0]

        # 删除文件
        file_path = music.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                logger.warning(f"Failed to delete file: {file_path}")

        # 删除数据库记录
        query = "DELETE FROM audio_files WHERE music_id = %s"
        params = (music_id,)
        DatabaseManager.execute_query(query, params)

        return jsonify({"success": True, "message": "音乐删除成功"}), 200

    except Exception as e:
        logger.error(f"Admin delete music error: {e}")
        return jsonify({"error": "删除音乐失败"}), 500


# 音乐权限控制
@app.route("/admin/music/<music_id>/toggle-disable", methods=["POST"])
def toggle_disable_music(music_id):
    try:
        # 获取当前状态
        query = "SELECT is_disabled, is_api_music FROM global_music WHERE music_id = %s"
        result = DatabaseManager.execute_query(query, (music_id,), fetch=True)

        if not result:
            return jsonify({"error": "Music not found"}), 404

        current_state = result[0]["is_disabled"]
        is_api_music = result[0]["is_api_music"]

        # 只允许禁用API音乐
        if not is_api_music:
            return jsonify({"success": False, "message": "自定义音频不允许禁用"}), 400

        # 更新状态
        new_state = not current_state
        update_query = "UPDATE global_music SET is_disabled = %s WHERE music_id = %s"
        DatabaseManager.execute_query(update_query, (new_state, music_id))

        action = "禁用" if new_state else "解除禁用"

        return jsonify({"success": True, "message": f"音乐已{action}"}), 200
    except Exception as e:
        logger.error(f"Error toggling music state: {e}")
        return jsonify({"error": str(e)}), 500


# 获取全局音乐详情
@app.route("/admin/global-music/<string:music_id>", methods=["GET"])
def admin_get_global_music(music_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        query = "SELECT * FROM global_music WHERE music_id = %s"
        params = (music_id,)
        result = DatabaseManager.execute_query(query, params, fetch=True)

        if not result:
            return jsonify({"error": "音乐不存在"}), 404

        music = result[0]
        music["filename"] = music["name"]

        # 如果有封面图，构建完整URL
        if music.get("pic_url") and not music["pic_url"].startswith("http"):
            host = request.host_url.rstrip("/")
            music["pic_url"] = f"{host}/static/images/{music['pic_url']}"

        return jsonify({"music": music}), 200

    except Exception as e:
        logger.error(f"Admin get global music error: {e}")
        return jsonify({"error": "获取音乐详情失败"}), 500


# 禁用/解除禁用全局音乐
@app.route("/admin/global-music/<string:music_id>/toggle-disable", methods=["POST"])
def admin_toggle_global_music(music_id):
    # 验证管理员身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Admin_"):
        return jsonify({"error": "未授权访问"}), 401

    try:
        # 获取当前状态
        query = "SELECT is_disabled FROM global_music WHERE music_id = %s"
        params = (music_id,)
        result = DatabaseManager.execute_query(query, params, fetch=True)

        if not result:
            return jsonify({"error": "音乐不存在"}), 404

        # 切换禁用状态
        current_state = result[0].get("is_disabled", False)
        new_state = not current_state

        # 更新全局音乐状态
        query = "UPDATE global_music SET is_disabled = %s WHERE music_id = %s"
        params = (new_state, music_id)
        DatabaseManager.execute_query(query, params)

        message = "音乐已禁用" if new_state else "音乐已解除禁用"
        return (
            jsonify({"success": True, "message": message, "is_disabled": new_state}),
            200,
        )

    except Exception as e:
        logger.error(f"Admin toggle global music error: {e}")
        return jsonify({"error": "操作失败"}), 500


@app.route("/api/user/update", methods=["POST"])
def update_user():
    """更新用户信息和密码接口"""
    try:
        data = request.form.to_dict()
        username = data.get("username")

        if not username:
            return jsonify({"error": "Username is required"}), 400

        # 获取当前用户信息
        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # 初始化更新状态
        profile_updated = False
        password_updated = False
        updates = {}

        # 更新基本信息
        if "nickname" in data:
            updates["nickname"] = data["nickname"]
        if "intro" in data:
            updates["intro"] = data["intro"]

        if updates:
            profile_result = UserService.update_user_profile(
                username, updates.get("nickname"), updates.get("intro")
            )
            if profile_result is None:
                return jsonify({"error": "Failed to update profile"}), 500
            profile_updated = True

        # 更新头像（文件上传）
        if "avatar" in request.files:
            file = request.files["avatar"]
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type"}), 400

            file_extension = file.filename.rsplit(".", 1)[1].lower()
            avatar_filename = f"{username}_avatar.{file_extension}"
            file_url = save_file(
                file, folder=f"user_avatars/{username}", filename=avatar_filename
            )
            if not file_url:
                return jsonify({"error": "Failed to save avatar"}), 500

            # 将头像的 URL 转换为完整的 HTTP 链接
            full_avatar_url = f"http://localhost:5001{file_url}"
            avatar_result = UserService.update_avatar(username, full_avatar_url)
            if avatar_result is None:
                return jsonify({"error": "Failed to update avatar"}), 500
            updates["avatar"] = full_avatar_url
            profile_updated = True

        # 更新密码
        old_password = data.get("oldPassword")
        new_password = data.get("newPassword")
        confirm_password = data.get("confirmPassword")

        if old_password or new_password or confirm_password:
            if not old_password or not new_password or not confirm_password:
                return jsonify({"error": "All password fields are required"}), 400
            if new_password != confirm_password:
                return (
                    jsonify({"error": "New password and confirmation do not match"}),
                    400,
                )

            password_result = UserService.update_password(
                username, new_password, old_password
            )
            if password_result is None:
                return jsonify({"error": "Failed to update password"}), 401
            password_updated = True

        return jsonify(
            {
                "code": 200,
                "message": "Update successful",
                "data": {
                    "profile_updated": profile_updated,
                    "password_updated": password_updated,
                    "updated_fields": updates,
                },
            }
        )

    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/verify-security", methods=["POST"])
def verify_security():
    """验证安全问题"""
    try:
        data = request.get_json()
        username = data.get("username")
        security_answer = data.get("security_answer")

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        if not security_answer:
            return jsonify({"security_question": user["security_question"]}), 200

        if user["security_answer"] != security_answer:
            return jsonify({"error": "Invalid security answer"}), 401

        return jsonify({"message": "Security answer verified", "verified": True}), 200

    except Exception as e:
        logger.error(f"Security verification error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/upload/audio", methods=["POST"])
def upload_audio():
    """
    1、检索文件夹音频：上传多个音频 / 没有音频
    2、上传音频：上传单个音频
    """
    try:
        username = request.form.get("username")
        files = request.files.getlist("audio_files")
        is_self = request.form.get("is_self")

        # 歌手名
        artist = request.form.get("artist") or "未知歌手"
        # song_name = request.form.get('song_name') or ''
        # 歌单，云歌单：1，本地歌单：2，喜欢的歌单：3
        playlist_type = request.form.get("playlist_type")
        pic_url = "burger.png"

        if not username:
            return jsonify({"error": "Missing username"}), 400

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user["id"]

        for file in files:
            if not allowed_audio_file(file.filename):
                continue

            # 检查是否存在同名文件
            query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s AND playlist_type = %s"
            params = (user_id, file.filename, playlist_type)
            existing_files = DatabaseManager.execute_query(query, params, fetch=True)

            if existing_files:
                logger.info(
                    f"User {username} already has a file named {file.filename}. Skipping save."
                )
                continue

            # 获取音频大小
            file.stream.seek(0, os.SEEK_END)
            file_size = file.stream.tell()
            file.stream.seek(0)

            # 保存音频文件
            file_path, filename = save_audio_file(file, username)

            if not file_path:
                continue

            # 处理filename,test.mp3 -> test
            filename = os.path.splitext(filename)[0]

            # 获取音频时长
            duration = get_audio_duration(file_path)

            # 生成唯一音频id，当前时间戳 + 随机数
            musics_id = int(time.time()) + random.randint(1000, 9999)
            # 保存到数据库
            query = """
                INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id,file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
            """
            params = (
                user_id,
                filename,
                duration,
                file_path,
                artist,
                playlist_type,
                pic_url,
                is_self,
                musics_id,
                file_size,
            )
            DatabaseManager.execute_query(query, params)

        return jsonify({"message": "Audio files processed successfully"}), 200

    except Exception as e:
        logger.error(f"Error uploading audio files: {e}")
        return jsonify({"error": str(e)}), 500


"""
添加音频到歌单
"""


@app.route("/api/playlist/add", methods=["POST"])
def add_to_playlist():
    try:
        # 音频两种
        """
        1、api音频，包含用户名、添加歌单类型、歌曲名、歌手名、歌曲时长、歌曲封面路径
        2、自定义音频：包含用户名、添加歌单类型、歌曲名、自定义歌曲声明
        """
        data = request.get_json()
        username = data.get("username")
        music_id = data.get("music_id")
        playlist_type = data.get("playlist_type")
        song_name = data.get("song_name")
        artist = data.get("artist")
        duration = data.get("duration")
        pic_url = data.get("pic_url")
        is_self = data.get("is_self")

        if not all([username, playlist_type]):
            return jsonify({"error": "Missing required fields"}), 400

        # 获取用户id
        user_id = UserService.get_user_by_username(username)["id"]
        if not user_id:
            return jsonify({"error": "User not found"}), 404

        # 查询是否已存在该歌曲
        query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s AND playlist_type = %s"
        params = (user_id, song_name, playlist_type)
        existing_files = DatabaseManager.execute_query(query, params, fetch=True)

        if existing_files:
            return jsonify({"message": "Audio already exists in playlist"}), 400

        if not is_self:
            # API音乐，检查管理端是否已存在
            check_query = "SELECT * FROM global_music WHERE music_id = %s"
            check_params = (music_id,)
            global_music = DatabaseManager.execute_query(
                check_query, check_params, fetch=True
            )

            if not global_music:
                # 不存在，添加到管理端
                global_query = """
                    INSERT INTO global_music 
                    (music_id, name, artist, duration, pic_url,is_api_music,user_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                global_params = (
                    music_id,
                    song_name,
                    artist,
                    duration,
                    pic_url,
                    True,
                    user_id,
                )
                DatabaseManager.execute_query(global_query, global_params)

            # 关联用户
            query = """
                INSERT INTO audio_files 
                (user_id, filename, duration, artist, playlist_type, pic_url, music_id, is_api_music, reference_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            gen_music_id = f"user_{user_id}_api_{music_id}_playlist_{playlist_type}"
            params = (
                user_id,
                song_name,
                duration,
                artist,
                playlist_type,
                pic_url,
                music_id,
                True,
                gen_music_id,
            )
            DatabaseManager.execute_query(query, params)
        else:
            # 自定义音频
            # 在audio_files表中查找该歌名
            query = "SELECT * FROM audio_files WHERE user_id = %s AND filename = %s"
            params = (user_id, song_name)
            existing_files = DatabaseManager.execute_query(query, params, fetch=True)

            if existing_files:
                # 歌名存在
                query = """
                    INSERT INTO audio_files (user_id, filename, duration, file_path,artist, playlist_type,pic_url,is_self,music_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    user_id,
                    existing_files[0]["filename"],
                    existing_files[0]["duration"],
                    existing_files[0]["file_path"],
                    existing_files[0]["artist"],
                    playlist_type,
                    existing_files[0]["pic_url"],
                    is_self,
                    existing_files[0]["music_id"],
                )
                DatabaseManager.execute_query(query, params)

                # 检查管理端该用户是否已添加过该歌曲
                check_query = (
                    "SELECT * FROM global_music WHERE music_id = %s AND user_id = %s"
                )
                check_params = (music_id, user_id)
                global_music = DatabaseManager.execute_query(
                    check_query, check_params, fetch=True
                )

                if not global_music:
                    # 未添加过，添加到管理端
                    global_query = """
                        INSERT INTO global_music 
                        (music_id, name, artist, duration, pic_url, user_id, is_api_music,username,user_id) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s,%s,%s)
                    """
                    global_params = (
                        music_id,
                        song_name,
                        artist,
                        duration,
                        pic_url,
                        user_id,
                        False,
                        username,
                        user_id,
                    )

                    DatabaseManager.execute_query(global_query, global_params)

        return jsonify({"message": "Audio added to playlist successfully"}), 200

    except Exception as e:
        logger.error(f"Error adding audio to playlist: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/audio", methods=["GET"])
def get_audio():
    """根据音频ID生成音频链接"""
    try:
        audio_id = request.args.get("id")
        query = "SELECT file_path FROM audio_files WHERE music_id = %s"
        result = DatabaseManager.execute_query(query, (audio_id,), fetch=True)

        if not result:
            return jsonify({"error": "Audio not found"}), 404

        # 获取文件路径
        file_path = result[0]["file_path"]

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found on server"}), 404

        # 构建完整的 HTTP URL
        host = request.host_url.rstrip("/")  # 获取主机地址
        file_url = f"{host}/static/{os.path.relpath(file_path, start='static')}"

        return jsonify({"musicUrl": file_url}), 200
    except Exception as e:
        logger.error(f"Error fetching audio file URL: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/logout", methods=["GET"])
def logout():
    try:
        return jsonify({"code": 200, "message": "Logout successful"})
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


# 根据用户、歌单获取歌曲
@app.route("/api/user/songs", methods=["GET"])
def get_user_songs():
    try:
        username = request.args.get("username")
        # 云歌单：1 本地歌单：2 我的最爱歌单：3
        playlist_type = request.args.get("playlist_type")
        if not username or not playlist_type:
            return jsonify({"error": "Missing username or playlist_type"}), 400

        # 获取用户 id
        with DatabaseManager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = "SELECT id FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                user = cursor.fetchone()

                if not user:
                    return jsonify({"error": "User not found"}), 404
                user_id = user[0]

        # 获取歌单信息
        """
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
        """
        query = """
            SELECT music_id, filename, duration, artist, playlist_type, pic_url, is_self, file_size, is_disabled
            FROM audio_files
            WHERE user_id = %s AND playlist_type = %s
        """
        result = DatabaseManager.execute_query(
            query, (user_id, playlist_type), fetch=True
        )

        # 构建完整的 HTTP 链接
        host = request.host_url.rstrip("/")  # 获取当前主机地址
        for row in result:
            # 去掉 filename 的后缀
            row["filename"] = os.path.splitext(row["filename"])[0]

            # 如果 pic_url 存在，构建 HTTP 链接
            if row["pic_url"] and row["is_self"]:
                row["pic_url"] = f"{host}/static/images/{row['pic_url']}"

        songs = []
        for row in result:
            songs.append(
                {
                    "id": row["music_id"],
                    "name": row["filename"],
                    "ar": [{"name": row["artist"]}],
                    "al": {"picUrl": row["pic_url"]},
                    "dt": row["duration"],
                    "mv": 0,
                    "alia": [],
                    "self": row["is_self"],
                    "fee": 8,
                    "st": 0,
                    # 音频大小
                    "file_size": row["file_size"],
                    "is_disabled": row["is_disabled"],
                }
            )

        if songs.__len__() == 0:
            response = {"songsDetail": {}}
        else:
            response = {
                "songsDetail": {
                    "songs": songs,
                    "privileges": [
                        {"chargeInfoList": [{"chargeType": 0}], "st": 0} for _ in songs
                    ],
                }
            }
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting user songs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        username = data.get("username")
        new_password = data.get("new_password")

        if not all([username, new_password]):
            return jsonify({"error": "Missing required fields"}), 400

        user = UserService.get_user_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        result = UserService.update_password(username, new_password)
        if result is not None:
            return jsonify({"message": "Password reset successful"}), 200
        else:
            return jsonify({"error": "Password reset failed"}), 500

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def delete_user_music_records(user_id):
    try:
        # 删除global_music表中用户上传的自定义音频记录
        query = "DELETE FROM global_music WHERE user_id = %s AND is_api_music = FALSE"
        DatabaseManager.execute_query(query, (user_id,))

        # 继续删除audio_files表中的记录
        query = "DELETE FROM audio_files WHERE user_id = %s"
        DatabaseManager.execute_query(query, (user_id,))

        return True
    except Exception as e:
        logger.error(f"Error deleting user music records: {e}")
        return False


@app.route("/api/user/delete", methods=["POST"])
def delete_user():
    username = request.json.get("username")
    if not username:
        return jsonify({"message": "Username is required"}), 400

    user = UserService.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # 删除用户相关的音乐记录
    delete_user_music_records(user["id"])

    user_deleted = UserService.delete_user_from_db(username)
    if user_deleted:

        folder_path = "./static/audio/test_api"
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"message": "User not found"}), 404


# 删除用户数据
@app.route("/api/user/delete-data", methods=["POST"])
def delete_user_data():
    username = request.json.get("username")
    if not username:
        return jsonify({"message": "Username is required"}), 400

    user_data_deleted = UserService.delete_user_data(username)
    if user_data_deleted:
        return jsonify({"message": "User data deleted successfully"}), 200
    else:
        return jsonify({"message": "User not found"}), 404


"""获取音频文件ID"""


@app.route("/api/audio/id", methods=["GET"])
def get_audio_id():
    result = get_audio_music_url()
    if not result:
        return jsonify({"error": "Audio ID not found"}), 404
    return jsonify({"message": "Audio ID fetched successfully"}), 200


"""查询用户名是否存在"""


@app.route("/api/user/exist", methods=["POST"])
def check_username_exist():
    username = request.json.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    user_exist = UserService.get_user_by_username(username)
    if user_exist:
        return jsonify({"message": "Username already exists"}), 400
    else:
        return jsonify({"message": "Username is available"}), 200


"""删除用户歌曲"""


@app.route("/api/user/songs/delete", methods=["POST"])
def delete_user_songs():
    data = request.get_json()
    username = data.get("username")
    music_id = data.get("music_id")
    playlist_type = data.get("playlist_type")

    if not all([username, music_id, playlist_type]):
        return jsonify({"error": "Missing required fields"}), 400

    # 获取用户id
    user = UserService.get_user_by_username(username)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_id = user["id"]

    try:
        # 查询歌曲
        query = """
            SELECT * FROM audio_files 
            WHERE user_id = %s AND music_id = %s AND playlist_type = %s
        """
        params = (user_id, music_id, playlist_type)
        existing_files = DatabaseManager.execute_query(query, params, fetch=True)

        if not existing_files:
            return jsonify({"error": "Song not found"}), 404

        music_info = existing_files[0]

        # 如果是API音乐，只删除用户关联
        if music_info.get("is_api_music"):
            query = """
                DELETE FROM audio_files 
                WHERE user_id = %s AND music_id = %s AND playlist_type = %s
            """
            params = (user_id, music_id, playlist_type)
            DatabaseManager.execute_query(query, params)
        else:
            # 如果是自定义音乐，删除文件和记录
            if music_info.get("is_self"):
                file_path = music_info.get("file_path")
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        logger.warning(f"Failed to delete file: {file_path}")

            # 删除用户的歌曲记录
            query = """
                DELETE FROM audio_files 
                WHERE user_id = %s AND music_id = %s AND playlist_type = %s
            """
            params = (user_id, music_id, playlist_type)
            DatabaseManager.execute_query(query, params)

        return jsonify({"message": "Song deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting user song: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/search", methods=["GET"])
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
        return jsonify({"error": "Audio ID not found", "data": []}), 404
    return jsonify({"message": "Audio ID fetched successfully", "data": result}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
