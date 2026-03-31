"""
点餐服务
smart_chat chat_with_assistant
delivery_check 配送范围展示
get_menu 菜单区域数据展示
"""
from tools.amap_tool import PathInputModel






def get_menu():
    """获取菜单区域数据展示"""
    from tools.db_tool import get_menu_item
    return get_menu_item()


def check_delivery_range(address: str, model:PathInputModel):
    """获取配送范围展示"""
    from tools.amap_tool import check_delivery_range
    return check_delivery_range(address, model)


def smart_chat(user_query: str):
    """
    对话接口
    :param user_query: 问题
    :return:
    """
    from agent.assistant import chat_with_assistant

    return chat_with_assistant(user_query)



