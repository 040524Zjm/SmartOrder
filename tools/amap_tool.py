"""
高德工具模块：
起始地，目的地 -> 转换成经纬坐标，地理位置编码
距离 -> 骑行、步行、驾车 -
配送距离范围 - 路径规划

"""
import logging
from json import JSONDecodeError
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import json

def create_session_with_retries():
    # 1.创建session对象
    session = requests.Session()
    # 2.定义重试机制
    retry_rule = Retry(
        total=3, # 总共重试次数
        backoff_factor=1, # (back,,)*(2^重试次数-1) 退避因子
        status_forcelist=[429, 500, 502, 503, 504, 505] # 429:请求过快
    )
    # 3.创建HTTP适配器，自定义HTTP请求
    adapter = HTTPAdapter(max_retries=retry_rule)
    # 4.适配器挂在到session
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def safe_request(base_url: str, params: dict) -> Optional[Dict]:
    """安全的HTTP请求，处理重试和SSL降级"""

    # 1.HTTP（加密）协议请求：1.ssl协议过期或者错误 -> 降级HTTP
    # 2.HTTP协议的网络连接没建立，建立网络连接超时了，读取超时。

    try:
        # 1.得到带重试机制的session对象
        session = create_session_with_retries()
        # 2.发送请求
        response = session.get(url=base_url, params=params, timeout=10)

        response.raise_for_status()  # 遇到【400-600】状态码都抛出异常
        return response.json()  # 网络传输的字节反序列化成字典对象 【字节：方便网络传输、IO读写->对象：应用程序方便处理】
    except requests.exceptions.SSLError as e:
        try:
            http_request_url = base_url.replace('https://', 'http://')
            response = session.get(url=http_request_url, params=params, timeout=10)
            response.raise_for_status()  # 遇到【400-600】状态码都抛出异常
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f'HTTP协议的请求发送失败，原因是{e}')
            raise requests.exceptions.RequestException(f'HTTP协议的请求发送失败，原因{e}')
    # HTTPS
    except requests.exceptions.RequestException as e:
        logging.error(f'HTTPS协议的请求发送失败，原因是{e}')
        raise requests.exceptions.RequestException(f'HTTPS协议的请求发送失败，原因{e}')

    except json.decoder.JSONDecodeError as e:
        logging.error(f'解析响应结果失败，原因是{e}')
        raise JSONDecodeError(f'反序列化失败，原因{e}')








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

















































































