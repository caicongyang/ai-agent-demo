# Order Customer Service System

基于 LangChain 的订单客服系统，可以：
1. 使用基础话术与客户对话
2. 记录对话历史
3. 从数据库查询订单发货时间、预计到货时间等信息

## 功能特点

- 🤖 基于 LangChain 构建的对话系统
- 📊 订单信息查询（发货状态、预计到货时间）
- 🚚 物流跟踪（物流公司、快递单号）
- 💬 记录完整对话历史
- 🛠️ 提供命令行和 API 两种使用方式

## 系统架构

- 数据库：MySQL/MariaDB (通过 SQLAlchemy ORM)
- 对话模型：OpenAI GPT (通过 LangChain)
- API：Flask RESTful API
- CLI：命令行交互界面

## 安装

1. 克隆代码库：

```bash
git clone <repository-url>
cd order-customer
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 创建环境变量文件 `.env`：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=order_system

OPENAI_API_KEY=your_openai_key
OPENAI_MODEL_NAME=gpt-3.5-turbo
```

## 使用方法

### 命令行界面

1. 初始化示例数据：

```bash
python cli.py --init-data
```

2. 启动客服对话：

```bash
python cli.py --phone 13800138000 --name 张三
```

示例查询：
- "我的订单什么时候发货？"
- "我想查询订单 ORD87654321 的状态"
- "我的快递到哪了？"

### API 服务

启动 API 服务：

```bash
python app.py
```

API 端点：
- `GET /api/health` - 服务健康检查
- `POST /api/conversation/start` - 开始对话
- `POST /api/conversation/message` - 发送消息
- `POST /api/conversation/end` - 结束对话
- `GET /api/conversation/history` - 获取对话历史

#### API 使用示例

1. 开始对话：

```bash
curl -X POST http://localhost:5000/api/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000", "name":"张三"}'
```

2. 发送消息：

```bash
curl -X POST http://localhost:5000/api/conversation/message \
  -H "Content-Type: application/json" \
  -d '{"session_id":"your-session-id", "message":"我的订单什么时候发货？"}'
```

3. 获取对话历史：

```bash
curl -X GET http://localhost:5000/api/conversation/history?session_id=your-session-id
```

## 数据库结构

- `customers` - 客户信息
- `orders` - 订单信息
- `order_items` - 订单商品
- `conversations` - 对话会话
- `messages` - 对话消息

## 常见问题

1. **数据库连接错误**
   - 检查 `.env` 文件中的数据库配置是否正确
   - 确保数据库服务已启动

2. **OpenAI API 错误**
   - 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
   - 确保 API KEY 有足够的使用额度

## 许可证

MIT License 