import os
import streamlit as st
from document_rag_system import DocumentRAGSystem

def initialize_rag_system():
    """
    初始化 RAG 系统
    """
    rag_system = DocumentRAGSystem(
        api_key=st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        base_url=st.secrets.get("BASE_URL") or os.getenv("BASE_URL")
    )
    return rag_system

def load_documents(rag_system):
    """
    加载文档
    """
    # 默认文档路径
    default_docs = [
        './demo/rag/documents/sample.txt',
        './demo/rag/documents/sample.pdf'
    ]
    
    # 确保文档目录存在
    os.makedirs('./demo/rag/documents', exist_ok=True)
    
    # 加载文档
    documents = rag_system.load_documents(default_docs)
    
    # 分割文档
    split_docs = rag_system.split_documents(documents)
    
    # 创建向量存储
    rag_system.create_vectorstore(split_docs)
    
    return rag_system

def main():
    # 设置页面标题和图标
    st.set_page_config(
        page_title="文档问答助手",
        page_icon="📚",
        layout="wide"
    )
    
    # 页面标题
    st.title("📚 智能文档问答助手")
    
    # 初始化 RAG 系统
    rag_system = initialize_rag_system()
    rag_system = load_documents(rag_system)
    
    # 创建 RAG 检索链
    rag_chain = rag_system.create_rag_chain()
    
    # 文件上传区域
    st.sidebar.header("📤 上传文档")
    uploaded_files = st.sidebar.file_uploader(
        "选择文档", 
        type=['txt', 'pdf', 'docx'], 
        accept_multiple_files=True
    )
    
    # 处理上传的文件
    if uploaded_files:
        uploaded_paths = []
        for uploaded_file in uploaded_files:
            # 保存上传的文件
            file_path = os.path.join('./demo/rag/documents', uploaded_file.name)
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            uploaded_paths.append(file_path)
        
        # 加载并处理上传的文档
        uploaded_docs = rag_system.load_documents(uploaded_paths)
        uploaded_split_docs = rag_system.split_documents(uploaded_docs)
        rag_system.create_vectorstore(uploaded_split_docs)
        
        # 重新创建 RAG 检索链
        rag_chain = rag_system.create_rag_chain()
        
        st.sidebar.success(f"已成功上传 {len(uploaded_files)} 个文档")
    
    # 问答区域
    st.header("💬 文档问答")
    
    # 用户输入问题
    query = st.text_input("请输入您的问题", placeholder="例如：文档的主要内容是什么？")
    
    # 问答按钮
    if st.button("获取答案") or query:
        if query:
            with st.spinner("正在检索并生成答案..."):
                try:
                    # 查询文档
                    answer = rag_system.query_documents(query, rag_chain)
                    
                    # 显示答案
                    st.success("📝 查询结果:")
                    st.write(answer)
                    
                except Exception as e:
                    st.error(f"查询出错: {e}")
        else:
            st.warning("请输入问题")
    
    # 页脚
    st.markdown("---")
    st.markdown("🤖 基于 LangChain 的智能文档问答系统")

if __name__ == "__main__":
    main() 