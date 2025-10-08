import os
import json
import logging
import html
import re
import markdown
import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from datetime import datetime, timedelta
import requests
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 加载项目根目录的 .env 文件
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    print(f"✅ 已尝试加载环境变量文件: {env_path}")
except ImportError:
    print("⚠️ 未安装 python-dotenv，无法自动加载 .env 文件")
    print("   可以运行: pip install python-dotenv")
except Exception as e:
    print(f"⚠️ 加载 .env 文件时出错: {e}")

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("weixin-publisher")


class WeixinRenderer(mistune.HTMLRenderer):
    """专门为微信公众号优化的自定义渲染器 - 增强版"""
    
    def __init__(self):
        super().__init__(escape=False)
        # 微信公众号样式配置 - 全面优化版
        self.styles = {
            'body': '''
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; 
                line-height: 1.75; 
                color: #2c3e50; 
                font-size: 16px; 
                margin: 0; 
                padding: 20px; 
                background: #ffffff;
                word-wrap: break-word;
                letter-spacing: 0.5px;
            '''.strip().replace('\n', ' '),
            
            'h1': '''
                font-size: 28px; 
                font-weight: 700; 
                color: #1a1a1a; 
                margin: 40px 0 25px 0; 
                padding: 15px 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                position: relative;
                line-height: 1.3;
            '''.strip().replace('\n', ' '),
            
            'h2': '''
                font-size: 24px; 
                font-weight: 600; 
                color: #2c3e50; 
                margin: 35px 0 20px 0; 
                padding: 12px 20px 12px 45px; 
                background: linear-gradient(90deg, #f8f9fa 0%, #ffffff 100%);
                border-left: 6px solid #e74c3c; 
                border-radius: 0 8px 8px 0;
                position: relative;
                box-shadow: 0 2px 10px rgba(231, 76, 60, 0.15);
                line-height: 1.4;
            '''.strip().replace('\n', ' ') + '''
                &::before {
                    content: "📌";
                    position: absolute;
                    left: 15px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 18px;
                }
            ''',
            
            'h3': '''
                font-size: 20px; 
                font-weight: 600; 
                color: #2c3e50; 
                margin: 25px 0 15px 0; 
                padding: 10px 20px 10px 40px; 
                background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                border-left: 5px solid #f39c12; 
                border-radius: 6px;
                position: relative;
                box-shadow: 0 2px 8px rgba(243, 156, 18, 0.2);
                line-height: 1.4;
            '''.strip().replace('\n', ' '),
            
            'h4': '''
                font-size: 18px; 
                font-weight: 600; 
                color: #2c3e50; 
                margin: 20px 0 12px 0; 
                padding: 8px 15px 8px 35px; 
                background: linear-gradient(90deg, #e8f5e8 0%, #ffffff 100%);
                border-left: 4px solid #27ae60;
                border-radius: 4px;
                position: relative;
                line-height: 1.4;
            '''.strip().replace('\n', ' '),
            
            'h5': '''
                font-size: 17px; 
                font-weight: 600; 
                color: #34495e; 
                margin: 18px 0 10px 0;
                padding: 6px 12px;
                border-bottom: 2px solid #9b59b6;
                display: inline-block;
                line-height: 1.4;
            '''.strip().replace('\n', ' '),
            
            'h6': '''
                font-size: 16px; 
                font-weight: 600; 
                color: #7f8c8d; 
                margin: 15px 0 8px 0;
                padding: 4px 8px;
                border-left: 3px solid #95a5a6;
                line-height: 1.4;
            '''.strip().replace('\n', ' '),
            
            'p': '''
                margin: 18px 0; 
                text-align: justify; 
                text-indent: 2em; 
                line-height: 1.8;
                color: #2c3e50;
                font-size: 16px;
                word-spacing: 2px;
            '''.strip().replace('\n', ' '),
            
            'blockquote': '''
                margin: 25px 0; 
                padding: 20px 25px 20px 50px; 
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-left: 6px solid #6c757d; 
                border-radius: 0 12px 12px 0; 
                font-style: italic; 
                color: #495057; 
                box-shadow: 0 4px 15px rgba(108, 117, 125, 0.15);
                position: relative;
                font-size: 15px;
                line-height: 1.7;
            '''.strip().replace('\n', ' '),
            
            'code_inline': '''
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                color: white;
                padding: 3px 8px; 
                border-radius: 6px; 
                font-family: "SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", monospace; 
                font-size: 14px; 
                margin: 0 3px;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(255, 107, 107, 0.3);
            '''.strip().replace('\n', ' '),
            
            'code_block': '''
                background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                color: #e2e8f0; 
                padding: 25px; 
                border-radius: 12px; 
                overflow-x: auto; 
                margin: 25px 0; 
                font-family: "SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", monospace; 
                font-size: 14px; 
                line-height: 1.6; 
                box-shadow: 0 8px 25px rgba(45, 55, 72, 0.3);
                border: 1px solid #4a5568;
                position: relative;
            '''.strip().replace('\n', ' '),
            
            'ul': '''
                margin: 15px 0; 
                padding-left: 0; 
                list-style: none;
            '''.strip().replace('\n', ' '),
            
            'ol': '''
                margin: 15px 0; 
                padding-left: 0; 
                list-style: none;
                counter-reset: ol-counter;
            '''.strip().replace('\n', ' '),
            
            'li': '''
                margin: 0; 
                padding: 1px 0 1px 35px; 
                position: relative; 
                list-style: none;
                line-height: 1.4;
                color: #2c3e50;
            '''.strip().replace('\n', ' '),
            
            'table': '''
                width: 100%; 
                border-collapse: collapse; 
                margin: 25px 0; 
                background: white; 
                border-radius: 12px; 
                overflow: hidden; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                border: 1px solid #e9ecef;
            '''.strip().replace('\n', ' '),
            
            'th': '''
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                color: white; 
                padding: 15px 20px; 
                text-align: left; 
                font-weight: 600; 
                font-size: 15px;
                letter-spacing: 0.5px;
            '''.strip().replace('\n', ' '),
            
            'td': '''
                padding: 15px 20px; 
                border-bottom: 1px solid #e9ecef; 
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.5;
            '''.strip().replace('\n', ' '),
            
            'tr_even': '''
                background: linear-gradient(90deg, #f8f9fa 0%, #ffffff 100%);
            '''.strip().replace('\n', ' '),
            
            'a': '''
                color: #3498db; 
                text-decoration: none; 
                border-bottom: 2px solid transparent; 
                transition: all 0.3s ease;
                font-weight: 500;
                padding: 2px 4px;
                border-radius: 4px;
            '''.strip().replace('\n', ' ') + '''
                &:hover {
                    background: rgba(52, 152, 219, 0.1);
                    border-bottom-color: #3498db;
                }
            ''',
            
            'strong': '''
                color: #e74c3c; 
                font-weight: 700;
                background: linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(231, 76, 60, 0.05) 100%);
                padding: 2px 4px;
                border-radius: 4px;
            '''.strip().replace('\n', ' '),
            
            'em': '''
                color: #8e44ad; 
                font-style: italic;
                background: linear-gradient(135deg, rgba(142, 68, 173, 0.1) 0%, rgba(142, 68, 173, 0.05) 100%);
                padding: 2px 4px;
                border-radius: 4px;
            '''.strip().replace('\n', ' '),
            
            'hr': '''
                border: none; 
                height: 3px; 
                background: linear-gradient(90deg, transparent, #bdc3c7, transparent); 
                margin: 40px 0;
                border-radius: 2px;
            '''.strip().replace('\n', ' ')
        }
        
        # 列表项符号配置
        self.list_symbols = {
            'ul': ['🔸', '▪️', '◦', '▫️'],
            'ol_styles': ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']
        }
        
        # 当前列表层级
        self.list_level = 0
        self.ol_counter = 0
    
    def heading(self, text, level):
        """自定义标题渲染"""
        style_key = f'h{level}'
        style = self.styles.get(style_key, self.styles['h6'])
        return f'<h{level} style="{style}">{text}</h{level}>\n'
    
    def paragraph(self, text):
        """自定义段落渲染 - 增强版"""
        # 检查是否是特殊段落（如包含特殊标记）
        if text.strip().startswith('💡') or text.strip().startswith('⚠️') or text.strip().startswith('❗'):
            # 提示框样式段落
            if text.strip().startswith('💡'):
                bg_color = 'linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%)'
                border_color = '#27ae60'
                icon = '💡'
            elif text.strip().startswith('⚠️'):
                bg_color = 'linear-gradient(135deg, #fff3cd 0%, #fefefe 100%)'
                border_color = '#ffc107'
                icon = '⚠️'
            else:  # ❗
                bg_color = 'linear-gradient(135deg, #f8d7da 0%, #fefefe 100%)'
                border_color = '#dc3545'
                icon = '❗'
            
            tip_style = f'''
                margin: 20px 0;
                padding: 15px 20px 15px 50px;
                background: {bg_color};
                border-left: 5px solid {border_color};
                border-radius: 0 8px 8px 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                position: relative;
                line-height: 1.7;
                color: #2c3e50;
                text-indent: 0;
            '''.strip().replace('\n', ' ')
            
            icon_style = '''
                position: absolute;
                left: 15px;
                top: 15px;
                font-size: 18px;
            '''.strip().replace('\n', ' ')
            
            return f'''<div style="{tip_style}">
                <span style="{icon_style}">{icon}</span>
                <div style="margin-left: 5px;">{text}</div>
            </div>\n'''
        
        return f'<p style="{self.styles["p"]}">{text}</p>\n'
    
    def block_quote(self, text):
        """自定义引用块渲染 - 增强版"""
        # 引用图标样式
        quote_icon_style = '''
            position: absolute;
            left: 15px;
            top: 15px;
            font-size: 24px;
            color: #6c757d;
            opacity: 0.6;
        '''.strip().replace('\n', ' ')
        
        return f'''<blockquote style="{self.styles["blockquote"]}">
            <span style="{quote_icon_style}">❝</span>
            <div style="margin-left: 10px; text-indent: 0;">{text}</div>
        </blockquote>\n'''
    
    def block_code(self, code, info=None, **attrs):
        """自定义代码块渲染 - 增强版，支持语法高亮"""
        try:
            # info 参数包含语言信息
            lang = info.strip() if info else None
            
            if lang:
                lexer = get_lexer_by_name(lang, stripall=True)
            else:
                lexer = TextLexer()
            
            formatter = HtmlFormatter(
                style='monokai',
                noclasses=True,
                cssclass='highlight',
                linenos=False
            )
            highlighted_code = highlight(code, lexer, formatter)
            
            # 提取body内容并添加自定义样式
            import re
            body_match = re.search(r'<div[^>]*>(.*?)</div>', highlighted_code, re.DOTALL)
            if body_match:
                code_content = body_match.group(1)
            else:
                code_content = highlighted_code
            
            # 语言标签样式
            lang_display = lang.upper() if lang else 'TEXT'
            lang_colors = {
                'PYTHON': '#3776ab',
                'JAVASCRIPT': '#f7df1e', 
                'JAVA': '#ed8b00',
                'HTML': '#e34c26',
                'CSS': '#1572b6',
                'SQL': '#336791',
                'JSON': '#000000',
                'BASH': '#4eaa25',
                'SHELL': '#4eaa25',
                'TEXT': '#6c757d'
            }
            lang_color = lang_colors.get(lang_display, '#6c757d')
            
            # 语言标签图标
            lang_icons = {
                'PYTHON': '🐍',
                'JAVASCRIPT': '⚡',
                'JAVA': '☕',
                'HTML': '🌐',
                'CSS': '🎨',
                'SQL': '🗃️',
                'JSON': '📋',
                'BASH': '💻',
                'SHELL': '💻',
                'TEXT': '📝'
            }
            lang_icon = lang_icons.get(lang_display, '📝')
            
            # 头部样式
            header_style = f'''
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #4a5568;
            '''.strip().replace('\n', ' ')
            
            # 语言标签样式
            lang_tag_style = f'''
                background: {lang_color};
                color: white;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
                display: flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            '''.strip().replace('\n', ' ')
            
            # 复制按钮样式
            copy_btn_style = '''
                background: #4a5568;
                color: #e2e8f0;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s ease;
            '''.strip().replace('\n', ' ')
            
            return f'''<div style="{self.styles['code_block']}">
                <div style="{header_style}">
                    <div style="{lang_tag_style}">
                        <span>{lang_icon}</span>
                        <span>{lang_display}</span>
                    </div>
                    <button style="{copy_btn_style}" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent)">
                        📋 复制
                    </button>
                </div>
                <div style="position: relative; overflow-x: auto;">
                    {code_content}
                </div>
            </div>\n'''
        except Exception as e:
            # 如果语法高亮失败，使用美观的普通代码块
            escaped_code = mistune.escape(code)
            lang_display = lang.upper() if lang else 'TEXT'
            
            return f'''<div style="{self.styles['code_block']}">
                <div style="margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #4a5568; color: #a0aec0; font-size: 12px; font-weight: bold;">
                    📝 {lang_display}
                </div>
                <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;"><code>{escaped_code}</code></pre>
            </div>\n'''
    
    def codespan(self, text):
        """自定义行内代码渲染"""
        return f'<code style="{self.styles["code_inline"]}">{mistune.escape(text)}</code>'
    
    def list(self, text, ordered, **attrs):
        """自定义列表渲染 - 增强版"""
        tag = 'ol' if ordered else 'ul'
        style = self.styles[tag]
        
        if ordered:
            self.ol_counter = 0  # 重置计数器
        
        # 增加列表层级
        self.list_level += 1
        result = f'<{tag} style="{style}">{text}</{tag}>'
        self.list_level -= 1
        
        return result
    
    def list_item(self, text):
        """自定义列表项渲染 - 增强版"""
        # 根据层级选择不同的符号
        level_index = min(self.list_level - 1, len(self.list_symbols['ul']) - 1)
        bullet = self.list_symbols['ul'][level_index]
        
        # 创建带有美观符号的列表项
        symbol_style = '''
            position: absolute;
            left: 10px;
            top: 1px;
            font-size: 14px;
            color: #3498db;
            font-weight: bold;
        '''.strip().replace('\n', ' ')
        
        return f'<li style="{self.styles["li"]}"><span style="{symbol_style}">{bullet}</span><div style="margin-left: 5px;">{text}</div></li>'
    
    def table(self, text):
        """自定义表格渲染"""
        return f'<table style="{self.styles["table"]}">\n{text}</table>\n'
    
    def table_head(self, text):
        """自定义表格头渲染"""
        return f'<thead>\n{text}</thead>\n'
    
    def table_body(self, text):
        """自定义表格体渲染"""
        return f'<tbody>\n{text}</tbody>\n'
    
    def table_row(self, text, is_head=False):
        """自定义表格行渲染 - 增强版"""
        if is_head:
            return f'<tr>\n{text}</tr>\n'
        else:
            # 为奇偶行添加不同的背景
            return f'<tr style="{self.styles["tr_even"]}" onmouseover="this.style.backgroundColor=\'#e3f2fd\'" onmouseout="this.style.backgroundColor=\'#f8f9fa\'">\n{text}</tr>\n'
    
    def table_cell(self, text, align=None, is_head=False):
        """自定义表格单元格渲染 - 增强版"""
        if is_head:
            style = self.styles['th']
            tag = 'th'
        else:
            style = self.styles['td']
            tag = 'td'
        
        align_style = f'text-align: {align};' if align else ''
        return f'<{tag} style="{style} {align_style}">{text}</{tag}>\n'
    
    def link(self, text, url, title=None):
        """自定义链接渲染 - 增强版"""
        title_attr = f' title="{mistune.escape(title)}"' if title else ''
        
        # 检查链接类型并添加相应图标
        if 'github.com' in url:
            icon = '🔗'
        elif 'docs.' in url or 'documentation' in url:
            icon = '📚'
        elif url.startswith('mailto:'):
            icon = '📧'
        elif url.endswith(('.pdf', '.doc', '.docx')):
            icon = '📄'
        else:
            icon = '🔗'
        
        enhanced_style = self.styles["a"] + '''
            display: inline-flex;
            align-items: center;
            gap: 4px;
        '''.strip().replace('\n', ' ')
        
        return f'<a href="{mistune.escape(url)}" style="{enhanced_style}"{title_attr}><span>{icon}</span><span>{text}</span></a>'
    
    def strong(self, text):
        """自定义粗体渲染 - 增强版"""
        return f'<strong style="{self.styles["strong"]}">✨ {text}</strong>'
    
    def emphasis(self, text):
        """自定义斜体渲染 - 增强版"""
        return f'<em style="{self.styles["em"]}">💫 {text}</em>'
    
    def thematic_break(self):
        """自定义分隔线渲染 - 增强版"""
        decorative_style = '''
            border: none;
            height: 40px;
            background: transparent;
            margin: 40px 0;
            position: relative;
            text-align: center;
        '''.strip().replace('\n', ' ')
        
        line_style = '''
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #bdc3c7, transparent);
            border-radius: 2px;
        '''.strip().replace('\n', ' ')
        
        diamond_style = '''
            position: relative;
            display: inline-block;
            background: white;
            padding: 0 15px;
            color: #bdc3c7;
            font-size: 20px;
            z-index: 1;
        '''.strip().replace('\n', ' ')
        
        return f'''<div style="{decorative_style}">
            <div style="{line_style}"></div>
            <span style="{diamond_style}">◆</span>
        </div>\n'''

class WeixinToken:
    def __init__(self, access_token: str, expires_in: int):
        self.access_token = access_token
        self.expires_in = expires_in
        self.expires_at = datetime.now() + timedelta(seconds=expires_in)

class ConfigManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    async def get(self, key: str) -> str:
        return os.getenv(key, '')

class WXPublisher:
    def __init__(self):
        """初始化微信公众号发布器"""
        self.access_token: Optional[WeixinToken] = None
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.config_manager = ConfigManager.get_instance()
        self.data_path = os.getenv('DATA_SAVE_PATH', './data')

    async def refresh(self) -> None:
        """刷新配置信息"""
        self.app_id = await self.config_manager.get("WEIXIN_APP_ID")
        self.app_secret = await self.config_manager.get("WEIXIN_APP_SECRET")
        logger.info("微信公众号配置: %s", {
            "appId": self.app_id,
            "appSecret": "***" + (self.app_secret[-4:] if self.app_secret else "")  # 只显示密钥后4位
        })

    async def ensure_access_token(self) -> str:
        """确保访问令牌有效"""
        # 检查现有token是否有效
        if (self.access_token and 
            self.access_token.expires_at > datetime.now() + timedelta(minutes=1)):  # 预留1分钟余量
            return self.access_token.access_token

        try:
            await self.refresh()
            # 获取新token
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
            response = requests.get(url).json()
            
            if 'access_token' not in response:
                raise Exception(f"获取access_token失败: {json.dumps(response)}")

            self.access_token = WeixinToken(
                response['access_token'],
                response['expires_in']
            )
            return self.access_token.access_token

        except Exception as error:
            logger.error("获取微信access_token失败: %s", error)
            raise

    def _preprocess_article(self, article: str) -> str:
        """预处理文章内容，确保编码正确"""
        if not article:
            return ""
            
        # 确保内容是字符串
        if not isinstance(article, str):
            article = str(article)
            
        # 检查编码，确保是UTF-8
        try:
            # 如果是bytes，转成字符串
            if isinstance(article, bytes):
                article = article.decode('utf-8')
                
            # 确保可以编码为UTF-8，这样可以检测潜在的编码问题
            article.encode('utf-8').decode('utf-8')
        except UnicodeError:
            logger.warning("文章内容编码有问题，尝试修复...")
            # 尝试修复编码问题
            try:
                # 如果是bytes，可能是其他编码，尝试不同的编码
                if isinstance(article, bytes):
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                        try:
                            article = article.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
            except Exception as e:
                logger.error(f"修复编码失败: {e}")
        
        # 处理HTML实体和特殊字符编码
        article = html.unescape(article)  # 将HTML实体转换回实际字符
                
        # 移除可能导致问题的特殊字符或控制字符
        article = ''.join(ch for ch in article if ord(ch) >= 32 or ch in '\n\t\r')
        
        # 检查是否存在中文字符 (如果全是英文，可能需要特别处理)
        has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in article)
        if not has_chinese and len(article) > 50:  # 较长内容中没有中文可能是编码问题
            logger.warning("文章内容中未检测到中文字符，可能存在编码问题")
            
        return article

    def _md_to_html(self, md_content: str) -> str:
        """将Markdown内容转换为美观的HTML，专门为微信公众号优化"""
        if not md_content:
            return ""
            
        # 移除可能存在的markdown标记
        if 'markdown' in md_content.lower():
            # 去除带有markdown字样的行
            md_content = re.sub(r'^.*markdown.*$', '', md_content, flags=re.MULTILINE | re.IGNORECASE)
        
        try:
            # 使用自定义的微信渲染器
            renderer = WeixinRenderer()
            markdown_parser = mistune.create_markdown(
                renderer=renderer,
                plugins=[
                    'strikethrough',  # 删除线支持
                    'footnotes',      # 脚注支持
                    'table',          # 表格支持
                    'url',            # 自动链接
                    'task_lists',     # 任务列表
                    'def_list',       # 定义列表
                    'abbr',           # 缩写
                    'mark',           # 标记高亮
                    'superscript',    # 上标
                    'subscript',      # 下标
                ]
            )
            
            # 转换markdown为HTML
            html_content = markdown_parser(md_content)
            
            # 添加整体容器样式
            styled_html = f'''<div style="{renderer.styles['body']}">
{html_content}
</div>'''
            
            logger.info("使用Mistune自定义渲染器成功转换内容，应用微信公众号优化样式")
            return styled_html
            
        except Exception as e:
            logger.error(f"使用Mistune转换失败，尝试备用方案: {e}")
            
            # 备用方案：使用原来的markdown库
            try:
                extensions = [
                    'markdown.extensions.extra',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.smarty',
                    'markdown.extensions.nl2br',
                    'markdown.extensions.toc'
                ]
                html_content = markdown.markdown(md_content, extensions=extensions)
                logger.info("使用备用markdown库成功转换内容")
                return html_content
            except Exception as backup_error:
                logger.error(f"备用转换方案也失败: {backup_error}")
                # 最后的备用方案：返回带基本样式的原始内容
                return f'<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><p>{md_content}</p></div>'

   

    async def upload_draft(self, article: str, title: str, digest: str, media_id: str) -> Dict[str, str]:
        """上传草稿"""
        token = await self.ensure_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        # 预处理文章内容
        article = self._preprocess_article(article)
        
        # 假设文章内容可能是Markdown格式，尝试转换为HTML并应用模板
        try:
            html_content = self._md_to_html(article)
            logger.info("Markdown内容已成功转换为带模板的HTML")
        except Exception as e:
            logger.warning(f"Markdown转换失败，使用原始内容: {e}")
        
        # 预处理标题和摘要
        if title and isinstance(title, str):
            title = self._preprocess_article(title)
        if digest and isinstance(digest, str):
            digest = self._preprocess_article(digest)

        articles = [{
            "title": title,
            "author": await self.config_manager.get("AUTHOR"),
            "digest": digest,
            "content": html_content,
            "thumb_media_id": media_id,
            "need_open_comment": 1 if await self.config_manager.get("NEED_OPEN_COMMENT") == "true" else 0,
            "only_fans_can_comment": 1 if await self.config_manager.get("ONLY_FANS_CAN_COMMENT") == "true" else 0
        }]

        try:
            # 记录请求日志
           # logger.debug("微信草稿请求内容: %s", json.dumps({"articles": articles}, ensure_ascii=False))
            
            # 准备请求数据和头信息
            data = json.dumps({"articles": articles}, ensure_ascii=False, separators=(',', ':'))
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json; charset=utf-8'
            }
            
            # 明确指定编码方式进行POST请求
            response = requests.post(
                url, 
                data=data.encode('utf-8'), 
                headers=headers
            )
            
            # 确保响应是UTF-8编码
            if response.encoding.lower() != 'utf-8':
                response.encoding = 'utf-8'
                
            response_json = response.json()
            
            # 记录响应日志
            logger.debug("微信草稿响应内容: %s", json.dumps(response_json, ensure_ascii=False))
            
            if 'errcode' in response_json:
                raise Exception(f"上传草稿失败: {response_json['errmsg']}")

            return {"media_id": response_json['media_id']}

        except Exception as error:
            logger.error("上传微信草稿失败: %s", error)
            raise

    def _is_local_file(self, path: str) -> bool:
        """判断路径是否为本地文件"""
        return not (path.startswith('http://') or path.startswith('https://'))
    
    def _get_image_content_type(self, file_path: str) -> str:
        """根据文件扩展名获取图片内容类型"""
        ext = Path(file_path).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        return content_types.get(ext, 'image/jpeg')

    async def upload_image(self, image_path: str) -> str:
        """上传图片到微信，支持本地文件和网络URL"""
        if not image_path:
            return "SwCSRjrdGJNaWioRQUHzgF68BHFkSlb_f5xlTquvsOSA6Yy0ZRjFo0aW9eS3JJu_"

        token = await self.ensure_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"

        try:
            # 判断是本地文件还是网络URL
            if self._is_local_file(image_path):
                # 处理本地图片文件
                logger.info(f"上传本地图片文件: {image_path}")
                
                # 检查文件是否存在
                local_path = Path(image_path)
                if not local_path.exists():
                    raise FileNotFoundError(f"本地图片文件不存在: {image_path}")
                
                if not local_path.is_file():
                    raise ValueError(f"路径不是文件: {image_path}")
                
                # 检查文件扩展名
                allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                if local_path.suffix.lower() not in allowed_extensions:
                    raise ValueError(f"不支持的图片格式: {local_path.suffix}，支持的格式: {', '.join(allowed_extensions)}")
                
                # 读取本地文件
                with open(local_path, 'rb') as f:
                    image_content = f.read()
                
                # 获取内容类型和文件名
                content_type = self._get_image_content_type(image_path)
                filename = local_path.name
                
                logger.info(f"本地图片文件大小: {len(image_content)} 字节，类型: {content_type}")
                
            else:
                # 处理网络URL
                logger.info(f"下载网络图片: {image_path}")
                response = requests.get(image_path, timeout=30)
                response.raise_for_status()
                image_content = response.content
                content_type = response.headers.get('content-type', 'image/jpeg')
                filename = 'image.jpg'
                
                logger.info(f"网络图片下载完成，大小: {len(image_content)} 字节，类型: {content_type}")

            # 检查图片大小（微信限制10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if len(image_content) > max_size:
                raise ValueError(f"图片文件过大: {len(image_content)} 字节，超过微信限制的 {max_size} 字节")

            # 上传到微信
            files = {
                'media': (filename, image_content, content_type)
            }
            response = requests.post(url, files=files).json()

            if 'errcode' in response:
                raise Exception(f"上传图片失败: {response['errmsg']}")

            logger.info(f"图片上传成功，media_id: {response['media_id']}")
            return response['media_id']

        except Exception as error:
            logger.error("上传微信图片失败: %s", error)
            raise

    async def upload_content_image(self, image_url: str, image_buffer: Optional[bytes] = None) -> str:
        """上传图文消息内的图片获取URL"""
        if not image_url:
            raise Exception("图片URL不能为空")

        token = await self.ensure_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"

        try:
            if image_buffer:
                image_content = image_buffer
            else:
                image_content = requests.get(image_url).content

            files = {
                'media': ('image.jpg', image_content, 'image/jpeg')
            }
            response = requests.post(url, files=files).json()

            if 'errcode' in response:
                raise Exception(f"上传图文消息图片失败: {response['errmsg']}")

            return response['url']

        except Exception as error:
            logger.error("上传微信图文消息图片失败: %s", error)
            raise

    async def publish(self, article: str, title: str, digest: str, media_id: str) -> Dict[str, Any]:
        """发布文章到微信"""
        try:
            # 记录原始内容长度，用于调试
            article_len = len(article) if article else 0
            logger.info(f"原始文章内容长度: {article_len} 字符")
            
            # 预处理文章内容
            article = self._preprocess_article(article)
            
            # 记录处理后内容长度
            processed_len = len(article) if article else 0
            logger.info(f"处理后文章内容长度: {processed_len} 字符")
            
            if processed_len > 0 and processed_len < article_len:
                logger.warning(f"文章内容在预处理中被截断，原始长度: {article_len}，处理后长度: {processed_len}")
            
            # 记录请求详情，但限制内容长度，避免日志过大
            content_preview = article[:200] + "..." if len(article) > 200 else article
            logger.info(f"发布标题: {title}")
            logger.info(f"发布摘要: {digest}")
            logger.info(f"发布图片ID: {media_id}")
            logger.info(f"发布文章预览: {content_preview}")
            
            # 检查是否需要直接发布
            direct_publish = await self.config_manager.get("DIRECT_PUBLISH")
            
            # 上传草稿
            draft = await self.upload_draft(article, title, digest, media_id)
            logger.info(f"草稿上传成功，media_id: {draft['media_id']}")
            
            # 如果配置了直接发布，则调用发布接口
            if direct_publish and direct_publish.lower() == "true":
                publish_result = await self.direct_publish(draft['media_id'])
                logger.info(f"直接发布成功，publish_id: {publish_result['publish_id']}")
                return {
                    "publishId": publish_result['publish_id'],
                    "draftId": draft['media_id'],
                    "status": "publishing",
                    "publishedAt": datetime.now().isoformat(),
                    "platform": "weixin",
                    "url": f"https://mp.weixin.qq.com/s/{draft['media_id']}"
                }
            
            return {
                "publishId": draft['media_id'],
                "status": "draft",
                "publishedAt": datetime.now().isoformat(),
                "platform": "weixin",
                "url": f"https://mp.weixin.qq.com/s/{draft['media_id']}"
            }

        except Exception as error:
            logger.error("微信发布失败: %s", error)
            raise

    async def direct_publish(self, media_id: str) -> Dict[str, Any]:
        """直接发布草稿
        
        Args:
            media_id: 草稿的media_id
            
        Returns:
            Dict: 包含发布ID的字典
        """
        try:
            token = await self.ensure_access_token()
            url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
            
            data = {
                "media_id": media_id
            }
            
            # 准备请求数据和头信息
            data_json = json.dumps(data, ensure_ascii=False)
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json; charset=utf-8'
            }
            
            # 发送请求
            response = requests.post(
                url, 
                data=data_json.encode('utf-8'), 
                headers=headers
            )
            
            # 确保响应是UTF-8编码
            if response.encoding.lower() != 'utf-8':
                response.encoding = 'utf-8'
                
            response_json = response.json()
            
            # 记录响应日志
            logger.debug("微信发布响应内容: %s", json.dumps(response_json, ensure_ascii=False))
            
            if 'errcode' in response_json and response_json['errcode'] != 0:
                error_msg = response_json.get('errmsg', '未知错误')
                error_code = response_json.get('errcode', -1)
                
                # 特殊错误码处理
                if error_code == 53503:
                    error_msg = "该草稿未通过发布检查"
                elif error_code == 53504:
                    error_msg = "需前往公众平台官网使用草稿"
                elif error_code == 53505:
                    error_msg = "请手动保存成功后再发表"
                
                raise Exception(f"发布失败 (错误码: {error_code}): {error_msg}")

            return {
                "publish_id": response_json.get('publish_id', ''),
                "msg_data_id": response_json.get('msg_data_id', '')
            }

        except Exception as error:
            logger.error("直接发布微信文章失败: %s", error)
            raise
            
    async def check_publish_status(self, publish_id: str) -> Dict[str, Any]:
        """查询发布状态
        
        Args:
            publish_id: 发布任务的ID
            
        Returns:
            Dict: 包含发布状态的字典
        """
        try:
            token = await self.ensure_access_token()
            url = f"https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token={token}"
            
            data = {
                "publish_id": publish_id
            }
            
            # 准备请求数据和头信息
            data_json = json.dumps(data, ensure_ascii=False)
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json; charset=utf-8'
            }
            
            # 发送请求
            response = requests.post(
                url, 
                data=data_json.encode('utf-8'), 
                headers=headers
            )
            
            # 确保响应是UTF-8编码
            if response.encoding.lower() != 'utf-8':
                response.encoding = 'utf-8'
                
            response_json = response.json()
            
            # 记录响应日志
            logger.debug("微信发布状态查询响应: %s", json.dumps(response_json, ensure_ascii=False))
            
            if 'errcode' in response_json and response_json['errcode'] != 0:
                raise Exception(f"查询发布状态失败: {response_json['errmsg']}")

            # 可能的发布状态：0=成功, 1=发布中, 2=原创失败, 3=常规失败, 4=平台审核不通过, 5=成功但是转义了表情
            status_map = {
                0: "published",
                1: "publishing",
                2: "failed_original",
                3: "failed_general", 
                4: "failed_audit",
                5: "published_emoji_escaped"
            }
            
            publish_status = response_json.get('publish_status', -1)
            
            return {
                "status": status_map.get(publish_status, "unknown"),
                "publish_id": publish_id,
                "publish_status": publish_status,
                "article_id": response_json.get('article_id', ''),
                "article_url": response_json.get('article_url', ''),
                "fail_reason": response_json.get('fail_reason', '')
            }

        except Exception as error:
            logger.error("查询微信发布状态失败: %s", error)
            raise

    async def validate_ip_whitelist(self) -> str | bool:
        """验证当前服务器IP是否在微信公众号的IP白名单中"""
        try:
            await self.ensure_access_token()
            return True
        except Exception as error:
            error_msg = str(error)
            if "40164" in error_msg:
                import re
                match = re.search(r"invalid ip ([^ ]+)", error_msg)
                return match.group(1) if match else "未知IP"
            raise

    async def push_recommendation(self, content: str = None, title: str = None, digest: str = None, image_url: str = None) -> Dict[str, Any]:
        """推送内容到微信公众号
        
        Args:
            content: 要推送的内容，如果为None则从文件读取
            title: 文章标题，如果为None则使用默认标题或从文件读取
            digest: 文章摘要，如果为None则使用默认摘要或从文件读取
            image_url: 封面图片URL，如果为None则使用默认图片

        Returns:
            Dict[str, Any]: 包含发布状态的字典
        """
        try:
            # 如果没有直接提供内容，则从文件读取
            if content is None:
                # 读取最新的投资建议
                recommendation_path = os.path.join(self.data_path, "investment_recommendation.json")
                
                try:
                    with open(recommendation_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"成功读取投资建议文件: {recommendation_path}")
                except FileNotFoundError:
                    logger.error(f"未找到投资建议文件: {recommendation_path}")
                    return {
                        "status": "error",
                        "message": "未找到投资建议文件"
                    }
                except json.JSONDecodeError:
                    logger.error(f"投资建议文件格式错误: {recommendation_path}")
                    return {
                        "status": "error",
                        "message": "投资建议文件格式错误"
                    }
                
                # 获取必要的字段
                content = data.get('recommendation', '')
                if title is None:
                    title = data.get('title', '投资建议分析报告')
                if digest is None:
                    digest = data.get('digest', '投资建议分析报告')
                if image_url is None:
                    image_url = data.get('image_url', '')
            else:
                # 使用传入的参数或默认值
                if title is None:
                    title = '市场分析报告'
                if digest is None:
                    digest = '最新市场分析报告'
            
            # 检查内容是否为空
            if not content:
                logger.error("推送内容为空")
                return {
                    "status": "error",
                    "message": "推送内容为空"
                }
            
            # 预处理内容和字段
            content = self._preprocess_article(content)
            title = self._preprocess_article(title)
            digest = self._preprocess_article(digest)
            
            # 记录处理结果
            logger.info(f"处理后标题: {title}")
            logger.info(f"处理后摘要: {digest}")
            logger.info(f"处理后内容长度: {len(content)} 字符")
            
            # 上传图片
            default_img_url = "https://gips0.baidu.com/it/u=1690853528,2506870245&fm=3028&app=3028&f=JPEG&fmt=auto?w=1024&h=1024"
            img_path = image_url if image_url else default_img_url
            
            # 判断是本地文件还是网络URL
            if self._is_local_file(img_path):
                logger.info(f"准备上传本地图片文件: {img_path}")
            else:
                logger.info(f"准备上传网络图片: {img_path}")
                
            media_id = await self.upload_image(img_path)
            logger.info(f"上传图片成功: {media_id}")
            
            # 推送到微信公众号
            logger.info("开始推送到微信公众号...")
            result = await self.publish(
                article=content,
                title=title,
                digest=digest,
                media_id=media_id
            )
            logger.info(f"推送结果: {json.dumps(result, ensure_ascii=False)}")
            return result
            
        except Exception as error:
            logger.error("推送内容时发生错误: %s", error)
            return {
                "status": "error",
                "message": f"推送内容失败: {str(error)}"
            }

    def read_markdown_file(self, file_path: str) -> str:
        """读取本地 Markdown 文件
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            str: 文件内容
        """
        try:
            # 确保文件路径存在
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            if not path.is_file():
                raise ValueError(f"路径不是文件: {file_path}")
            
            # 检查文件扩展名
            if path.suffix.lower() not in ['.md', '.markdown']:
                logger.warning(f"文件扩展名不是 .md 或 .markdown: {file_path}")
            
            # 读取文件内容
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"成功读取 Markdown 文件: {file_path}, 内容长度: {len(content)} 字符")
            return content
            
        except Exception as error:
            logger.error(f"读取 Markdown 文件失败: {error}")
            raise

    async def publish_from_markdown(self, md_file_path: str, title: str, digest: str = None, image_url: str = None) -> Dict[str, Any]:
        """从 Markdown 文件发布到微信公众号
        
        Args:
            md_file_path: Markdown 文件路径
            title: 文章标题
            digest: 文章摘要，如果为None则从标题生成
            image_url: 封面图片URL，如果为None则使用默认图片
            
        Returns:
            Dict[str, Any]: 包含发布状态的字典
        """
        try:
            # 读取 Markdown 文件
            logger.info(f"开始读取 Markdown 文件: {md_file_path}")
            content = self.read_markdown_file(md_file_path)
            
            # 如果没有提供摘要，从标题生成
            if digest is None:
                digest = f"{title} - 最新分析报告"
            
            # 预处理内容和字段
            content = self._preprocess_article(content)
            title = self._preprocess_article(title)
            digest = self._preprocess_article(digest)
            
            # 记录处理结果
            logger.info(f"处理后标题: {title}")
            logger.info(f"处理后摘要: {digest}")
            logger.info(f"处理后内容长度: {len(content)} 字符")
            
            # 上传图片
            default_img_url = "https://gips0.baidu.com/it/u=1690853528,2506870245&fm=3028&app=3028&f=JPEG&fmt=auto?w=1024&h=1024"
            img_path = image_url if image_url else default_img_url
            
            # 判断是本地文件还是网络URL
            if self._is_local_file(img_path):
                logger.info(f"准备上传本地图片文件: {img_path}")
            else:
                logger.info(f"准备上传网络图片: {img_path}")
                
            media_id = await self.upload_image(img_path)
            logger.info(f"上传图片成功: {media_id}")
            
            # 发布到微信公众号
            logger.info("开始发布到微信公众号...")
            result = await self.publish(
                article=content,
                title=title,
                digest=digest,
                media_id=media_id
            )
            logger.info(f"发布结果: {json.dumps(result, ensure_ascii=False)}")
            return result
            
        except Exception as error:
            logger.error("从 Markdown 文件发布内容时发生错误: %s", error)
            return {
                "status": "error",
                "message": f"发布内容失败: {str(error)}"
            }


async def main():
    """主函数 - 直接在代码中配置参数"""
    
    # 首先检查和显示环境变量状态
    print("🔍 检查环境变量状态:")
    env_vars_to_check = ['WEIXIN_APP_ID', 'WEIXIN_APP_SECRET', 'AUTHOR', 'DIRECT_PUBLISH', 'NEED_OPEN_COMMENT', 'ONLY_FANS_CAN_COMMENT']
    for var in env_vars_to_check:
        value = os.getenv(var)
        if value:
            # 对敏感信息进行脱敏显示
            if 'SECRET' in var:
                display_value = f"***{value[-4:]}" if len(value) > 4 else "***"
            elif 'APP_ID' in var:
                display_value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else value
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: 未设置")
    print()
    
    # ==================== 在这里修改你的参数 ====================
    # Markdown 文件路径（必填）
    md_file_path = "docs/qanything-qa.md"  # 请修改为你的 Markdown 文件路径
    
    # 文章标题（必填）
    title = "LangGraph Human-in-the-Loop 完整指南"  # 请修改为你的文章标题
    
    # 文章摘要（可选，如果为 None 则自动生成）
    digest = None  # 可以设置为 "这是文章摘要" 或保持 None
    
    # 封面图片路径（可选，如果为 None 则使用默认图片）
    # 支持本地图片文件路径（如 "./images/cover.jpg"）和网络URL（如 "https://example.com/image.jpg"）
    image_url = "docs/ai-image.png"  # 可以设置为本地图片路径或网络URL，或保持 None
    
    # 是否检查配置和IP白名单（可选）
    check_config = True  # 设置为 True 来检查配置
    # =========================================================
    
    # 创建发布器实例
    publisher = WXPublisher()
    
    try:
        # 检查配置（可选）
        if check_config:
            logger.info("检查微信公众号配置和IP白名单...")
            ip_result = await publisher.validate_ip_whitelist()
            if ip_result is True:
                logger.info("✅ IP白名单验证通过")
            else:
                logger.warning(f"⚠️ IP白名单验证失败，当前IP: {ip_result}")
                print(f"警告: 当前服务器IP ({ip_result}) 可能不在微信公众号的IP白名单中")
                print("请在微信公众平台后台添加此IP到白名单")
                
                # 询问是否继续
                continue_publish = input("是否继续发布？(y/N): ").strip().lower()
                if continue_publish not in ['y', 'yes']:
                    print("取消发布")
                    return
        
        # 检查必要的环境变量
        required_env_vars = ['WEIXIN_APP_ID', 'WEIXIN_APP_SECRET']
        missing_vars = []
        
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
            print("❌ 缺少必要的环境变量:")
            for var in missing_vars:
                print(f"   {var}")
            print("\n请设置以下环境变量:")
            print("export WEIXIN_APP_ID='你的微信公众号AppID'")
            print("export WEIXIN_APP_SECRET='你的微信公众号AppSecret'")
            print("export AUTHOR='作者名称'  # 可选")
            print("export DIRECT_PUBLISH='true'  # 可选，是否直接发布")
            print("export NEED_OPEN_COMMENT='true'  # 可选，是否开启评论")
            print("export ONLY_FANS_CAN_COMMENT='false'  # 可选，是否仅粉丝可评论")
            return
        
        # 显示配置信息
        logger.info("当前配置:")
        logger.info(f"  Markdown文件: {md_file_path}")
        logger.info(f"  文章标题: {title}")
        logger.info(f"  文章摘要: {digest or '(从标题自动生成)'}")
        logger.info(f"  封面图片: {image_url or '(使用默认图片)'}")
        logger.info(f"  作者: {os.getenv('AUTHOR', '未设置')}")
        logger.info(f"  直接发布: {os.getenv('DIRECT_PUBLISH', 'false')}")
        
        # 发布文章
        print("🚀 开始发布到微信公众号...")
        result = await publisher.publish_from_markdown(
            md_file_path=md_file_path,
            title=title,
            digest=digest,
            image_url=image_url
        )
        
        # 显示结果
        if result.get('status') == 'error':
            print(f"❌ 发布失败: {result.get('message')}")
            sys.exit(1)
        else:
            print("✅ 发布成功!")
            print(f"   状态: {result.get('status')}")
            print(f"   平台: {result.get('platform')}")
            print(f"   发布时间: {result.get('publishedAt')}")
            
            if result.get('status') == 'draft':
                print("   📝 文章已保存为草稿，请到微信公众平台手动发布")
            elif result.get('status') == 'publishing':
                print("   📤 文章正在发布中...")
                if result.get('publishId'):
                    print(f"   发布ID: {result.get('publishId')}")
            
            if result.get('url'):
                print(f"   链接: {result.get('url')}")
    
    except KeyboardInterrupt:
        print("\n❌ 用户取消操作")
        sys.exit(1)
    except Exception as error:
        logger.error(f"发布过程中发生错误: {error}")
        print(f"❌ 发布失败: {error}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 