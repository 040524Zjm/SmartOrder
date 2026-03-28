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
















