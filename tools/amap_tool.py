"""
高德工具模块：
起始地，目的地 -> 转换成经纬坐标，地理位置编码
距离 -> 骑行、步行、驾车 -
配送距离范围 - 路径规划

"""
import logging
from json import JSONDecodeError
from typing import Dict, Any, Optional, Literal, Union
import requests
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import json
import os
from dotenv import load_dotenv
load_dotenv()


# 静态检查：typing 不在运行时约束
# 动态检查：pydantic库，运行时做校验。

PathInputModel = Literal['1','2','3'] # 外部,只能是其中
PathModel = Literal['walking', 'electrobike', 'driving']
# 路径转换工具
class PathModeConverter:
    """路径模式转换工具"""
    # 映射关系 外部输入的路径模式 -> 内部使用的路径模式
    MODE_MAPPING = {
        "1": "walking",
        "2": "electrobike",
        "3": "driving"
    }

    @classmethod
    def to_mode(cls, mode_input: Union[PathInputModel]) -> PathModel:
        """将输入的模式1转换为内部使用的方式"""
        if mode_input in cls.MODE_MAPPING:
            return cls.MODE_MAPPING[mode_input]
        else:
            raise ValueError(f'不支持的路径模式: {mode_input}，支持的模式：{list(cls.MODE_MAPPING.keys())}')


@dataclass # 快速对对象赋值
class AmapConfig:
    AMAP_API_KEY: str=os.getenv('AMAP_API_KEY')
    MERCHANT_LONGITUDE: str=os.getenv('MERCHANT_LONGITUDE')
    MERCHANT_LATITUDE: str=os.getenv('MERCHANT_LATITUDE')
    DELIVERY_RADIUS: int=int(os.getenv('DELIVERY_RADIUS'))
    DEFAULT_PATH_MODE = os.getenv('DEFAULT_PATH_MODE')

    def __post_init__(self):
        """自动调用"""
        if self.AMAP_API_KEY is None:
            raise ValueError('Amap_API_KEY not found!')

# 创建实例
config = AmapConfig()

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
    try:
        # 1.请求url
        request_url = "https://restapi.amap.com/v3/geocode/geo"
        # 2.param
        params = {
            'address': address,
            'key': os.getenv('AMAP_API_KEY'),
        }
        # 3.发请求
        response = safe_request(request_url, params)
        # 4.解析结果
        # 4.1失败
        if response['status'] != '1':
            return {
                'success': False,
                'message': response['info'],
            }
        # 4.2成功
        geocodes = response['geocodes'][0]
        return {
            'formatted_address': geocodes['formatted_address'],
            'location': geocodes['location'],
            'success': True
        }

    except Exception as e:
        logging.error(f'调用高德地图进行地理位置编码失败，原因：{e}')
        raise e


def calculate_distance(
        origin_location: str, destination_location: str,
        path_mode_input: PathInputModel or None
    ) -> Dict[str,Any]:
    """
    不同的路径模式计算两个地点之间的距离和预计时间

    Args:
        origin_location: 起点经纬度
        destination_location:  终点经纬度
        path_mode_input:  路径模式，1:步行，2:骑行，3:驾车

    Returns:
        Dict: 路径结果，包含路径模式、距离、预计时间等

    """
    try:
        # 1.校验APIkey
        if config.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY 不存在")
        # 2.外部路径mode转换
        inner_model = PathModeConverter.to_mode(path_mode_input)

        # 3.构建请求URL
        path_endpoint = {
            'walking': 'https://restapi.amap.com/v5/direction/walking',
            'electrobike': 'https://restapi.amap.com/v5/direction/electrobike',
            'driving': 'https://restapi.amap.com/v5/direction/driving'
        }
        # 4.构建param
        params = {
            'key': config.AMAP_API_KEY,
            'origin': origin_location,
            'destination': destination_location,
        }
        if inner_model == 'driving':
            params['show_fields'] = 'cost'
        # 5.发送请求
        response = safe_request(path_endpoint[inner_model], params)
        # 6.解析结果
        if response['status'] != '1':
            return {
                'success': False,
                'message': response['info']
            }
        path = response['route']['paths'][0]
        duration = path['duration'] if inner_model == 'electrobike' else path['cost']['duration']
        return {
                "distance":int(path["distance"]), # 两点之间距离
                "duration":duration, # 两点之间某一种路径规划下的时间
                "success":True # 状态
            }
    except Exception as e:
        logging.error(f'调用高德地图进行路线规划失败，原因{e}')
        raise e

# 已经有了获得坐标和计算距离的方法了，接下来检查是不是在配送范围
def check_delivery_range(address: str, path_mode_input: PathInputModel =  None) -> Dict[str,Any]:
    """检查地址是否在配送范围内

    Args:
    address: 用户输入的地址
    path_mode_input: 路径模式，支持 "1"(walking), "2"(bicycling), "3"(driving)。如果为None则使用配置的默认模式
    Returns:
    包含检查结果的 Dict 对象
    """
    # 1.获取重点坐标
    try:
        geocode_result = geocode_address(address)
        if not geocode_result['success']:
            return {
                'status': 'fail',
                'message': geocode_result['message']
            }
        # 2.看距离
        # 起点
        origin_location = f'{config.MERCHANT_LONGITUDE}, {config.MERCHANT_LATITUDE}'
        calculate_distance_result = calculate_distance(origin_location, geocode_result['location'], path_mode_input=path_mode_input or config.DEFAULT_PATH_MODE)
        if not calculate_distance_result['success']:
            return {
                "status": 'fail',
                'message': calculate_distance_result['message']
            }
        # 两点距离， 时间， 配送范围 格式化地址 message
        distance = calculate_distance_result['distance'] # 除1000——米转千米
        in_range = distance <= config.DELIVERY_RADIUS
        return {
            "status": "success",
            "in_range": in_range, # 是不是在配送范围
            "distance": round(int(distance)/1000, 2), # 距离
            "duration": int(calculate_distance_result['duration']), #  时间
            "formatted_address": geocode_result['formatted_address'],
            "message": (
                f"配送地址：{geocode_result['formatted_address']}\n"
                f"配送距离：{distance/1000:.2f}公里\n"
                f"配送状态：{'在配送范围内' if in_range else '超出配送范围'}"
            )
        }
    except Exception as e:
        logging.error(f'调用高德地图进行配送范围检查失败，原因：{e}')
        raise e


if __name__ == '__main__':
    # print(geocode_address(address='北京大学')) # {'formatted_address': '北京市海淀区北京大学', 'location': '116.310918,39.992873', 'success': True}
    # print(geocode_address(address='新中关购物中心')) # {'formatted_address': '北京市海淀区新中关购物中心', 'location': '116.315280,39.978319', 'success': True}

    # print(calculate_distance(origin_location='116.310918,39.992873', destination_location='116.315280,39.978319')) #
    # {'distance': 2202, 'duration': '508', 'status': 'success'}
    # 不同模式的使用

    test_address = "北京大学" #  测试地址
    print("\n=== 测试不同路径模式 ===")
    # 测试步行模式 (1)
    print("\n1. 步行模式测试:")
    result1 = check_delivery_range(test_address, "1")
    minutes = result1['duration'] // 60
    seconds = result1['duration'] % 60
    print(f"步行模式距离: {result1['distance']}公里 时间: {result1['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result1['message']}")

    # 测试骑行模式 (2)
    print("\n2. 骑行模式测试:")
    result2 = check_delivery_range(test_address, "2")
    minutes = result2['duration'] // 60
    seconds = result2['duration'] % 60
    print(f"骑行模式距离: {result2['distance']}公里 时间: {result2['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result2['message']}")

    # # 测试驾车模式 (3)
    # print("\n3. 驾车模式测试:")
    # result3 = check_delivery_range(test_address, "3")
    # minutes = result3['duration'] // 60
    # seconds = result3['duration'] % 60
    # print(f"步行模式距离: {result3['distance']}公里 时间: {result3['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    # print(f"是否在配送范围内: {result3['message']}")






