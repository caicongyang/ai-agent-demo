import os
from flask import Flask, render_template, request, jsonify
from document_rag_system import DocumentRAGSystem

app = Flask(__name__, template_folder='templates')

# 全局 RAG 系统
rag_system = None
rag_chain = None

def initialize_rag_system():
    """
    初始化 RAG 系统
    """
    global rag_system, rag_chain
    
    rag_system = DocumentRAGSystem(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("BASE_URL")
    )
    
    # 默认文档路径
    default_docs = [
        './rag/documents/sample.txt',
        './rag/documents/sample.pdf'
    ]
    
    # 确保文档目录存在
    os.makedirs('./rag/documents', exist_ok=True)
    
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
    create_templates_dir()
    create_index_html()
    
    # 初始化 RAG 系统
    initialize_rag_system()
    
    # 运行 Flask 应用
    app.run(debug=True, port=5000)

if __name__ == '__main__':
    main() 