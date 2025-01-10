import pandas as pd
import openpyxl
import re
from typing import List, Union, Optional

class ExcelHandler:
    def __init__(self, file_path: str):
        """
        初始化 Excel 处理器
        
        :param file_path: Excel 文件路径
        """
        self.file_path = file_path
        self.df = None

    def read_excel(self, sheet_name: Union[str, int] = 0) -> pd.DataFrame:
        """
        读取 Excel 文件
        
        :param sheet_name: 工作表名称或索引，默认为第一个工作表
        :return: pandas DataFrame
        """
        try:
            self.df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            return self.df
        except Exception as e:
            print(f"读取 Excel 文件时发生错误: {e}")
            return None

    def clean_column_data(self, column_name: str, 
                          patterns: List[str] = None) -> bool:
        """
        清理指定列的数据，去除特定模式的后缀和括号内容
        
        :param column_name: 要清理的列名
        :param patterns: 要匹配并删除的正则表达式模式列表
        :return: 是否清理成功
        """
        if self.df is None:
            self.read_excel()
        
        # 默认模式列表
        if patterns is None:
            patterns = [
                r'\(.*?\)',  # 删除小括号及其内容
                r'\[.*?\]',  # 删除中括号及其内容
                r'_\d+\*\d+(\.\d+)?$',  # 删除 _数字*数字 后缀
                r'\s*_\d+\*\d+(\.\d+)?'
            ]
        
        try:
            # 依次应用所有模式
            def clean_text(text):
                text_str = str(text)
                for pattern in patterns:
                    text_str = re.sub(pattern, '', text_str).strip()
                return text_str
            
            self.df[column_name] = self.df[column_name].apply(clean_text)
            return True
        except Exception as e:
            print(f"清理数据时发生错误: {e}")
            return False

    def write_excel(self, 
                    data: pd.DataFrame = None, 
                    output_path: Optional[str] = None, 
                    sheet_name: str = 'Sheet1') -> bool:
        """
        写入 Excel 文件
        
        :param data: 要写入的 DataFrame，默认为当前 DataFrame
        :param output_path: 输出文件路径，默认为原文件路径
        :param sheet_name: 工作表名称
        :return: 是否写入成功
        """
        try:
            data = data if data is not None else self.df
            output_path = output_path or self.file_path
            data.to_excel(output_path, sheet_name=sheet_name, index=False)
            print(f"成功写入文件: {output_path}")
            return True
        except Exception as e:
            print(f"写入 Excel 文件时发生错误: {e}")
            return False

    def filter_data(self, 
                    column: str, 
                    condition: Union[str, int, float]) -> pd.DataFrame:
        """
        根据条件过滤数据
        
        :param column: 要过滤的列名
        :param condition: 过滤条件
        :return: 过滤后的 DataFrame
        """
        if self.df is None:
            self.read_excel()
        
        try:
            filtered_df = self.df[self.df[column] == condition]
            return filtered_df
        except Exception as e:
            print(f"过滤数据时发生错误: {e}")
            return None

    def add_column(self, 
                   column_name: str, 
                   values: List[Union[str, int, float]]) -> bool:
        """
        添加新列
        
        :param column_name: 新列名称
        :param values: 新列的值
        :return: 是否添加成功
        """
        if self.df is None:
            self.read_excel()
        
        try:
            if len(values) != len(self.df):
                raise ValueError("新列的值数量必须与 DataFrame 行数相同")
            
            self.df[column_name] = values
            return True
        except Exception as e:
            print(f"添加列时发生错误: {e}")
            return False

def main():
    # 示例使用
    handler = ExcelHandler('example.xlsx')
    
    # 读取 Excel
    df = handler.read_excel()
    print("原始数据:")
    print(df)
    
    # 清理第一列数据
    handler.clean_column_data('商品名称')
    
    print("\n清理后的数据:")
    print(handler.df)
    
    # 写入新的 Excel 文件
    handler.write_excel(output_path='cleaned_example.xlsx')

# 测试代码
def test_clean_column_data():
    # 测试用例
    test_data = [
        "【周末放价】自选汉堡+粗薯+塔塔鸡块+双享翅根+冰柠可乐[自选汉堡:藤椒鸡腿中国汉堡]_1*44.6+荆楚尖叫翅尖_1*8.8",
        "原味鸡腿中国汉堡+粗薯+塔塔鸡块+冰柠可乐_1*33.8",
        "冰柠可乐(直饮杯，需要吸管请备注)_1*9.0+【品牌会员】香辣鸡腿中国汉堡X2+塔塔鸡块+冰柠可乐X2_1*40.0"
    ]
    
    import pandas as pd
    
    # 创建测试 DataFrame
    df = pd.DataFrame({'商品名称': test_data})
    handler = ExcelHandler('test.xlsx')
    handler.df = df
    
    # 清理数据
    handler.clean_column_data('商品名称')
    
    # 打印结果
    print("\n测试结果:")
    print(handler.df)

if __name__ == '__main__':
    test_clean_column_data() 