# LangChain 上下文管理与工具调用完整指南

## 目录
1. [概述](#概述)
2. [上下文管理](#上下文管理)
3. [工具调用机制](#工具调用机制)
4. [状态管理](#状态管理)
5. [最佳实践](#最佳实践)
6. [实际应用案例](#实际应用案例)

## 概述

LangChain 是一个强大的框架，专为构建基于大语言模型的应用程序而设计。本文档将深入探讨 LangChain 如何处理两个核心概念：**上下文管理**和**工具调用**。

### 核心概念
- **上下文（Context）**：在对话或任务执行过程中保持和传递的信息
- **工具调用（Tool Calling）**：让 AI 能够调用外部函数或服务来完成特定任务
- **状态管理（State Management）**：在复杂工作流中维护和更新应用状态

## 上下文管理

### 1. 对话历史记忆

LangChain 提供多种记忆机制来管理对话上下文：

#### ConversationBufferMemory - 完整历史记忆

```python
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 初始化对话历史记忆
buffer_memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="chat_history"
)

# 创建带记忆的对话模板
chat_prompt = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),  # 插入历史对话
    ("human", "{input}"),
])

# 使用记忆
memory_content = buffer_memory.load_memory_variables({})
response = chain.invoke({
    "input": "你好，我叫小明",
    **memory_content
})

# 保存对话到记忆
buffer_memory.save_context(
    {"input": "你好，我叫小明"},
    {"output": response}
)
```

**特点：**
- ✅ 保留完整的对话历史
- ✅ 适合短期对话
- ❌ 长对话会消耗大量 token

#### ConversationSummaryMemory - 摘要记忆

```python
from langchain.memory import ConversationSummaryMemory

# 初始化摘要记忆
summary_memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="chat_summary"
)

# 摘要记忆会自动将长对话压缩为摘要
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "对话历史摘要：{chat_summary}"),
    ("human", "{input}"),
])
```

**特点：**
- ✅ 节省 token 消耗
- ✅ 适合长期对话
- ❌ 可能丢失细节信息

### 2. LangGraph 中的状态管理

LangGraph 通过 TypedDict 定义状态结构，实现更精细的上下文控制：

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END, START

class QAState(TypedDict):
    """问答状态定义"""
    question: str        # 用户问题
    thoughts: str        # AI 思考过程
    final_answer: str    # 最终答案

class SimpleQADemo:
    def __init__(self):
        self.workflow = self._create_workflow()
    
    async def think_step(self, state: QAState) -> Dict:
        """思考步骤 - 分析问题"""
        result = await self.llm.ainvoke([
            {"role": "system", "content": "仔细思考如何回答用户问题"},
            {"role": "user", "content": state["question"]}
        ])
        return {"thoughts": result.content}
    
    async def answer_step(self, state: QAState) -> Dict:
        """回答步骤 - 基于思考给出答案"""
        result = await self.llm.ainvoke([
            {"role": "system", "content": "根据思考过程给出清晰答案"},
            {"role": "user", "content": f"问题：{state['question']}\n思考：{state['thoughts']}"}
        ])
        return {"final_answer": result.content}
    
    def _create_workflow(self):
        """创建工作流图"""
        workflow = StateGraph(QAState)
        
        # 添加节点
        workflow.add_node("think", self.think_step)
        workflow.add_node("answer", self.answer_step)
        
        # 定义执行流程
        workflow.add_edge(START, "think")
        workflow.add_edge("think", "answer")
        workflow.add_edge("answer", END)
        
        return workflow.compile()
```

**状态管理特点：**
- 🔄 **状态传递**：每个节点都能访问和修改全局状态
- 📊 **类型安全**：通过 TypedDict 确保状态结构正确
- 🔀 **灵活控制**：可以根据状态决定执行路径

### 3. 上下文在多智能体系统中的应用

```python
class TeamState(TypedDict):
    """团队协作状态"""
    task: str           # 任务描述
    research: str       # 研究结果
    draft: str         # 初稿内容
    feedback: str      # 审核反馈
    final_output: str  # 最终输出

class TeamCollaborationDemo:
    async def research_step(self, state: TeamState) -> Dict:
        """研究员收集信息"""
        result = await self.llm.ainvoke([
            {"role": "system", "content": "你是专业研究员，收集分析相关信息"},
            {"role": "user", "content": f"研究主题：{state['task']}"}
        ])
        return {"research": result.content}
    
    async def write_step(self, state: TeamState) -> Dict:
        """作家基于研究撰写内容"""
        result = await self.llm.ainvoke([
            {"role": "system", "content": "你是专业作家，创作结构良好的内容"},
            {"role": "user", "content": f"任务：{state['task']}\n研究结果：{state['research']}"}
        ])
        return {"draft": result.content}
    
    async def review_step(self, state: TeamState) -> Dict:
        """审核员审查内容质量"""
        result = await self.llm.ainvoke([
            {"role": "system", "content": "你是严格的审核员，评估内容质量"},
            {"role": "user", "content": f"任务：{state['task']}\n内容：{state['draft']}"}
        ])
        
        feedback = result.content
        if "通过" in feedback:
            return {"feedback": feedback, "final_output": state["draft"]}
        return {"feedback": feedback}
```

## 工具调用机制

### 1. 基础工具定义

LangChain 支持多种方式定义和使用工具：

#### 使用 Pydantic 定义工具

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticToolsParser

class Add(BaseModel):
    """加法工具"""
    a: int = Field(..., description="第一个整数")
    b: int = Field(..., description="第二个整数")

class Multiply(BaseModel):
    """乘法工具"""
    a: int = Field(..., description="第一个整数")
    b: int = Field(..., description="第二个整数")

# 实际执行函数
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

class ToolCallingDemo:
    def __init__(self):
        self.tools = [Add, Multiply]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def execute_tools(self, query: str) -> List[int]:
        """执行工具并返回结果"""
        # 解析工具调用
        chain = self.llm_with_tools | PydanticToolsParser(tools=self.tools)
        tool_calls = chain.invoke(query)
        
        results = []
        for tool_call in tool_calls:
            if isinstance(tool_call, Add):
                results.append(add(tool_call.a, tool_call.b))
            elif isinstance(tool_call, Multiply):
                results.append(multiply(tool_call.a, tool_call.b))
        
        return results
```

#### 使用 @tool 装饰器

```python
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """搜索网页信息"""
    # 实际搜索逻辑
    return f"搜索结果：{query}"

@tool 
def calculate_math(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)  # 注意：实际应用中需要安全处理
        return f"计算结果：{result}"
    except:
        return "计算错误"

# 绑定工具到模型
tools = [search_web, calculate_math]
llm_with_tools = llm.bind_tools(tools)
```

### 2. 搜索工具集成

```python
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

def init_search_tool():
    """初始化搜索工具"""
    search = SerpAPIWrapper(
        params={
            "engine": "google",
            "api_key": os.getenv("SERPAPI_API_KEY")
        }
    )
    
    return Tool(
        name="Search",
        func=search.run,
        description="用于搜索最新信息的工具。输入应该是搜索查询。"
    )

# 在工作流中使用搜索工具
async def execute_step(self, state: PlanExecuteState) -> Dict:
    """执行计划步骤"""
    task = state["plan"][0]
    
    if "搜索" in task and search_tool:
        # 执行搜索
        search_query = task.replace("搜索", "").strip()
        search_result = search_tool.run(search_query)
        result_content = f"搜索结果: {search_result}"
    else:
        # 使用 LLM 处理
        result = await self.llm.ainvoke([
            {"role": "user", "content": task}
        ])
        result_content = result.content
    
    return {"past_steps": [(task, result_content)]}
```

### 3. 自定义工具集成

```python
class CustomToolDemo:
    def __init__(self):
        self.tools = self._create_custom_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _create_custom_tools(self):
        """创建自定义工具集"""
        
        @tool
        def get_weather(city: str) -> str:
            """获取指定城市的天气信息"""
            # 模拟天气 API 调用
            weather_data = {
                "北京": "晴天，15°C",
                "上海": "多云，18°C", 
                "广州": "小雨，22°C"
            }
            return weather_data.get(city, f"无法获取{city}的天气信息")
        
        @tool
        def translate_text(text: str, target_lang: str = "英语") -> str:
            """翻译文本到目标语言"""
            # 模拟翻译服务
            return f"已将'{text}'翻译为{target_lang}"
        
        @tool
        def save_note(content: str) -> str:
            """保存笔记内容"""
            # 模拟保存操作
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"笔记已保存 [{timestamp}]: {content[:50]}..."
        
        return [get_weather, translate_text, save_note]
    
    async def process_with_tools(self, user_input: str) -> str:
        """使用工具处理用户输入"""
        # 让 LLM 决定是否需要使用工具
        response = self.llm_with_tools.invoke(user_input)
        
        # 如果有工具调用
        if response.tool_calls:
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # 执行相应的工具
                for tool in self.tools:
                    if tool.name == tool_name:
                        result = tool.run(tool_args)
                        tool_results.append(f"{tool_name}: {result}")
            
            # 将工具结果返回给 LLM 生成最终回复
            final_prompt = f"""
            用户请求: {user_input}
            工具执行结果: {'; '.join(tool_results)}
            
            请基于工具结果给出完整回复。
            """
            
            final_response = await self.llm.ainvoke(final_prompt)
            return final_response.content
        
        return response.content
```

## 状态管理

### 1. 输入输出状态分离

```python
# 定义不同层次的状态
class InputState(TypedDict):
    """输入状态"""
    text: str
    target_lang: str

class OutputState(TypedDict):
    """输出状态"""
    translated_text: str
    confidence: float

class OverallState(InputState, OutputState):
    """整体状态，包含中间状态"""
    detected_lang: str
    translation_steps: List[Dict]

# 在工作流中使用分层状态
workflow = StateGraph(OverallState, input=InputState, output=OutputState)
```

### 2. 状态更新和传递

```python
async def detect_language(self, state: InputState) -> Dict:
    """检测语言步骤"""
    result = await self.llm.ainvoke([
        {"role": "system", "content": "检测文本语言，只返回语言名称"},
        {"role": "user", "content": state['text']}
    ])
    
    # 返回的字典会自动合并到状态中
    return {"detected_lang": result.content}

async def translate_text(self, state: OverallState) -> Dict:
    """翻译步骤"""
    result = await self.llm.ainvoke([
        {"role": "system", "content": f"将{state['detected_lang']}翻译为{state['target_lang']}"},
        {"role": "user", "content": state['text']}
    ])
    
    return {
        "translated_text": result.content,
        "confidence": 0.95,
        "translation_steps": state.get("translation_steps", []) + [
            {"step": "translate", "input": state['text'], "output": result.content}
        ]
    }
```

### 3. 条件状态控制

```python
def should_continue(self, state: PlanExecuteState) -> str:
    """根据状态决定执行路径"""
    # 检查是否有最终响应
    if "response" in state and state["response"]:
        return END
    
    # 检查执行步数限制
    if len(state.get("past_steps", [])) >= 5:
        return END
    
    # 检查是否还有计划要执行
    if not state.get("plan"):
        return END
    
    # 继续执行
    return "agent"

# 在工作流中使用条件控制
workflow.add_conditional_edges(
    "replan",
    should_continue,
    {
        END: END,
        "agent": "agent"
    }
)
```

## 最佳实践

### 1. 上下文管理最佳实践

#### ✅ 合理选择记忆类型
```python
# 短期对话 - 使用 ConversationBufferMemory
short_term_memory = ConversationBufferMemory(return_messages=True)

# 长期对话 - 使用 ConversationSummaryMemory  
long_term_memory = ConversationSummaryMemory(llm=llm)

# 混合模式 - 根据对话长度动态切换
def get_appropriate_memory(conversation_length):
    if conversation_length < 10:
        return ConversationBufferMemory(return_messages=True)
    else:
        return ConversationSummaryMemory(llm=llm)
```

#### ✅ 状态结构设计
```python
# 好的实践：清晰的状态层次
class WorkflowState(TypedDict):
    # 输入相关
    user_input: str
    task_type: str
    
    # 处理过程
    analysis_result: str
    processing_steps: List[Dict]
    
    # 输出相关
    final_result: str
    confidence_score: float
    
    # 元数据
    execution_time: float
    error_messages: List[str]
```

#### ❌ 避免的反模式
```python
# 不好的实践：混乱的状态结构
class BadState(TypedDict):
    data: str  # 太模糊
    stuff: Any  # 类型不明确
    result1: str  # 命名不清晰
    result2: str
    temp_var: str  # 临时变量不应在状态中
```

### 2. 工具调用最佳实践

#### ✅ 工具设计原则
```python
@tool
def well_designed_tool(
    query: str, 
    max_results: int = 5,
    language: str = "zh"
) -> str:
    """
    设计良好的搜索工具
    
    Args:
        query: 搜索查询，应该是具体的关键词
        max_results: 最大结果数量，默认5个
        language: 结果语言，默认中文
    
    Returns:
        格式化的搜索结果字符串
        
    Example:
        >>> search_web("人工智能发展趋势", max_results=3)
        "1. AI技术突破...\n2. 行业应用...\n3. 未来展望..."
    """
    # 输入验证
    if not query.strip():
        return "错误：搜索查询不能为空"
    
    if max_results <= 0:
        return "错误：结果数量必须大于0"
    
    try:
        # 实际搜索逻辑
        results = perform_search(query, max_results, language)
        return format_results(results)
    except Exception as e:
        return f"搜索失败：{str(e)}"
```

#### ✅ 错误处理和重试
```python
async def execute_with_retry(self, tool_call, max_retries=3):
    """带重试机制的工具执行"""
    for attempt in range(max_retries):
        try:
            result = await tool_call()
            return {"success": True, "result": result}
        except Exception as e:
            if attempt == max_retries - 1:
                return {"success": False, "error": str(e)}
            
            # 等待后重试
            await asyncio.sleep(2 ** attempt)
    
    return {"success": False, "error": "超过最大重试次数"}
```

### 3. 性能优化

#### ✅ 并行处理
```python
from langchain_core.runnables import RunnableParallel

# 并行执行多个独立任务
parallel_chain = RunnableParallel({
    "search_results": search_chain,
    "analysis": analysis_chain,
    "summary": summary_chain
})

result = await parallel_chain.ainvoke(input_data)
```

#### ✅ 流式处理
```python
async def stream_workflow_results(self, input_data):
    """流式返回工作流结果"""
    async for event in self.workflow.astream(input_data):
        for node_name, node_result in event.items():
            if node_name != "__end__":
                # 实时返回中间结果
                yield {
                    "node": node_name,
                    "result": node_result,
                    "timestamp": datetime.now().isoformat()
                }
```

## 实际应用案例

### 1. 智能客服系统

```python
class CustomerServiceBot:
    def __init__(self):
        self.memory = ConversationSummaryMemory(llm=self.llm)
        self.tools = [
            self.create_order_lookup_tool(),
            self.create_faq_search_tool(),
            self.create_human_handoff_tool()
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    async def handle_customer_query(self, query: str, customer_id: str):
        """处理客户查询"""
        # 加载客户历史对话
        memory_context = self.memory.load_memory_variables({"customer_id": customer_id})
        
        # 构建完整上下文
        full_context = f"""
        客户ID: {customer_id}
        对话历史: {memory_context.get('history', '')}
        当前查询: {query}
        """
        
        # 让 AI 决定使用哪些工具
        response = await self.llm_with_tools.ainvoke(full_context)
        
        # 执行工具调用
        if response.tool_calls:
            tool_results = await self.execute_tools(response.tool_calls)
            final_response = await self.generate_final_response(query, tool_results)
        else:
            final_response = response.content
        
        # 保存对话到记忆
        self.memory.save_context(
            {"input": query, "customer_id": customer_id},
            {"output": final_response}
        )
        
        return final_response
```

### 2. 研究分析助手

```python
class ResearchAssistant:
    def __init__(self):
        self.workflow = self._create_research_workflow()
    
    def _create_research_workflow(self):
        """创建研究工作流"""
        workflow = StateGraph(ResearchState)
        
        # 研究流程节点
        workflow.add_node("plan", self.create_research_plan)
        workflow.add_node("search", self.search_information)  
        workflow.add_node("analyze", self.analyze_findings)
        workflow.add_node("synthesize", self.synthesize_report)
        workflow.add_node("review", self.review_quality)
        
        # 流程控制
        workflow.add_edge(START, "plan")
        workflow.add_edge("plan", "search")
        workflow.add_edge("search", "analyze")
        workflow.add_edge("analyze", "synthesize")
        workflow.add_edge("synthesize", "review")
        
        # 条件分支
        workflow.add_conditional_edges(
            "review",
            self.decide_next_step,
            {
                "improve": "analyze",  # 需要改进时回到分析步骤
                "complete": END        # 质量满足要求时结束
            }
        )
        
        return workflow.compile()
    
    async def conduct_research(self, topic: str, requirements: str):
        """执行研究任务"""
        initial_state = {
            "topic": topic,
            "requirements": requirements,
            "research_plan": "",
            "search_results": [],
            "analysis": "",
            "report": "",
            "quality_score": 0.0
        }
        
        final_result = await self.workflow.ainvoke(initial_state)
        return final_result["report"]
```

### 3. 多模态内容生成器

```python
class MultiModalContentGenerator:
    def __init__(self):
        self.text_llm = ChatOpenAI(model="gpt-4")
        self.image_tools = self._setup_image_tools()
        self.audio_tools = self._setup_audio_tools()
        
        self.workflow = self._create_content_workflow()
    
    def _create_content_workflow(self):
        """创建多模态内容生成工作流"""
        workflow = StateGraph(ContentState)
        
        # 内容生成节点
        workflow.add_node("analyze_request", self.analyze_content_request)
        workflow.add_node("generate_text", self.generate_text_content)
        workflow.add_node("generate_images", self.generate_image_content)
        workflow.add_node("generate_audio", self.generate_audio_content)
        workflow.add_node("integrate_content", self.integrate_all_content)
        
        # 流程定义
        workflow.add_edge(START, "analyze_request")
        workflow.add_edge("analyze_request", "generate_text")
        
        # 并行生成不同模态内容
        workflow.add_conditional_edges(
            "generate_text",
            self.determine_content_types,
            {
                "text_only": "integrate_content",
                "with_images": "generate_images", 
                "with_audio": "generate_audio",
                "multimedia": "generate_images"
            }
        )
        
        workflow.add_edge("generate_images", "generate_audio")
        workflow.add_edge("generate_audio", "integrate_content")
        workflow.add_edge("integrate_content", END)
        
        return workflow.compile()
    
    async def create_content(self, request: str, content_type: str):
        """创建多模态内容"""
        initial_state = {
            "request": request,
            "content_type": content_type,
            "text_content": "",
            "image_content": [],
            "audio_content": [],
            "final_content": {}
        }
        
        result = await self.workflow.ainvoke(initial_state)
        return result["final_content"]
```

## 总结

LangChain 通过以下机制实现强大的上下文管理和工具调用能力：

### 上下文管理核心要点：
1. **多层次记忆系统**：从简单的缓冲记忆到智能的摘要记忆
2. **状态驱动架构**：通过 TypedDict 定义清晰的状态结构
3. **流程化上下文传递**：在工作流节点间自动传递和更新上下文
4. **灵活的上下文控制**：根据业务逻辑动态调整上下文内容

### 工具调用核心要点：
1. **标准化工具接口**：通过 Pydantic 模型和装饰器定义工具
2. **智能工具选择**：AI 自动判断何时以及如何使用工具
3. **错误处理和重试**：确保工具调用的可靠性
4. **结果整合**：将工具结果无缝整合到对话流程中

### 最佳实践总结：
- 🎯 **明确状态设计**：清晰定义状态结构和生命周期
- 🔧 **合理工具拆分**：每个工具应该功能单一、职责明确
- 🔄 **优雅错误处理**：预期并妥善处理各种异常情况
- ⚡ **性能优化**：合理使用并行处理和流式输出
- 📊 **监控和调试**：记录关键状态变化和工具调用结果

通过掌握这些概念和实践，你可以构建出功能强大、用户体验优秀的 AI 应用程序。LangChain 的灵活性使得它能够适应各种复杂的业务场景，从简单的聊天机器人到复杂的多智能体协作系统。
