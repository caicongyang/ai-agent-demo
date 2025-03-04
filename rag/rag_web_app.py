import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from document_rag_system import DocumentRAGSystem

# 加载 .env 文件
load_dotenv()

app = Flask(__name__, template_folder='templates')

# 全局 RAG 系统
rag_system = None
rag_chain = None

def get_all_documents(directory):
    """
    获取目录下所有支持的文档
    
    :param directory: 文档目录
    :return: 文档路径列表
    """
    supported_extensions = ['.txt', '.pdf', '.docx']
    documents = []
    
    # 确保目录存在
    if not os.path.exists(directory):
        os.makedirs(directory)
        return documents
    
    # 遍历目录
    for filename in os.listdir(directory):
        # 获取文件扩展名
        ext = os.path.splitext(filename)[1].lower()
        
        # 检查是否为支持的文档类型
        if ext in supported_extensions:
            full_path = os.path.join(directory, filename)
            documents.append(full_path)
    
    return documents

def initialize_rag_system():
    """
    初始化 RAG 系统
    """
    global rag_system, rag_chain
    
    # 从环境变量读取 API 密钥和基础 URL
    embedding_api_key = os.getenv("EMBEDDING_API_KEY")
    embedding_base_url = os.getenv("EMBEDDING_BASE_URL")
    
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL")
    
    # 检查 API 密钥是否存在
    if not embedding_api_key or not llm_api_key:
        raise ValueError("未找到 API 密钥")
    
    rag_system = DocumentRAGSystem(
        embedding_api_key=embedding_api_key,
        embedding_base_url=embedding_base_url,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        embedding_model="BAAI/bge-m3",
        chat_model="deepseek-chat"
    )
    
    # 默认文档目录
    documents_dir = './rag/documents'
    
    # 获取所有文档
    default_docs = get_all_documents(documents_dir)
    
    # 如果没有文档，创建示例文档
    if not default_docs:
        sample_docs = [
            {
                'path': os.path.join(documents_dir, 'sample.txt'),
                'content': """
人工智能的发展已经成为当今科技领域最引人注目的话题之一。从机器学习到深度学习，AI技术正在rapidly改变我们的生活和工作方式。

关键技术包括：
1. 机器学习算法
2. 神经网络
3. 自然语言处理
4. 计算机视觉

人工智能的应用范围广泛，从医疗诊断到自动驾驶，从金融分析到个性化推荐，AI正在重塑各个行业的格局。
"""
            },
            {
                'path': os.path.join(documents_dir, 'sample.pdf'),
                'content': """
人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，致力于创造能够模仿人类智能行为的智能机器。

AI的主要研究领域包括：
- 机器学习
- 深度学习
- 自然语言处理
- 计算机视觉
- 专家系统

随着技术的不断进步，AI正在改变我们的生活、工作和思考方式，为人类社会带来巨大的变革和可能性。
"""
            }
        ]
        
        # 创建示例文档
        for doc in sample_docs:
            with open(doc['path'], 'w', encoding='utf-8') as f:
                f.write(doc['content'])
        
        # 重新获取文档列表
        default_docs = get_all_documents(documents_dir)
    
    # 加载文档
    documents = rag_system.load_documents(default_docs)
    
    # 分割文档
    split_docs = rag_system.split_documents(documents)
    
    # 创建向量存储
    rag_system.create_vectorstore(split_docs)
    
    # 创建 RAG 检索链
    rag_chain = rag_system.create_rag_chain()
    
    return rag_system, rag_chain

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query_documents():
    global rag_system, rag_chain
    
    # 获取用户问题
    query = request.form.get('query', '')
    
    if not query:
        return jsonify({"error": "请输入问题"})
    
    try:
        # 如果 RAG 系统未初始化，则初始化
        if rag_system is None or rag_chain is None:
            rag_system, rag_chain = initialize_rag_system()
        
        # 查询文档
        answer = rag_system.query_documents(query, rag_chain)
        
        return jsonify({"answer": answer})
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/upload', methods=['POST'])
def upload_document():
    global rag_system, rag_chain
    
    if 'file' not in request.files:
        return jsonify({"error": "没有文件上传"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "未选择文件"})
    
    # 保存文件
    file_path = os.path.join('./rag/documents', file.filename)
    file.save(file_path)
    
    try:
        # 加载并处理上传的文档
        uploaded_docs = rag_system.load_documents([file_path])
        uploaded_split_docs = rag_system.split_documents(uploaded_docs)
        rag_system.create_vectorstore(uploaded_split_docs)
        
        # 重新创建 RAG 检索链
        rag_chain = rag_system.create_rag_chain()
        
        return jsonify({"message": "文档上传成功"})
    
    except Exception as e:
        return jsonify({"error": str(e)})

def create_templates_dir():
    """创建模板目录"""
    os.makedirs('templates', exist_ok=True)

def create_index_html():
    """创建 index.html 模板"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>智能文档问答助手</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
            }
            #chat-container {
                border: 1px solid #ddd;
                min-height: 300px;
                max-height: 500px;
                overflow-y: auto;
                padding: 10px;
                margin-bottom: 10px;
            }
            #query-input {
                width: 100%;
                padding: 10px;
                margin-bottom: 10px;
            }
            #upload-file {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <h1>📚 智能文档问答助手</h1>
        
        <div>
            <input type="file" id="upload-file" accept=".txt,.pdf,.docx">
            <button onclick="uploadDocument()">上传文档</button>
        </div>
        
        <div id="chat-container"></div>
        
        <input type="text" id="query-input" placeholder="请输入您的问题">
        <button onclick="queryDocuments()">获取答案</button>

        <script>
            function addMessage(message, type) {
                const chatContainer = document.getElementById('chat-container');
                const messageElement = document.createElement('div');
                messageElement.classList.add(type);
                messageElement.textContent = message;
                chatContainer.appendChild(messageElement);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            function queryDocuments() {
                const queryInput = document.getElementById('query-input');
                const query = queryInput.value.trim();
                
                if (!query) {
                    alert('请输入问题');
                    return;
                }

                addMessage('您: ' + query, 'user-message');

                fetch('/query', {
                    method: 'POST',
                    body: new URLSearchParams({query: query}),
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        addMessage('错误: ' + data.error, 'error-message');
                    } else {
                        addMessage('助手: ' + data.answer, 'assistant-message');
                    }
                })
                .catch(error => {
                    addMessage('错误: ' + error, 'error-message');
                });

                queryInput.value = '';
            }

            function uploadDocument() {
                const fileInput = document.getElementById('upload-file');
                const file = fileInput.files[0];

                if (!file) {
                    alert('请选择文件');
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        addMessage('上传错误: ' + data.error, 'error-message');
                    } else {
                        addMessage('文档上传成功: ' + file.name, 'system-message');
                    }
                })
                .catch(error => {
                    addMessage('上传错误: ' + error, 'error-message');
                });

                fileInput.value = '';
            }
        </script>
    </body>
    </html>
    """
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # create_templates_dir()
    # create_index_html()
    
    # 初始化 RAG 系统
    initialize_rag_system()
    
    # 运行 Flask 应用
    app.run(debug=True, port=5000)

if __name__ == '__main__':
    main() 