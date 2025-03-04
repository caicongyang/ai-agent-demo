import httpx
import json
import csv
from bs4 import BeautifulSoup
from time import sleep
import ssl

def fetch_stores(size=500):
    """抓取大润发门店信息"""
    
    # 存储所有门店数据
    all_stores = []
    
    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.rt-mart.com.cn/stores',
        'Connection': 'keep-alive'
    }
    
    # 创建自定义SSL上下文
    ssl_context = ssl.create_default_context()
    ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    
    # 配置客户端
    client_config = {
        'timeout': 30.0,
        'verify': ssl_context,
        'follow_redirects': True,
        'http2': True
    }
    
    try:
        # 创建客户端
        with httpx.Client(**client_config, headers=headers) as client:
            # 先访问首页获取cookies
            client.get('https://www.rt-mart.com.cn/stores')
            
            # 构建URL
            url = f'https://www.rt-mart.com.cn/stores/store?size={size}'
            
            # 发送请求
            response = client.get(url)
            response.raise_for_status()
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有门店项
            store_items = soup.find_all('div', class_='store-item')
            
            # 处理每个门店数据
            for store in store_items:
                # 获取门店标题
                title = store.find('p', class_='store-right__title').text.strip()
                
                # 获取门店信息
                info_div = store.find('div', class_='store-right__info')
                info_items = info_div.find_all('p')
                
                # 解析地址信息
                address = ''
                for item in info_items:
                    if '门店地址：' in item.text:
                        address = item.text.replace('门店地址：', '').strip()
                        break
                
                # 从标题中提取省市和店名
                title_parts = title.split('-')
                if len(title_parts) >= 2:
                    city = title_parts[0].strip()
                    name = title_parts[1].strip()
                    
                    # 提取省份（这里简单处理，实际可能需要更复杂的映射）
                    province = city.split('市')[0] if '市' in city else city
                    
                    store_info = {
                        'province': province,
                        'name': name,
                        'address': address
                    }
                    all_stores.append(store_info)
                    print(f'获取到门店: {province} - {name}')
            
            print(f'成功获取 {len(all_stores)} 条门店数据')
            
    except httpx.RequestError as e:
        print(f'请求发生错误: {e}')
    except Exception as e:
        print(f'发生未知错误: {e}')
        
    return all_stores

def save_to_csv(stores, filename='rt_mart_stores.csv'):
    """将门店信息保存到CSV文件"""
    
    if not stores:
        print('没有数据可保存')
        return
        
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['province', 'name', 'address'])
            writer.writeheader()
            writer.writerows(stores)
        print(f'数据已保存到 {filename}')
    except IOError as e:
        print(f'保存文件时发生错误: {e}')

def main():
    # 抓取门店数据
    stores = fetch_stores()
    
    # 打印统计信息
    print(f'\n总共抓取到 {len(stores)} 家门店')
    
    # 保存数据到CSV文件
    save_to_csv(stores)

if __name__ == '__main__':
    main() 