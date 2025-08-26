"""
完整的上下文工程演示 (Complete Context Engineering Demo)
在一个演示中展示所有四个核心概念：写入、选择、压缩、隔离

这个演示模拟一个智能研究助手，展示：
1. Write Context: 将信息写入状态和长期记忆
2. Select Context: 从状态、记忆、工具和知识库中选择相关信息
3. Compress Context: 压缩长对话和工具输出
4. Isolate Context: 使用多智能体和沙盒隔离不同类型的处理
"""

import os
import uuid
import json
from typing import TypedDict, List, Dict, Any, Literal
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import init_embeddings
from langchain.tools.retriever import create_retriever_tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.prebuilt import create_react_agent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track
from rich.logging import RichHandler
import time
import logging

console = Console()

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("ContextEngineering")

# ================================
# 1. 环境设置和工具函数
# ================================

def setup_environment():
    """设置必要的环境变量"""
    required_keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    for key in required_keys:
        if not os.environ.get(key):
            api_key = input(f"请输入您的 {key}: ")
            os.environ[key] = api_key

def log_context_operation(operation_type: str, location: str, key: str, content_preview: str):
    """记录上下文操作到日志"""
    logger.info(f"🔄 [{operation_type}] {location} | Key: {key} | Content: {content_preview[:100]}...")

def log_context_selection(source: str, selected_items: int, details: str = ""):
    """记录上下文选择操作"""
    logger.info(f"🎯 [SELECT] From {source} | Selected: {selected_items} items | {details}")

def display_section_header(title: str, description: str, color: str = "blue"):
    """显示章节标题"""
    console.print(Panel(
        f"[bold]{title}[/bold]\n{description}",
        border_style=color,
        padding=(1, 2)
    ))

# ================================
# 2. 状态定义
# ================================

class ComprehensiveState(TypedDict):
    """综合演示的状态定义"""
    # 基本信息
    research_topic: str
    current_query: str
    conversation_round: int
    
    # Write Context - 写入的信息
    initial_analysis: str
    research_plan: str
    collected_data: List[str]
    tool_results: List[Dict]
    
    # Select Context - 选择的上下文
    selected_memories: List[Dict]
    relevant_tools: List[str]
    retrieved_knowledge: str
    context_selections: List[Dict]
    
    # Compress Context - 压缩的信息
    conversation_summary: str
    compressed_findings: str
    
    # Isolate Context - 隔离的处理结果
    specialist_reports: Dict[str, str]
    
    # 消息历史和对话管理
    messages: List[Any]
    conversation_history: List[Dict]
    
    # 元数据和日志
    processing_steps: List[str]
    context_operations_log: List[Dict]
    token_usage: Dict[str, int]

# ================================
# 3. 核心组件初始化
# ================================

def create_research_tools():
    """创建多个研究工具"""
    def web_search_tool(query: str) -> str:
        """模拟网络搜索工具"""
        search_results = {
            "人工智能": "AI技术在教育、医疗、金融等领域广泛应用，预计2024年市场规模将达到5000亿美元。",
            "教育": "在线教育市场快速增长，个性化学习成为主流趋势，AI辅导系统效果显著。",
            "机器学习": "深度学习、强化学习等技术不断发展，在图像识别、自然语言处理等领域取得突破。",
            "default": f"关于'{query}'的搜索结果：这是一个重要的研究领域，具有广阔的发展前景和应用价值。"
        }
        for key in search_results:
            if key in query.lower():
                return search_results[key]
        return search_results["default"]
    
    def data_analysis_tool(data_type: str) -> str:
        """模拟数据分析工具"""
        analysis_results = {
            "教育数据": "学生学习效果提升25%，教师工作效率提高40%，个性化推荐准确率达到85%。",
            "市场数据": "AI教育市场年复合增长率15%，头部企业占据60%市场份额。",
            "用户数据": "用户满意度92%，日活跃用户增长30%，平均学习时长增加45分钟。",
            "default": f"对{data_type}的分析显示：数据质量良好，趋势向上，具有重要参考价值。"
        }
        for key in analysis_results:
            if key in data_type:
                return analysis_results[key]
        return analysis_results["default"]
    
    def literature_search_tool(topic: str) -> str:
        """模拟文献搜索工具"""
        return f"找到关于'{topic}'的相关文献15篇，包括顶级期刊论文8篇，会议论文7篇。主要研究方向包括技术创新、应用实践、效果评估等。"
    
    return {
        "web_search": web_search_tool,
        "data_analysis": data_analysis_tool,
        "literature_search": literature_search_tool
    }

def initialize_components():
    """初始化所有必要的组件"""
    setup_environment()
    
    # LLM
    llm = init_chat_model("anthropic:claude-3-5-sonnet-20241022", temperature=0.7)
    
    # 存储组件
    checkpointer = InMemorySaver()
    memory_store = InMemoryStore()
    namespace = ("demo_user", "research_assistant")
    
    # 嵌入和向量存储
    embeddings = init_embeddings("openai:text-embedding-3-small")
    
    # 扩展的知识库
    sample_docs = [
        "人工智能在教育中的应用包括个性化学习、智能辅导系统和自动评估。研究表明AI可以提高学习效率30%。",
        "机器学习算法可以分析学生的学习模式，提供定制化的学习路径。adaptive learning系统已在多所学校试点。",
        "自然语言处理技术使得智能聊天机器人能够回答学生的问题。ChatGPT等大模型在教育领域应用广泛。",
        "计算机视觉可以用于自动批改作业和检测学术不端行为。准确率已达到95%以上。",
        "深度学习在语音识别和语言翻译方面有重要应用。实时翻译技术支持多语言教学。",
        "区块链技术可用于学历认证和成绩管理，确保教育数据的真实性和不可篡改性。",
        "虚拟现实和增强现实为教育带来沉浸式学习体验，特别适用于历史、地理等学科。",
        "大数据分析帮助教育机构了解学习趋势，优化课程设计和教学方法。"
    ]
    
    # 创建向量存储
    vectorstore = InMemoryVectorStore.from_texts(sample_docs, embeddings)
    retriever = vectorstore.as_retriever()
    
    # 创建检索工具
    retriever_tool = create_retriever_tool(
        retriever,
        "knowledge_retriever",
        "搜索和检索相关的知识信息"
    )
    
    # 创建研究工具
    research_tools = create_research_tools()
    
    return llm, checkpointer, memory_store, namespace, retriever_tool, embeddings, research_tools

# ================================
# 4. Write Context - 写入上下文
# ================================

def write_initial_analysis(state: ComprehensiveState, store: BaseStore) -> Dict:
    """写入初始分析到状态和长期记忆"""
    display_section_header(
        "📝 WRITE CONTEXT - 写入上下文", 
        "将初始分析写入状态（草稿本）和长期记忆"
    )
    
    llm, _, _, namespace, _, _, _ = initialize_components()
    
    console.print("🧠 正在生成初始分析...")
    
    # 检查是否有历史上下文
    round_num = state.get("conversation_round", 1)
    current_query = state.get("current_query", state['research_topic'])
    
    prompt = f"""作为一个研究助手，请对主题 "{state['research_topic']}" 进行分析。
    
当前查询：{current_query}
对话轮次：第 {round_num} 轮

请提供：
1. 主题的关键概念
2. 可能的研究方向  
3. 需要关注的重点领域
4. 针对当前查询的具体建议"""
    
    response = llm.invoke(prompt)
    analysis = response.content
    
    # 记录写入操作到日志
    log_context_operation(
        "WRITE", 
        "Long-term Memory", 
        f"analysis_{state['research_topic'].replace(' ', '_')}_round_{round_num}",
        analysis
    )
    
    # 写入长期记忆
    memory_key = f"analysis_{state['research_topic'].replace(' ', '_')}_round_{round_num}"
    store.put(
        namespace,
        memory_key,
        {
            "topic": state['research_topic'],
            "analysis": analysis,
            "timestamp": time.time(),
            "round": round_num,
            "query": current_query,
            "type": "initial_analysis"
        }
    )
    
    # 记录写入操作到状态
    context_op = {
        "operation": "WRITE",
        "location": "State + Long-term Memory", 
        "key": "initial_analysis",
        "content_length": len(analysis),
        "timestamp": time.time(),
        "round": round_num
    }
    
    log_context_operation("WRITE", "State", "initial_analysis", analysis)
    
    console.print(Panel(analysis[:200] + "...", title="✅ 初始分析已写入", border_style="green"))
    
    return {
        "initial_analysis": analysis,
        "conversation_round": round_num,
        "processing_steps": state.get("processing_steps", []) + [f"第{round_num}轮：写入初始分析"],
        "context_operations_log": state.get("context_operations_log", []) + [context_op],
        "messages": state.get("messages", []) + [AIMessage(content=f"第{round_num}轮分析：{analysis[:100]}...")]
    }

def multi_tool_research(state: ComprehensiveState, store: BaseStore) -> Dict:
    """多轮工具调用进行研究"""
    display_section_header(
        "🔧 MULTI-TOOL RESEARCH - 多工具研究",
        "使用多个工具进行深入研究并记录所有操作"
    )
    
    llm, _, _, namespace, retriever_tool, _, research_tools = initialize_components()
    round_num = state.get("conversation_round", 1)
    
    console.print(f"🔍 第{round_num}轮：开始多工具研究...")
    
    tool_results = []
    
    # 工具调用序列
    tools_to_use = [
        ("knowledge_retriever", state['research_topic']),
        ("web_search", state['research_topic']),
        ("data_analysis", "教育数据"),
        ("literature_search", state['research_topic'])
    ]
    
    for i, (tool_name, query) in enumerate(tools_to_use, 1):
        console.print(f"🛠️  调用工具 {i}/{len(tools_to_use)}: {tool_name}")
        
        try:
            if tool_name == "knowledge_retriever":
                result = retriever_tool.invoke({"query": query})
            else:
                result = research_tools[tool_name](query)
            
            tool_result = {
                "tool": tool_name,
                "query": query,
                "result": result,
                "timestamp": time.time(),
                "round": round_num,
                "call_order": i
            }
            
            tool_results.append(tool_result)
            
            # 记录工具调用到日志和长期记忆
            log_context_operation(
                "WRITE",
                "Tool Results",
                f"{tool_name}_round_{round_num}_call_{i}",
                str(result)
            )
            
            # 将工具结果写入长期记忆
            store.put(
                namespace,
                f"tool_result_{tool_name}_round_{round_num}_call_{i}",
                tool_result
            )
            
            console.print(f"✅ {tool_name} 调用完成，结果已保存")
            time.sleep(0.5)  # 模拟处理时间
            
        except Exception as e:
            console.print(f"❌ {tool_name} 调用失败: {str(e)}")
            tool_results.append({
                "tool": tool_name,
                "query": query,
                "result": f"Error: {str(e)}",
                "timestamp": time.time(),
                "round": round_num,
                "call_order": i,
                "status": "failed"
            })
    
    # 记录所有工具调用操作
    context_op = {
        "operation": "WRITE",
        "location": "Tool Results + Long-term Memory",
        "key": f"multi_tool_results_round_{round_num}",
        "content_length": sum(len(str(r['result'])) for r in tool_results),
        "timestamp": time.time(),
        "round": round_num,
        "tools_used": len(tool_results)
    }
    
    console.print(Panel(
        f"完成 {len(tool_results)} 个工具调用，所有结果已写入上下文",
        title="✅ 多工具研究完成",
        border_style="green"
    ))
    
    return {
        "tool_results": state.get("tool_results", []) + tool_results,
        "processing_steps": state["processing_steps"] + [f"第{round_num}轮：多工具研究({len(tool_results)}个工具)"],
        "context_operations_log": state.get("context_operations_log", []) + [context_op]
    }

# ================================
# 5. Select Context - 选择上下文
# ================================

def comprehensive_context_selection(state: ComprehensiveState, store: BaseStore) -> Dict:
    """综合上下文选择 - 从多个来源选择相关信息"""
    display_section_header(
        "🎯 SELECT CONTEXT - 选择上下文",
        "从状态、记忆、工具结果中智能选择相关信息"
    )
    
    _, _, _, namespace, _, _, _ = initialize_components()
    round_num = state.get("conversation_round", 1)
    
    console.print(f"🔍 第{round_num}轮：开始综合上下文选择...")
    
    # 1. 从长期记忆中选择
    console.print("📚 从长期记忆中选择相关信息...")
    stored_items = list(store.search(namespace))
    selected_memories = []
    memory_selection_details = []
    
    for item in stored_items:
        # 选择与当前主题和轮次相关的记忆
        if (state['research_topic'].replace(' ', '_') in item.key or 
            f"round_{round_num}" in item.key or
            any(keyword in item.key for keyword in ["analysis", "tool_result", "plan"])):
            
            memory_item = {
                "key": item.key,
                "type": item.value.get("type", "unknown"),
                "round": item.value.get("round", "unknown"),
                "timestamp": item.value.get("timestamp", 0),
                "content_preview": str(item.value)[:150] + "..."
            }
            selected_memories.append(memory_item)
            memory_selection_details.append(f"Selected: {item.key} (type: {memory_item['type']})")
    
    log_context_selection("Long-term Memory", len(selected_memories), 
                         f"Topics: {[m['type'] for m in selected_memories]}")
    
    # 2. 从状态中选择当前轮次的信息
    console.print("📝 从当前状态中选择信息...")
    state_selections = []
    
    # 选择当前分析
    if state.get("initial_analysis"):
        state_selections.append({
            "source": "current_state",
            "key": "initial_analysis", 
            "content_length": len(state["initial_analysis"]),
            "preview": state["initial_analysis"][:100] + "..."
        })
        log_context_selection("Current State", 1, "initial_analysis")
    
    # 3. 从工具结果中选择
    console.print("🛠️  从工具结果中选择相关信息...")
    tool_selections = []
    recent_tool_results = state.get("tool_results", [])[-5:]  # 选择最近5个工具结果
    
    for tool_result in recent_tool_results:
        if tool_result.get("round") == round_num:
            tool_selections.append({
                "tool": tool_result["tool"],
                "query": tool_result["query"],
                "result_preview": str(tool_result["result"])[:100] + "...",
                "timestamp": tool_result["timestamp"]
            })
    
    log_context_selection("Tool Results", len(tool_selections),
                         f"Tools: {[t['tool'] for t in tool_selections]}")
    
    # 4. 智能相关性评分和过滤
    console.print("🧠 基于相关性进行智能过滤...")
    
    # 模拟智能选择逻辑
    current_query = state.get("current_query", state['research_topic'])
    relevant_keywords = current_query.lower().split()
    
    filtered_memories = []
    for memory in selected_memories:
        relevance_score = sum(1 for keyword in relevant_keywords 
                            if keyword in memory["key"].lower() or 
                               keyword in memory.get("content_preview", "").lower())
        if relevance_score > 0:
            memory["relevance_score"] = relevance_score
            filtered_memories.append(memory)
    
    # 按相关性排序
    filtered_memories.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    # 记录选择操作
    context_selections = {
        "memories": filtered_memories[:10],  # 最多选择10个最相关的记忆
        "state_info": state_selections,
        "tool_results": tool_selections,
        "selection_criteria": {
            "round": round_num,
            "query": current_query,
            "keywords": relevant_keywords
        },
        "total_selected": len(filtered_memories) + len(state_selections) + len(tool_selections)
    }
    
    context_op = {
        "operation": "SELECT",
        "sources": ["Long-term Memory", "Current State", "Tool Results"],
        "total_items": len(stored_items),
        "selected_items": context_selections["total_selected"],
        "timestamp": time.time(),
        "round": round_num,
        "selection_details": memory_selection_details
    }
    
    log_context_selection("Comprehensive Selection", 
                         context_selections["total_selected"],
                         f"From {len(stored_items)} available items")
    
    console.print(Panel(
        f"""选择完成统计：
📚 长期记忆: {len(filtered_memories)} 项
📝 当前状态: {len(state_selections)} 项  
🛠️  工具结果: {len(tool_selections)} 项
🎯 总计选择: {context_selections['total_selected']} 项""",
        title="✅ 综合上下文选择完成",
        border_style="green"
    ))
    
    return {
        "selected_memories": filtered_memories,
        "context_selections": [context_selections],
        "processing_steps": state["processing_steps"] + [f"第{round_num}轮：综合上下文选择({context_selections['total_selected']}项)"],
        "context_operations_log": state.get("context_operations_log", []) + [context_op]
    }

def select_tools_and_knowledge(state: ComprehensiveState) -> Dict:
    """选择相关工具并检索知识"""
    _, _, _, _, retriever_tool, _, _ = initialize_components()
    
    console.print("🔧 正在选择相关工具并检索知识...")
    
    # 模拟工具选择（基于主题）
    available_tools = [
        "数据分析工具", "文献检索工具", "统计分析工具", 
        "可视化工具", "机器学习工具", "自然语言处理工具"
    ]
    
    # 简单的工具选择逻辑
    relevant_tools = []
    topic_lower = state['research_topic'].lower()
    if "人工智能" in topic_lower or "ai" in topic_lower:
        relevant_tools.extend(["机器学习工具", "自然语言处理工具"])
    if "教育" in topic_lower:
        relevant_tools.extend(["数据分析工具", "统计分析工具"])
    if "分析" in topic_lower:
        relevant_tools.extend(["数据分析工具", "可视化工具"])
    
    # 使用检索工具获取知识
    try:
        retrieved_docs = retriever_tool.invoke({"query": state['research_topic']})
        retrieved_knowledge = retrieved_docs[:300] + "..."
    except Exception as e:
        retrieved_knowledge = f"检索知识时出错: {str(e)}"
    
    console.print(Panel(
        f"选择的工具: {', '.join(relevant_tools)}\n检索的知识: {retrieved_knowledge[:100]}...",
        title="✅ 工具和知识选择完成",
        border_style="green"
    ))
    
    return {
        "relevant_tools": relevant_tools,
        "retrieved_knowledge": retrieved_knowledge,
        "processing_steps": state["processing_steps"] + ["选择工具和检索知识"]
    }

# ================================
# 6. Compress Context - 压缩上下文
# ================================

def compress_conversation(state: ComprehensiveState) -> Dict:
    """压缩对话历史"""
    display_section_header(
        "🗜️ COMPRESS CONTEXT - 压缩上下文",
        "压缩长对话历史和工具输出以节省token"
    )
    
    llm, _, _, _, _, _, _ = initialize_components()
    
    console.print("📄 正在压缩对话历史...")
    
    # 模拟长对话历史
    long_conversation = f"""
用户查询: {state['user_query']}
初始分析: {state['initial_analysis']}
研究计划: {state['research_plan']}
选择的记忆: {json.dumps(state.get('selected_memories', []), ensure_ascii=False)}
相关工具: {', '.join(state.get('relevant_tools', []))}
检索的知识: {state.get('retrieved_knowledge', '')}
"""
    
    prompt = f"""请将以下长对话历史压缩成简洁的摘要，保留关键信息：

{long_conversation}

请提供一个简洁但完整的摘要，包含所有重要的决策和发现。"""
    
    response = llm.invoke(prompt)
    summary = response.content
    
    console.print(Panel(
        f"原始长度: {len(long_conversation)} 字符\n压缩后: {len(summary)} 字符\n压缩率: {(1 - len(summary)/len(long_conversation))*100:.1f}%",
        title="✅ 对话历史压缩完成",
        border_style="green"
    ))
    
    return {
        "conversation_summary": summary,
        "processing_steps": state["processing_steps"] + ["压缩对话历史"]
    }

def compress_findings(state: ComprehensiveState) -> Dict:
    """压缩研究发现"""
    llm, _, _, _, _, _, _ = initialize_components()
    
    console.print("📊 正在压缩研究发现...")
    
    # 模拟详细的研究发现
    detailed_findings = f"""
详细研究发现：

基于初始分析: {state['initial_analysis']}

根据研究计划: {state['research_plan']}

利用选择的工具: {', '.join(state.get('relevant_tools', []))}

参考检索的知识: {state.get('retrieved_knowledge', '')}

结合历史记忆: {len(state.get('selected_memories', []))} 项相关记录

综合分析表明该研究主题具有重要意义和广阔的应用前景。
"""
    
    prompt = f"""请将以下详细的研究发现压缩成核心要点：

{detailed_findings}

请提取最重要的3-5个关键发现，每个用一句话概括。"""
    
    response = llm.invoke(prompt)
    compressed = response.content
    
    console.print(Panel(
        compressed,
        title="✅ 研究发现压缩完成",
        border_style="green"
    ))
    
    return {
        "compressed_findings": compressed,
        "processing_steps": state["processing_steps"] + ["压缩研究发现"]
    }

# ================================
# 7. Isolate Context - 隔离上下文
# ================================

def isolate_with_specialists(state: ComprehensiveState) -> Dict:
    """使用专门的智能体隔离不同类型的分析"""
    display_section_header(
        "🏗️ ISOLATE CONTEXT - 隔离上下文",
        "使用多个专门的智能体隔离不同类型的处理"
    )
    
    llm, _, _, _, _, _, _ = initialize_components()
    
    console.print("👥 正在创建专门的智能体进行隔离分析...")
    
    # 定义不同的专家角色
    specialists = {
        "技术专家": "分析技术实现和挑战",
        "教育专家": "评估教育影响和应用",
        "商业专家": "分析市场前景和商业价值"
    }
    
    specialist_reports = {}
    
    for specialist, role in track(specialists.items(), description="专家分析中..."):
        prompt = f"""你是一个{specialist}，专门负责{role}。

研究主题：{state['research_topic']}
压缩的发现：{state.get('compressed_findings', '')}

请从你的专业角度提供分析报告，重点关注你的专业领域。"""
        
        response = llm.invoke(prompt)
        specialist_reports[specialist] = response.content
        
        console.print(f"✅ {specialist}报告完成")
        time.sleep(0.5)  # 模拟处理时间
    
    console.print(Panel(
        f"完成了 {len(specialist_reports)} 个专家的隔离分析",
        title="✅ 专家隔离分析完成",
        border_style="green"
    ))
    
    return {
        "specialist_reports": specialist_reports,
        "processing_steps": state["processing_steps"] + ["多智能体隔离分析"]
    }

def sandbox_simulation(state: ComprehensiveState) -> Dict:
    """模拟沙盒环境隔离计算"""
    console.print("🏖️ 正在模拟沙盒环境进行隔离计算...")
    
    # 模拟沙盒中的计算
    sandbox_results = {
        "data_processing": "在沙盒中安全处理了敏感数据",
        "model_training": "在隔离环境中训练了机器学习模型",
        "security_check": "通过了安全检查，没有发现恶意代码"
    }
    
    console.print(Panel(
        "\n".join([f"• {k}: {v}" for k, v in sandbox_results.items()]),
        title="✅ 沙盒隔离计算完成",
        border_style="green"
    ))
    
    return {
        "processing_steps": state["processing_steps"] + ["沙盒隔离计算"]
    }

# ================================
# 8. 主工作流构建
# ================================

def conversation_router(state: ComprehensiveState) -> Literal["continue_conversation", "end_conversation"]:
    """决定是否继续对话"""
    round_num = state.get("conversation_round", 1)
    max_rounds = 3  # 最多3轮对话
    
    if round_num < max_rounds:
        return "continue_conversation"
    else:
        return "end_conversation"

def prepare_next_round(state: ComprehensiveState) -> Dict:
    """准备下一轮对话"""
    current_round = state.get("conversation_round", 1)
    next_round = current_round + 1
    
    # 模拟新的用户查询
    next_queries = [
        "请详细分析技术实现的挑战",
        "分析市场前景和商业价值", 
        "总结关键发现和建议"
    ]
    
    if next_round <= len(next_queries):
        next_query = next_queries[next_round - 1]
    else:
        next_query = "请提供最终总结"
    
    console.print(Panel(
        f"🔄 准备第 {next_round} 轮对话\n新查询: {next_query}",
        title="多轮对话",
        border_style="cyan"
    ))
    
    return {
        "conversation_round": next_round,
        "current_query": next_query,
        "processing_steps": state["processing_steps"] + [f"开始第{next_round}轮对话"]
    }

def build_comprehensive_workflow():
    """构建完整的上下文工程工作流"""
    llm, checkpointer, memory_store, namespace, retriever_tool, embeddings, research_tools = initialize_components()
    
    # 创建状态图
    workflow = StateGraph(ComprehensiveState)
    
    # 添加所有节点
    workflow.add_node("write_analysis", write_initial_analysis)
    workflow.add_node("multi_tool_research", multi_tool_research)
    workflow.add_node("select_context", comprehensive_context_selection)
    workflow.add_node("compress_conv", compress_conversation)
    workflow.add_node("compress_findings", compress_findings)
    workflow.add_node("isolate_specialists", isolate_with_specialists)
    workflow.add_node("prepare_next_round", prepare_next_round)
    workflow.add_node("final_summary", sandbox_simulation)
    
    # 定义工作流程 - 支持多轮对话
    workflow.add_edge(START, "write_analysis")
    workflow.add_edge("write_analysis", "multi_tool_research")
    workflow.add_edge("multi_tool_research", "select_context")
    workflow.add_edge("select_context", "compress_conv")
    workflow.add_edge("compress_conv", "compress_findings")
    workflow.add_edge("compress_findings", "isolate_specialists")
    
    # 条件路由：决定是否继续对话
    workflow.add_conditional_edges(
        "isolate_specialists",
        conversation_router,
        {
            "continue_conversation": "prepare_next_round",
            "end_conversation": "final_summary"
        }
    )
    
    # 继续对话的循环
    workflow.add_edge("prepare_next_round", "write_analysis")
    workflow.add_edge("final_summary", END)
    
    # 编译工作流
    app = workflow.compile(checkpointer=checkpointer, store=memory_store)
    
    return app, memory_store, namespace

# ================================
# 9. 结果展示和分析
# ================================

def display_comprehensive_results(result: Dict, memory_store: InMemoryStore, namespace):
    """展示完整的演示结果"""
    console.print(Panel(
        "🎉 多轮对话上下文工程演示结果",
        title="演示完成",
        border_style="bold green",
        padding=(1, 2)
    ))
    
    # 创建结果表格
    table = Table(title="上下文工程演示总结")
    table.add_column("功能", style="cyan", no_wrap=True)
    table.add_column("实现", style="magenta")
    table.add_column("结果", style="green")
    
    table.add_row(
        "Write Context",
        "多轮写入状态和长期记忆",
        f"✅ 分析: {len(result.get('initial_analysis', ''))} 字符\n✅ 工具结果: {len(result.get('tool_results', []))} 个\n✅ 轮次: {result.get('conversation_round', 1)} 轮"
    )
    
    table.add_row(
        "Select Context", 
        "智能选择多源上下文",
        f"✅ 记忆: {len(result.get('selected_memories', []))} 项\n✅ 上下文选择: {len(result.get('context_selections', []))} 次\n✅ 选择操作: {len(result.get('context_operations_log', []))} 个"
    )
    
    table.add_row(
        "Compress Context",
        "压缩对话和发现", 
        f"✅ 对话摘要: {len(result.get('conversation_summary', ''))} 字符\n✅ 压缩发现: {len(result.get('compressed_findings', ''))} 字符"
    )
    
    table.add_row(
        "Isolate Context",
        "多智能体和沙盒隔离",
        f"✅ 专家报告: {len(result.get('specialist_reports', {}))} 个\n✅ 沙盒隔离: 完成"
    )
    
    console.print(table)
    
    # 显示处理步骤
    console.print(Panel(
        "\n".join([f"{i+1}. {step}" for i, step in enumerate(result.get('processing_steps', []))]),
        title="🔄 处理步骤",
        border_style="blue"
    ))
    
    # 显示上下文操作日志
    if result.get('context_operations_log'):
        console.print(Panel(
            "\n".join([
                f"[{op.get('round', '?')}] {op.get('operation', 'UNKNOWN')} -> {op.get('location', 'Unknown')} "
                f"({op.get('selected_items', op.get('content_length', '?'))} items/chars)"
                for op in result.get('context_operations_log', [])
            ]),
            title="📝 上下文操作日志",
            border_style="yellow"
        ))
    
    # 显示长期记忆状态
    stored_items = list(memory_store.search(namespace))
    console.print(Panel(
        f"长期记忆中保存了 {len(stored_items)} 项记录:\n" + 
        "\n".join([
            f"• {item.key}: {item.value.get('type', 'unknown')} "
            f"(Round {item.value.get('round', '?')})"
            for item in stored_items
        ]),
        title="🧠 长期记忆状态",
        border_style="purple"
    ))

# ================================
# 10. 主演示函数
# ================================

def run_complete_demo():
    """运行完整的多轮对话上下文工程演示"""
    console.print(Panel(
        "[bold blue]🚀 LangGraph 多轮对话上下文工程演示[/bold blue]\n\n"
        "这个演示将展示：\n"
        "🔄 多轮对话管理\n"
        "🛠️  多次工具调用\n"
        "📝 Write Context - 写入上下文（带日志）\n"
        "🎯 Select Context - 选择上下文（带日志）\n" 
        "🗜️ Compress Context - 压缩上下文\n"
        "🏗️ Isolate Context - 隔离上下文\n\n"
        "[yellow]注意：所有上下文操作都会记录到日志中[/yellow]",
        title="多轮对话上下文工程演示",
        border_style="bold blue",
        padding=(2, 4)
    ))
    
    # 构建工作流
    app, memory_store, namespace = build_comprehensive_workflow()
    
    # 配置
    config = {"configurable": {"thread_id": "multi_round_demo_1"}}
    
    # 初始输入
    initial_state = {
        "research_topic": "人工智能在教育中的应用",
        "current_query": "请帮我深入分析人工智能在教育领域的应用现状",
        "conversation_round": 1,
        "processing_steps": [],
        "context_operations_log": [],
        "conversation_history": [],
        "messages": [HumanMessage(content="开始多轮对话上下文工程演示")],
        "tool_results": [],
        "token_usage": {"input": 0, "output": 0}
    }
    
    console.print(f"\n📚 研究主题: {initial_state['research_topic']}")
    console.print(f"❓ 初始查询: {initial_state['current_query']}")
    console.print(f"🔄 将进行多轮对话，每轮都会进行完整的上下文工程操作\n")
    
    # 运行工作流
    logger.info("开始执行多轮对话上下文工程流程")
    console.print("🔄 开始执行多轮对话上下文工程流程...\n")
    
    result = app.invoke(initial_state, config)
    
    # 显示结果
    display_comprehensive_results(result, memory_store, namespace)
    
    # 显示最终的日志摘要
    console.print(Panel(
        f"""📊 演示统计：
🔄 对话轮次: {result.get('conversation_round', 1)} 轮
🛠️  工具调用: {len(result.get('tool_results', []))} 次
📝 上下文操作: {len(result.get('context_operations_log', []))} 个
🧠 长期记忆项: {len(list(memory_store.search(namespace)))} 个
📋 处理步骤: {len(result.get('processing_steps', []))} 步

✅ 所有上下文写入和选择操作都已记录到日志中！""",
        title="📈 演示完成统计",
        border_style="bold cyan"
    ))
    
    return result, memory_store

if __name__ == "__main__":
    try:
        result, store = run_complete_demo()
        console.print("\n✨ 演示完成！所有上下文工程功能都已成功展示。")
    except KeyboardInterrupt:
        console.print("\n❌ 演示被用户中断")
    except Exception as e:
        console.print(f"\n❌ 演示过程中出现错误: {str(e)}")
        console.print("请检查环境配置和依赖包是否正确安装。")
