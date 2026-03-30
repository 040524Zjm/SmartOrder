"""
FastAPI接口
定义FastAPI应用实例
提供三个主要接口
POST / chat
POST / delivery
POST / menu / list
"""
from fastapi import FastAPI
from pydantic import BaseModel # 数据验证
from typing import List
from tools.amap_tool import PathInputModel
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




app = FastAPI(title='智能点餐助手API接口', description='智能点餐应用主要暴露在三个接口分别为智能对话接口、配送查询接口、菜品列表接口', )

@app.get('/')
def hello_word():
    """测试项目根路径访问是否可用"""
    return {'hello': 'world'}
@app.get('/healthy')
def healthy():
    """测试项目请求路径访问是否可用"""
    return {'message': '请求路径访问健康'}

# 定义数据模型
# 菜品列表展示
class MenuListResponse(BaseModel): # dict - kv -> 对象 （校验，转换）
    """菜品列表相应"""
    success: bool # 有无数据True， False
    menu_items: List[dict] # 菜品列表
    count: int # 菜品数量
    message: str # 响应消息


# 响应数据模型
class DeliveryResponse(BaseModel):
    """配送查询响应"""
    success: bool  # 成功(True) or 失败的标识（False）
    in_range: bool #  配送是否在配送范围内(True False)
    distance: float # 配送距离(公里 km)
    formatted_address: str # 格式化地址
    duration:float # 配送时间（秒）
    message: str  # (前端要展示的配送完整消息内容)
    travel_mode: PathInputModel # 配送模式 (1:步行 2:骑电动车 3:驾车)
    input_address: str # 输入原始内容

class DeliveryRequest(BaseModel):
    """配送查询请求"""
    address: str
    travel_mode: PathInputModel = "2"  # 1=步行, 2=骑电动车, 3=驾车



@app.get('/menu/list', response_model=MenuListResponse)
async def menu_list_endpoint():
    """菜品列表区展示"""

    # 调用service
    from service.Order_service import get_menu
    menu_items = get_menu()
    if not menu_items:
        return MenuListResponse(
            success=False,
            menu_items=[],
            count=0,
            message='暂无菜品列表可用'
        )

    return MenuListResponse(
        success=True,
        menu_items=menu_items,
        count=len(menu_items),
        message=f'成功查询到{len(menu_items)}道菜品信息'
    )

@app.post("/delivery", response_model=DeliveryResponse)
async def delivery_endpoint(request: DeliveryRequest):
    """
    配送查询接口

    检查指定地址是否在配送范围内
    """
    try:
        # 1.调用service
        from service.Order_service import check_delivery_range
        check_delivery_range_response = check_delivery_range(request.address, request.travel_mode)
        if check_delivery_range_response['status'] == 'fail':
            return DeliveryResponse(
                success=False,
                in_range=False,
                distance=0.0,
                formatted_address=request.address,
                duration=0.0,
                message=check_delivery_range_response['message'],
                travel_mode=request.travel_mode,
                input_address=request.address
            )

        return DeliveryResponse(
            success=True,
            in_range=check_delivery_range_response['in_range'],
            distance=check_delivery_range_response['distance'],
            formatted_address=check_delivery_range_response['formatted_address'],
            duration=check_delivery_range_response['duration'],
            message=check_delivery_range_response['message'],
            travel_mode=request.travel_mode,
            input_address=request.address
        )
    except Exception as e:
        logger.error(f'配送范围查询失败： {e}')
        return DeliveryResponse(
            success=False,
            message=f'配送范围查询失败{e}'
        )












