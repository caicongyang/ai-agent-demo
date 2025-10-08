#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作内容提炼脚本
功能：
1. 根据 '工作内容-补充说明' 列提炼到 '内容' 列
2. 根据 '工作内容-补充说明' 列补充 '工作分类' 列
"""

import pandas as pd
import os
from typing import List, Dict, Any
import re

class WorkContentProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        
        # 工作分类选项
        self.work_categories = [
            "核心任务",
            "辅助任务", 
            "临时事务",
            "未产生价值",
            "其他杂项事务"
        ]
        
        # 工作分类关键词映射
        self.category_keywords = {
            "核心任务": [
                "开发", "设计", "架构", "核心功能", "主要任务", "重要项目", 
                "产品开发", "系统设计", "技术方案", "业务逻辑", "核心模块"
            ],
            "辅助任务": [
                "测试", "调试", "优化", "文档", "代码审查", "部署", "配置",
                "维护", "监控", "支持", "培训", "指导"
            ],
            "临时事务": [
                "紧急", "临时", "突发", "加急", "应急", "修复", "hotfix",
                "临时需求", "紧急修复", "临时支持"
            ],
            "未产生价值": [
                "无效", "取消", "废弃", "无用", "重复", "无意义", "浪费时间",
                "无结果", "失败", "回滚"
            ],
            "其他杂项事务": [
                "会议", "沟通", "协调", "整理", "学习", "培训", "日常",
                "例行", "杂项", "其他", "行政", "报告"
            ]
        }
    
    def load_excel(self) -> bool:
        """加载Excel文件"""
        try:
            self.df = pd.read_excel(self.file_path)
            print(f"成功加载Excel文件，共 {len(self.df)} 行数据")
            print(f"列名: {list(self.df.columns)}")
            return True
        except Exception as e:
            print(f"加载Excel文件失败: {e}")
            return False
    
    def extract_content(self, work_description: str) -> str:
        """
        从工作内容-补充说明中提炼内容
        """
        if pd.isna(work_description) or not work_description:
            return ""
        
        # 转换为字符串
        work_description = str(work_description).strip()
        
        # 提炼关键信息的规则
        # 1. 去除多余的标点符号和空白
        content = re.sub(r'\s+', ' ', work_description)
        
        # 2. 提取核心动作和对象
        # 寻找动作词 + 对象的模式
        action_patterns = [
            r'(开发|设计|实现|创建|构建|编写|修改|优化|测试|部署|配置|维护|修复|调试|分析|研究|学习|整理|文档化|重构|升级)(.{1,30})',
            r'(完成|处理|解决|协助|支持|参与|负责)(.{1,30})',
            r'(.{1,20})(功能|模块|系统|接口|服务|组件|工具|平台|应用)',
        ]
        
        extracted_parts = []
        for pattern in action_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    extracted_parts.extend([part.strip() for part in match if part.strip()])
        
        # 3. 如果没有匹配到模式，则截取前50个字符作为摘要
        if not extracted_parts:
            content = content[:50] + ("..." if len(content) > 50 else "")
        else:
            # 合并提取的部分，去重
            unique_parts = []
            for part in extracted_parts:
                if part and part not in unique_parts and len(part) > 2:
                    unique_parts.append(part)
            content = " ".join(unique_parts[:3])  # 最多取前3个关键部分
        
        return content.strip()
    
    def classify_work(self, work_description: str) -> str:
        """
        根据工作内容-补充说明分类工作
        """
        if pd.isna(work_description) or not work_description:
            return "其他杂项事务"
        
        work_description = str(work_description).lower()
        
        # 计算每个分类的匹配分数
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in work_description:
                    score += 1
            category_scores[category] = score
        
        # 返回得分最高的分类
        if max(category_scores.values()) > 0:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return "其他杂项事务"
    
    def process_data(self):
        """处理数据"""
        if self.df is None:
            print("请先加载Excel文件")
            return
        
        # 检查必要的列是否存在
        required_column = "工作内容-补充说明"
        if required_column not in self.df.columns:
            print(f"未找到必需的列: {required_column}")
            print(f"可用的列: {list(self.df.columns)}")
            return
        
        # 如果不存在目标列，则创建
        if "内容" not in self.df.columns:
            self.df["内容"] = ""
        
        if "工作分类" not in self.df.columns:
            self.df["工作分类"] = ""
        
        # 处理每一行
        for index, row in self.df.iterrows():
            work_desc = row[required_column]
            
            # 提炼内容
            content = self.extract_content(work_desc)
            self.df.at[index, "内容"] = content
            
            # 分类工作
            category = self.classify_work(work_desc)
            self.df.at[index, "工作分类"] = category
            
            print(f"处理第 {index + 1} 行: {work_desc[:30]}... -> 内容: {content[:20]}... -> 分类: {category}")
    
    def save_excel(self, output_path: str = None):
        """保存处理后的Excel文件"""
        if self.df is None:
            print("没有数据可保存")
            return
        
        if output_path is None:
            # 在原文件名基础上添加后缀
            base_name = os.path.splitext(self.file_path)[0]
            output_path = f"{base_name}_processed.xlsx"
        
        try:
            self.df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"处理后的文件已保存到: {output_path}")
        except Exception as e:
            print(f"保存文件失败: {e}")
    
    def display_summary(self):
        """显示处理摘要"""
        if self.df is None:
            return
        
        print("\n=== 处理摘要 ===")
        print(f"总行数: {len(self.df)}")
        
        if "工作分类" in self.df.columns:
            print("\n工作分类分布:")
            category_counts = self.df["工作分类"].value_counts()
            for category, count in category_counts.items():
                print(f"  {category}: {count} 项")
        
        print("\n前5行处理结果预览:")
        preview_columns = []
        if "工作内容-补充说明" in self.df.columns:
            preview_columns.append("工作内容-补充说明")
        if "内容" in self.df.columns:
            preview_columns.append("内容")
        if "工作分类" in self.df.columns:
            preview_columns.append("工作分类")
        
        if preview_columns:
            print(self.df[preview_columns].head().to_string(index=False))


def main():
    """主函数"""
    file_path = "/Users/caicongyang/IdeaProjects/github/ai-agent-demo/工作内容提炼.xlsx"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    # 创建处理器实例
    processor = WorkContentProcessor(file_path)
    
    # 加载Excel文件
    if not processor.load_excel():
        return
    
    # 处理数据
    print("\n开始处理数据...")
    processor.process_data()
    
    # 显示摘要
    processor.display_summary()
    
    # 保存处理后的文件
    processor.save_excel()
    
    print("\n处理完成！")


if __name__ == "__main__":
    main()
