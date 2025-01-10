import pandas as pd
import openpyxl
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

    def write_excel(self, 
                    data: pd.DataFrame, 
                    output_path: Optional[str] = None, 
                    sheet_name: str = 'Sheet1') -> bool:
        """
        写入 Excel 文件
        
        :param data: 要写入的 DataFrame
        :param output_path: 输出文件路径，默认为原文件路径
        :param sheet_name: 工作表名称
        :return: 是否写入成功
        """
        try:
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
    
    # 过滤数据
    filtered_df = handler.filter_data('Age', 25)
    print("\n过滤后的数据:")
    print(filtered_df)
    
    # 添加新列
    handler.add_column('Salary', [5000, 6000, 7000])
    
    # 写入新的 Excel 文件
    handler.write_excel(handler.df, 'output.xlsx')

if __name__ == '__main__':
    main() 