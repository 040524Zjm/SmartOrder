"""
点餐服务
smart_chat chat_with_assistant
delivery_check 配送范围展示
get_menu 菜单区域数据展示
"""

def get_menu():
    """获取菜单区域数据展示"""
    from tools.db_tool import get_menu_item
    return get_menu_item()






