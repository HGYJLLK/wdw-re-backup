# API Documentation

## 基础 URL
所有接口的基础 URL 为：`http://localhost:5001`

---

### 1. 用户注册
**URL:** `/register`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "password": "string",  // 密码
  "security_question": "string",  // 安全问题
  "security_answer": "string"  // 安全问题答案
}
```

**响应:**
- 成功：
  ```json
  {
    "message": "User registered successfully"
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 2. 用户登录
**URL:** `/login`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "password": "string"   // 密码
}
```

**响应:**
- 成功：
  ```json
  {
    "code": 200,
    "message": "Login successful",
    "data": {
      "token": "string",
      "userInfo": {
        "username": "string",
        "nickname": "string",
        "avatar": "string",
        "intro": "string",
        "security_question": "string"
      }
    }
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 3. 上传音频
**URL:** `/upload/audio`

**请求方法:** POST

**请求体:**
- 表单数据：
  - `username` (string): 用户名
  - `is_self` (boolean): 是否为用户自定义音频
  - `playlist_type` (int): 歌单类型
  - `audio_files` (file): 音频文件

**响应:**
- 成功：
  ```json
  {
    "message": "Audio files processed successfully"
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 4. 更新用户信息
**URL:** `/api/user/update`

**请求方法:** POST

**请求体:**
- 表单数据：
  - `username` (string): 用户名
  - 可选：`nickname` (string), `intro` (string)
  - 可选：
    - `oldPassword` (string): 旧密码
    - `newPassword` (string): 新密码
    - `confirmPassword` (string): 确认新密码
  - 可选：头像文件 `avatar` (file)

**响应:**
- 成功：
  ```json
  {
    "code": 200,
    "message": "Update successful",
    "data": {
      "profile_updated": true,
      "password_updated": true,
      "updated_fields": {
        "nickname": "string",
        "intro": "string",
        "avatar": "string"
      }
    }
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 5. 添加音频到歌单
**URL:** `/api/playlist/add`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "playlist_type": "int",  // 歌单类型
  "song_name": "string",  // 歌曲名
  "artist": "string",  // 歌手名
  "duration": "int",  // 时长 (ms)
  "pic_url": "string",  // 歌曲封面
  "is_self": "boolean",  // 是否为自定义
  "music_id": "string"  // 音乐ID（可选）
}
```

**响应:**
- 成功：
  ```json
  {
    "message": "Audio added to playlist successfully"
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 6. 获取用户歌曲
**URL:** `/api/user/songs`

**请求方法:** GET

**请求参数:**
- `username` (string): 用户名
- `playlist_type` (int): 歌单类型

**响应:**
- 成功：
  ```json
  {
    "songsDetail": {
      "songs": [
        {
          "id": "string",
          "name": "string",
          "ar": [{ "name": "string" }],
          "al": { "picUrl": "string" },
          "dt": "int",  // 时长 (ms)
          "mv": 0,
          "alia": [],
          "self": true,
          "fee": 8,
          "st": 0,
          "file_size": "int"  // 文件大小
        }
      ],
      "privileges": [
        { "chargeInfoList": [{ "chargeType": 0 }], "st": 0 }
      ]
    }
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 7. 忘记密码
**URL:** `/reset-password`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "new_password": "string"  // 新密码
}
```

**响应:**
- 成功：
  ```json
  {
    "message": "Password reset successful"
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 8. 删除用户歌曲
**URL:** `/api/user/songs/delete`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "playlist_type": "int",  // 歌单类型
  "music_id": "string"  // 音乐ID
}
```

**响应:**
- 成功：
  ```json
  {
    "message": "Song deleted successfully"
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 9. 验证安全问题
**URL:** `/verify-security`

**请求方法:** POST

**请求体:**
```json
{
  "username": "string",  // 用户名
  "security_answer": "string"  // 安全问题答案（可选）
}
```

**响应:**
- 成功（获取问题）：
  ```json
  {
    "security_question": "string"
  }
  ```
- 成功（验证答案）：
  ```json
  {
    "message": "Security answer verified",
    "verified": true
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 10. 根据音频ID生成音频链接
**URL:** `/audio`

**请求方法:** GET

**请求参数:**
- `id` (string): 音频ID

**响应:**
- 成功：
  ```json
  {
    "musicUrl": "string"  // 音频链接
  }
  ```
- 失败：
  ```json
  {
    "error": "string"
  }
  ```

---

### 11. 退出登录
**URL:** `/logout`

**请求方法:** GET

**响应:**
- 成功：
  ```json
  {
    "code": 200,
    "message": "Logout successful"
  }
  ```
- 失败：
  ```json
  {
    "error": "Logout failed"
  }
  ```