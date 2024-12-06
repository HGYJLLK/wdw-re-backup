# 用户管理系统 API 文档

## 基础 URL
```
http://localhost:5001
```

## 认证方式
除了注册和登录接口外，其他接口都需要在请求头中携带 Bearer token：
```
Authorization: Bearer_username
```

## API 接口列表

### 1. 用户注册
```http
POST /register
```

**请求体：**
```json
{
    "username": "用户名",
    "password": "密码",
    "security_question": "安全问题",
    "security_answer": "安全问题答案"
}
```

**响应：**
```json
{
    "message": "User registered successfully"
}
```

### 2. 用户登录
```http
POST /login
```

**请求体：**
```json
{
    "username": "用户名",
    "password": "密码"
}
```

**响应：**
```json
{
    "code": 200,
    "message": "Login successful",
    "data": {
        "token": "Bearer_username",
        "userInfo": {
            "username": "用户名",
            "nickname": "昵称",
            "avatarUrl": "头像URL",
            "intro": "个人简介",
            "security_question": "安全问题"
        }
    }
}
```

### 3. 更新用户信息
```http
PUT /api/user/profile
```

**请求头：**
```
Authorization: Bearer_username
```

**请求体：**
（除了 username 外，其他字段都是可选的）
```json
{
    "username": "用户名",
    "nickname": "新昵称",     // 可选
    "intro": "新个人简介",    // 可选
    "oldPassword": "旧密码",  // 如果要修改密码则必填
    "newPassword": "新密码"   // 如果要修改密码则必填
}
```

**响应：**
```json
{
    "code": 200,
    "message": "Update successful",
    "data": {
        "profile_updated": true,  // 是否更新了个人信息
        "password_updated": true  // 是否更新了密码
    }
}
```

### 4. 上传头像
```http
POST /upload/avatar
```

**请求头：**
```
Authorization: Bearer_username
Content-Type: multipart/form-data
```

**请求体：**
```
file: [图片文件]
```

**响应：**
```json
{
    "code": 200,
    "message": "头像上传成功",
    "data": {
        "url": "/uploads/avatars/[文件名]"
    }
}
```

### 5. 验证安全问题
```http
POST /verify-security
```

**请求体：**
```json
{
    "username": "用户名",
    "security_answer": "安全问题答案"  // 可选
}
```

**响应：**
如果没有提供 security_answer：
```json
{
    "security_question": "用户的安全问题"
}
```

如果提供了 security_answer：
```json
{
    "message": "Security answer verified",
    "verified": true
}
```

## 错误响应
所有接口在出错时会返回以下格式：

```json
{
    "error": "错误信息"
}
```

常见状态码：
- 400：请求参数错误
- 401：未授权（token无效或过期）
- 404：资源不存在
- 500：服务器内部错误

## 文件上传说明
- 支持的图片格式：PNG, JPG, JPEG, GIF
- 文件存储路径：`/uploads/avatars/`
- 文件命名规则：`时间戳_原文件名`

## 使用说明
1. 除了注册和登录接口，其他接口都需要在请求头中携带认证信息
2. 更新用户信息时可以只更新需要的字段，不需要的字段可以不传
3. 修改密码时必须同时提供旧密码和新密码
4. 头像上传是独立的接口，需要使用 multipart/form-data 格式
5. 所有接口都会返回 code 字段，200 表示成功，其他表示出错

## 代码调用示例

### 前端请求示例（使用 axios）：

```javascript
// 登录
const login = async (username, password) => {
    const response = await axios.post('/login', {
        username,
        password
    });
    return response.data;
};

// 上传头像
const uploadAvatar = async (file, token) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post('/upload/avatar', formData, {
        headers: {
            'Authorization': `Bearer_${username}`,
            'Content-Type': 'multipart/form-data'
        }
    });
    return response.data;
};

// 更新用户信息
const updateProfile = async (username, updateData, token) => {
    const response = await axios.put('/api/user/profile', {
        username,
        ...updateData  // 可以包含 nickname, intro, oldPassword, newPassword
    }, {
        headers: {
            'Authorization': `Bearer_${username}`
        }
    });
    return response.data;
};
```

## 注意事项
1. token 的格式为 `Bearer_用户名`
2. 文件上传时注意检查文件类型和大小
3. 更新用户信息时可以同时更新多个字段
4. 密码修改操作最好二次确认
5. 头像文件上传成功后，需要保存返回的 URL
