import os
import tiktoken  # 用于计算token数量
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import fitz  # PyMuPDF
import base64
import io
from PIL import Image
from openai import OpenAI

# 加载环境变量
try:
    # 获取当前文件所在目录
    current_dir = Path(__file__).resolve().parent
    
    # 尝试向上查找项目根目录
    project_root = current_dir.parent  # 项目根目录是当前目录的父目录
    env_path = project_root / '.env'
    
    if env_path.exists():
        print(f"从 {env_path} 加载环境变量")
        load_dotenv(dotenv_path=env_path)
    else:
        # 如果在父目录没找到，尝试当前目录
        print(f"在 {project_root} 未找到 .env 文件，尝试从当前目录加载")
        load_dotenv()
except Exception as e:
    print(f"加载 .env 文件时出错: {e}")
    # 如果出错，尝试默认加载
    load_dotenv()


class PDFAnalyzer:
    """PDF分析器，使用OpenAI的视觉模型分析PDF文件内容"""

    # 检验报告分析专家的系统提示词
    SYSTEM_PROMPT = """# Role: 检验报告分析专家

## Profile
- language: 中文
- description: 专业解析和结构化各类检验检测报告的领域专家
- background: 具备五年以上质量检测行业经验，熟悉GB/T标准体系
- personality: 严谨、细致、逻辑性强
- expertise: 文本信息抽取、报告格式解析、标准规范验证
- target_audience: 质量管理人员、检测机构、供应链审计人员

## Skills

1. 核心分析能力
   - 报告类型识别: 通过标题和关键词判定报告有效性
   - 结构化数据提取: 精准定位关键字段并建立映射关系
   - 标准规范验证: 核验检测标准与行业规范的匹配度
   - 逻辑关联分析: 建立企业-产品-检测项三级关联

2. 辅助处理能力
   - 自然语言处理: 处理非结构化文本数据
   - 格式异常检测: 识别扫描件中的缺失/模糊信息
   - 上下文关联: 处理公章/签名区域的关联信息
   - 多语义解析: 识别不同表述方式的同类字段

## Rules

1. 基本原则：
   - 完整性校验: 必须包含报告类型判断与基本字段验证
   - 准确性优先: 无法确认的字段保持null值
   - 格式强制约束: 日期统一转换为ISO8601格式
   - 原文保留原则: 结论字段必须保留原始文字

2. 行为准则：
   - 字段处理规则: 委托单位与生产单位相同时需显式重复
   - 错误分级机制: 关键字段缺失触发code=1错误
   - 模糊匹配原则: "NO."与"报告编号"视为同义字段
   - 多位置校验: 公章区域信息优先于正文内容

3. 限制条件：
   - 格式约束: 严格维持三级JSON结构
   - 安全要求: 自动屏蔽个人隐私信息
   - 字段容错: 允许检测明细部分字段缺失
   - 版本控制: 仅支持现行有效标准版本

4. 字段提取规则：
   1. 判断报告类型：
      - 若标题含"检验/检测报告"且包含"检测机构""检验依据""检测结论"等关键词，则判定为检测报告（isTestReport=true），否则返回code=1。
   2. 提取基础信息：
      - reportName：提取标题（如"检验检测报告"）。
      - reportNumber：从报告编码，或NO开始提取
      - issueDate：从"签发日期"提取日期。
      - expirationDate：从"有效期"提取日期。
      - testResult：若结论含"符合""通过"等关键词，则标记为"true"，否则为false。
      - conclusion：提取结论原文（如"符合Q/JSH 0011S-2022..."）。
   3. 提取商品信息：
      - productName：从"样品名称"提取完整名称（含括号内容）。
      - specification：从"规格型号"提取（如800g/袋）。
      - brand：从"商标"提取品牌名称。
   4. 提取企业信息：
      - client：从"委托单位"提取全称。
      - manufacturer：从"标称生产单位"提取全称，若为空则用委托单位。
      - inspectionAgency：检验机构。
   5. 检测明细：
      - item: 检测项目名称,
      - standard: 检测标准,
      - result: 检测结果
      - judge: 判定
   6. 响应结构：
   - 返回JSON包含code、msg、data三级：
      - code=0时，data按字段返回结构化数据。
      - code=1时，msg需用中文描述具体错误（如"未找到"）。
   - 无法识别的字段保留为null
   - 日期格式自动转换为标准格式
   - 特别注意公章、签名附近的文字信息

## Workflows

- 目标: 将非结构化检测报告转为标准化数据
- 步骤 1: 文档有效性验证（关键词匹配+格式校验）
- 步骤 2: 多维度字段提取（基础信息→商品信息→机构信息→检测明细）
- 步骤 3: 逻辑完整性检查（生产商推导+结论语句分析）
- 预期结果: 符合行业规范的结构化数据

## OutputFormat

1. 主输出格式：
   - format: application/json
   - structure: 三级嵌套结构（code/message/data）
   - style: 紧凑型无冗余字段
   - special_requirements: 中文字符不编码

2. 格式规范：
   - indentation: 2空格缩进
   - sections: 保持字段顺序不变
   - highlighting: 关键布尔值加粗

3. 验证规则：
   - validation: JSON Schema验证
   - constraints: 基础信息段为必选
   - error_handling: 错误代码分级处理

4. 示例说明：
   1. 示例1：
      - 标题: 标准检测报告
      - 格式类型: 成功响应
      - 说明: 包含完整检测明细
      - 示例内容: |
          {
            "code": "0",
            "message": "success",
            "data": {
              "reportValidation": {
                "isInspectionReport": true,
                "testResult": true
              },
              "basicInfo": {
                "reportName": "食品安全检测报告",
                "reportNumber": "LAB-2023-08752",
                "issueDate": "2023-11-15",
                "expirationDate": "2024-12-26",
                "conclusion": "所检项目符合GB 2763-2021标准要求"
              },
              "organizationInfo": {
                "client": "某某食品有限公司",
                "manufacturer": "某某食品生产厂",
                "inspectionAgency": "国家食品质量监督检验中心"
              },
              "productInfo": {
                "productName": "特级初榨橄榄油",
                "specification": "500ml×2瓶/礼盒",
                "brand": "绿野仙踪"
              },
              "inspectionResults": [
                  {
                  "item": "色泽",
                  "standard": "Q/JSH 0011S-2022/3.2",
                  "result": "均匀一致，正反两面无深浅差别",
                  "judge": "符合"
                   },
                  {
                    "item": "气味",
                    "standard": "Q/JSH 0011S-2022/3.2",
                    "result": "无酸味、霉味及其它异味",
                    "judge": "符合"
                  },
                  {
                    "item": "杂质",
                    "standard": "Q/JSH 0011S-2022/3.2",
                    "result": "无肉眼可见的杂质",
                    "judge": "符合"
                  },
                  {
                    "item": "口感",
                    "standard": "GB/T 40636-2021/附录A",
                    "result": "煮熟后口感不牙碜",
                    "judge": "符合"
                  },
                  {
                    "item": "水分",
                    "standard": "GB 5009.3-2016/第一法",
                    "result": "12.4%",
                    "judge": "符合"
                  },
                  {
                    "item": "酸度",
                    "standard": "GB 5009.239-2016/第一法",
                    "result": "0.969 mL/10g",
                    "judge": "符合"
                  },
                  {
                    "item": "熟断条率",
                    "standard": "GB/T 40636-2021/附录C.2.2",
                    "result": "0%",
                    "judge": "符合"
                  },
                  {
                    "item": "自然断条率",
                    "standard": "GB/T 40636-2021/附录B",
                    "result": "0%",
                    "judge": "符合"
                  },
                  {
                    "item": "烹调损失率",
                    "standard": "GB/T 40636-2021/附录C.2.3",
                    "result": "7.6%",
                    "judge": "符合"
                  },
                  {
                    "item": "脱氢乙酸及其钠盐（以脱氢乙酸计）",
                    "standard": "GB 5009.121-2016/第二法",
                    "result": "未检出(定量限 0.005g/kg)",
                    "judge": "符合"
                  },
                  {
                    "item": "铅（以Pb计）",
                    "standard": "GB 5009.12-2017/第一法",
                    "result": "未检出(定量限 0.04mg/kg)",
                        "judge": "符合"
                  },
                  {
                    "item": "标签",
                    "standard": "GB 7718-2011",
                    "result": "应符合GB 7718-2011规定",
                    "judge": "符合"
                  }
              ]
            }
          }

   2. 示例2：
      - 标题: 无效报告
      - 格式类型: 错误响应
      - 说明: 缺少检测结论
      - 示例内容: |
          {
            "code": "1",
            "message": "未检测到有效的结论字段",
            "data": null
          }

## Initialization
作为检验报告分析专家，你必须遵守上述Rules，按照Workflows执行任务，并按照OutputFormat输出。
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qvq-72b-preview",
        max_tokens: int = 4000
    ):
        """初始化PDF分析器"""
        # 设置API密钥
        self.api_key = api_key or os.getenv("VLLM_API_KEY") 
        if not self.api_key:
            raise ValueError("未找到API密钥，请在.env文件中设置VLLM_API_KEY，或者在初始化时提供")
        
        # 设置基础URL
        self.base_url = base_url or os.getenv("VLLM_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 设置模型和参数
        self.model = model
        self.max_tokens = max_tokens
        
        # 初始化OpenAI客户端 (使用新版API)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 初始化token计数器
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except:
            # 如果找不到特定模型的编码，使用默认编码
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        print(f"PDF分析器初始化完成，使用模型: {self.model}")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            print(f"计算token数量时出错: {e}")
            # 使用简单的估算方法作为备选
            return len(text) // 4
    
    def count_message_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的token数量"""
        token_count = 0
        
        for message in messages:
            # 基础token (每条消息的固定开销)
            token_count += 4  # 每条消息的基础token数
            
            # 角色token
            if "role" in message:
                token_count += 1  # 角色名称的token数
            
            # 内容token
            if "content" in message:
                content = message["content"]
                if isinstance(content, str):
                    token_count += self.count_tokens(content)
                elif isinstance(content, list):
                    # 处理多模态内容
                    for item in content:
                        if item.get("type") == "text":
                            token_count += self.count_tokens(item.get("text", ""))
                        elif item.get("type") == "image_url":
                            # 图像URL的token计算是近似的
                            # 根据OpenAI的文档，低分辨率图像约为85个token，高分辨率约为170个token
                            # 这里我们假设所有图像都是高分辨率
                            token_count += 170
        
        return token_count
    
    def extract_images_from_pdf(self, pdf_path: str, max_pages: int = 5) -> List[str]:
        """从PDF提取图像并转换为base64编码"""
        try:
            # 确保文件路径是绝对路径
            pdf_path = self._ensure_absolute_path(pdf_path)
            print(f"尝试打开PDF文件: {pdf_path}")
            
            # 检查文件是否存在
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"找不到文件: {pdf_path}")
            
            # 打开PDF文件
            doc = fitz.open(pdf_path)
            
            # 限制页数
            page_count = min(len(doc), max_pages)
            print(f"处理PDF: {pdf_path}，共{page_count}页")
            
            # 存储base64编码的图像
            base64_images = []
            
            # 遍历页面
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                
                # 将页面渲染为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以提高清晰度
                
                # 将图像转换为PIL格式
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 将图像转换为base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)  # 使用JPEG格式，质量85%
                img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # 添加到列表
                base64_images.append(img_base64)
                
                print(f"已处理第{page_num+1}页，图像大小: {len(img_base64)//1024}KB")
            
            return base64_images
            
        except Exception as e:
            print(f"提取PDF图像时出错: {e}")
            raise
    
    def _ensure_absolute_path(self, file_path: str) -> str:
        """确保文件路径是绝对路径"""
        if os.path.isabs(file_path):
            return file_path
        
        # 尝试多个可能的位置
        # 1. 相对于当前工作目录
        cwd_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(cwd_path):
            return cwd_path
        
        # 2. 相对于脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, file_path)
        if os.path.exists(script_path):
            return script_path
        
        # 3. 相对于vl目录
        vl_dir = Path(__file__).resolve().parent
        vl_path = os.path.join(vl_dir, file_path)
        if os.path.exists(vl_path):
            return vl_path
        
        # 4. 相对于项目根目录
        project_root = vl_dir.parent
        root_path = os.path.join(project_root, file_path)
        if os.path.exists(root_path):
            return root_path
        
        # 如果都找不到，返回原始路径，让调用函数处理错误
        print(f"警告: 无法找到文件 '{file_path}'，尝试过以下路径:")
        print(f"  - {cwd_path}")
        print(f"  - {script_path}")
        print(f"  - {vl_path}")
        print(f"  - {root_path}")
        return file_path
    
    def analyze_pdf(self, pdf_path: str, prompt: Optional[str] = None, max_pages: int = 5) -> Tuple[str, Dict[str, int]]:
        """分析PDF内容并返回结果以及token使用情况"""
        try:
            # 确保文件路径是绝对路径
            pdf_path = self._ensure_absolute_path(pdf_path)
            
            # 提取图像
            base64_images = self.extract_images_from_pdf(pdf_path, max_pages)
            
            if not base64_images:
                return "无法从PDF中提取图像", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            # 如果没有提供自定义提示，使用默认提示
            if not prompt:
                prompt = "请分析这份检验报告，提取所有关键信息，并按照规定的JSON格式输出。"
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # 添加图像到用户消息
            for img_base64 in base64_images:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })
            
            # 计算输入token数量
            input_tokens = self.count_message_tokens(messages)
            print(f"输入token数量: {input_tokens}")
            
            # 调用API (使用新版API)
            print(f"调用OpenAI API，分析PDF内容...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            
            # 获取结果
            result = response.choices[0].message.content
            
            # 计算输出token数量
            output_tokens = self.count_tokens(result)
            print(f"输出token数量: {output_tokens}")
            
            # 计算总token数量
            total_tokens = input_tokens + output_tokens
            print(f"总token数量: {total_tokens}")
            
            # 返回结果和token使用情况
            token_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
            
            return result, token_usage
            
        except Exception as e:
            print(f"分析PDF时出错: {e}")
            return f"分析PDF时出错: {str(e)}", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = None) -> str:
        """从PDF中提取文本内容"""
        try:
            # 确保文件路径是绝对路径
            pdf_path = self._ensure_absolute_path(pdf_path)
            
            # 打开PDF文件
            doc = fitz.open(pdf_path)
            
            # 限制页数
            if max_pages is None:
                max_pages = len(doc)
            page_count = min(len(doc), max_pages)
            
            # 存储文本
            text = ""
            
            # 遍历页面
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            return text
            
        except Exception as e:
            print(f"提取PDF文本时出错: {e}")
            return f"提取PDF文本时出错: {str(e)}"
    
    def analyze_pdf_text(self, pdf_path: str, prompt: Optional[str] = None, max_pages: int = None) -> Tuple[str, Dict[str, int]]:
        """分析PDF文本内容并返回结果以及token使用情况"""
        try:
            # 确保文件路径是绝对路径
            pdf_path = self._ensure_absolute_path(pdf_path)
            
            # 提取文本
            text = self.extract_text_from_pdf(pdf_path, max_pages)
            
            if not text:
                return "无法从PDF中提取文本", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            # 如果没有提供自定义提示，使用默认提示
            if not prompt:
                prompt = "请分析这份检验报告，提取所有关键信息，并按照规定的JSON格式输出。"
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\n文档内容：\n{text}"
                }
            ]
            
            # 计算输入token数量
            input_tokens = self.count_message_tokens(messages)
            print(f"输入token数量: {input_tokens}")
            
            # 调用API (使用新版API)
            print(f"调用OpenAI API，分析PDF文本内容...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            
            # 获取结果
            result = response.choices[0].message.content
            
            # 计算输出token数量
            output_tokens = self.count_tokens(result)
            print(f"输出token数量: {output_tokens}")
            
            # 计算总token数量
            total_tokens = input_tokens + output_tokens
            print(f"总token数量: {total_tokens}")
            
            # 返回结果和token使用情况
            token_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
            
            return result, token_usage
            
        except Exception as e:
            print(f"分析PDF文本时出错: {e}")
            return f"分析PDF文本时出错: {str(e)}", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    def save_result_with_usage(self, result: str, token_usage: Dict[str, int], output_path: str = None) -> str:
        """保存分析结果和token使用情况到文件"""
        try:
            # 如果没有提供输出路径，生成一个默认路径
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"pdf_analysis_result_{timestamp}.md"
            
            # 构建输出内容
            output_content = f"""# PDF分析结果

## Token使用情况
- 输入Token数量: {token_usage['input_tokens']}
- 输出Token数量: {token_usage['output_tokens']}
- 总Token数量: {token_usage['total_tokens']}

## 分析结果
{result}
"""
            
            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            
            print(f"分析结果已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"保存结果时出错: {e}")
            return None


# 示例用法
if __name__ == "__main__":
    # 初始化分析器
    analyzer = PDFAnalyzer()
    
    # 获取当前工作目录并打印
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    
    # 列出当前目录下的所有PDF文件
    pdf_files = [f for f in os.listdir(current_dir) if f.endswith('.pdf')]
    if pdf_files:
        print(f"当前目录下的PDF文件: {pdf_files}")
    else:
        print("当前目录下没有PDF文件")
    
    # 分析PDF
    pdf_path = "挂面检测报告2.pdf"  # 替换为实际的PDF路径
    result, token_usage = analyzer.analyze_pdf(
        pdf_path=pdf_path,
        prompt="请分析这份检验报告，提取所有关键信息，并按照规定的JSON格式输出。",
        max_pages=3
    )
    
    # 保存结果和token使用情况
    output_path = analyzer.save_result_with_usage(result, token_usage)
    
    # 打印结果
    print("\n" + "="*50)
    print("PDF分析结果")
    print("="*50 + "\n")
    print(result)
    
    # 打印token使用情况
    print("\n" + "="*50)
    print("Token使用情况")
    print("="*50)
    print(f"输入Token数量: {token_usage['input_tokens']}")
    print(f"输出Token数量: {token_usage['output_tokens']}")
    print(f"总Token数量: {token_usage['total_tokens']}") 