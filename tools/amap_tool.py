"""
高德工具模块：
起始地，目的地 -> 转换成经纬坐标，地理位置编码
距离 -> 骑行、步行、驾车 -
配送距离范围 - 路径规划

"""
from typing import Dict, Any, Optional
import requests


def create_session_with_retries():
    # 1.创建session对象
    session = requests.Session()
    # 2.定义重试机制

def safe_request(base_url: str, params: dict) -> Optional[Dict]:
    """安全的HTTP请求，处理重试和SSL降级"""
    pass





def geocode_address(address: str) -> Dict[str, Any]:
    """
    地理编码 地址 - 坐标
    :param address:  用户输入查询的地址
    :return: 地理编码结果 - 格式化后的地址、经纬度
    """
    # 1.请求url

    # 2.param

    # 3.发请求

    # 4.解析结果

















































































