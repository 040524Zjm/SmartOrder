# 数据库查询
import os
import logging

import mysql.connector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()


class DataBaseConnection:
    """数据库管理相关操作"""
    def __init__(self):
        """初始化数据库配置信息"""
        self.host = os.getenv('MYSQL_HOST', 'localhost')
        self.port = os.getenv('MYSQL_PORT', '3306')
        self.user = os.getenv('MYSQL_USER_NAME', 'root')
        self.password = os.getenv('MYSQL_USER_PASSWORD')
        self.db_name = os.getenv('MYSQL_DB_NAME', 'menu')

        self.connection = None
        self.cursor = None

    def initialize_connection(self) -> bool:
        """初始化连接和游标对象"""
        try:
            # 初始化连接对象
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.db_name,
                charset= 'utf8'
            )
            # 初始化游标对象 : 执行SQL语句获得结果
            self.cursor = self.connection.cursor(
                dictionary=True, # 获取结果为字典，非元组
            )
            logger.info(f'数据库{self.db_name}连接初始化成功')
            return True

        except mysql.connector.Error as e:
            logger.error(f"数据库{self.db_name}连接初始化失败", {e})
            return False

    def disconnect_connection(self):
        """断开数据库连接"""
        try:
            # 游标
            if self.cursor:
                self.cursor.close()
                self.cursor = None  # 无引用,易于监控

            # 连接
            if self.connection and self.connection.is_connected():
                self.connection.close()
                self.connection = None
            logger.info(f'数据库{self.db_name}断开连接成功')
            return True

        except mysql.connector.Error as e:
            logger.error(f"数据库{self.db_name}断开连接失败", {e})
            return False


    def __enter__(self):
        """进入上下文管理器
        调用时机：实例化后，在with代码块执行
        返回上下文管理对象（自己）
        """
        if self.initialize_connection():
            logger.info(f'数据库{self.db_name}连接初始化成功')
            return self
        else:
            raise Exception

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器
        调用时机：with代码块执行后
        exc_type: 异常类型
        exc_val:异常类型对应具体说明
        exc_tb:记录那个模块 那一行代码出现错误

        """
        self.disconnect_connection()

        if exc_type:
            logger.error(f'数据库{self.db_name}连接异常退出', {exc_val})

        return False # False 只是告诉有异常，继续向上抛出 Ture：告诉有异常，不会向上。

def get_all_menu_items() -> str:
    """
    查menuitem中所有菜品信息，并对每一条菜品信息用\n连接，形成一个大字符串
    :return:
    """
    try:
        with DataBaseConnection() as db:
            # 定义SQL
            query_sql = """
                SELECT 
                    id, dish_name, price, description, category, 
                    spice_level, flavor, main_ingredients, cooking_method, 
                    is_vegetarian, allergens, is_available
                FROM menu_items 
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            # 执行SQL
            db.cursor.execute(query_sql)
            menu_items = db.cursor.fetchall()
            # 处理结果
            if not menu_items:
                logger.info(f'数据库{db.db_name}无菜品信息')
                return '无菜品信息'
            menu_item_strings = []
            for item in menu_items:
                # 格式化辣度
                spice_level_mapping = {0:"不辣", 1:"微辣", 2:"中辣", 3:"重辣"}
                format_spice_level = spice_level_mapping.get(item.get('spice_level'), "暂无辣度级别")
                # 格式化是否素食
                format_is_vegetarian = "是" if item.get('is_vegetarian') else "否"
                # 格式化菜品描述
                format_description = item.get('description') if item.get('description', '').strip() else "暂无描述"
                # 格式化主要食材
                format_main_ingredients = item.get('main_ingredients') if item.get('main_ingredients','').strip() else "暂无主要食材"
                # 格式化过敏源
                format_allergens = item.get('allergens') if item.get('allergens','').strip() else '暂无过敏源'
                # 拼接菜品结构为字符串
                menu_item_string = f"菜品ID:{item['id']}|菜品名称:{item['dish_name']}|价格:¥{item['price']:.2f}|菜品描述:{format_description}|分类:{item['category']}|辣度:{format_spice_level}|口味:{item['flavor']}|主要食材:{format_main_ingredients}|烹饪方法:{item['cooking_method']}|素食:{format_is_vegetarian}|过敏原:{format_allergens}"
                menu_item_strings.append(menu_item_string)
            logger.info(f'数据库{db.db_name}查询所有菜品信息字符串结果成功， 共{len(menu_item_strings)}条')
            # 返回处理后的结果
            return '\n'.join(menu_item_strings)
    except Exception as e:
        logger.error(f'数据库{db.db_name}查询所有菜品信息字符串结果失败', {e})
        return '数据库查询失败'

def get_menu_item():
    """
    前端菜品展示
    :return: dict(菜品)
    """
    try:
        # 定义sql
        with DataBaseConnection() as db:
            query_sql = """
                        SELECT 
                            id,
                            dish_name,
                            price,
                            description,
                            category,
                            spice_level,
                            flavor,
                            main_ingredients,
                            cooking_method,
                            is_vegetarian,
                            allergens,
                            is_available
                        FROM menu_items
                        WHERE is_available = 1
                        ORDER BY category, dish_name
                        """
            # 执行sql
            db.cursor.execute(query_sql)
            # 获取结果
            menu_items = db.cursor.fetchall()
            # 处理结果并且返回
            if not menu_items:
                logger.error(f'数据库{db.db_name}无菜品信息')
                return []

            processed_menu = []
            for item in menu_items:
                # 可视化数据 前端
                # 辣度等级转换
                spice_levels = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}
                spice_text = spice_levels.get(item['spice_level'], "未知")

                # 处理数据
                processed_item = {
                    "id": item['id'],
                    "dish_name": item['dish_name'],
                    "price": float(item['price']),
                    "formatted_price": f"¥{item['price']:.2f}",
                    "description": item['description'] or "暂无描述",
                    "category": item['category'],
                    "spice_level": item['spice_level'],
                    "spice_text": spice_text,
                    "flavor": item['flavor'] or "暂无口味",
                    "main_ingredients": item['main_ingredients'] or "暂无主要食材",
                    "cooking_method": item['cooking_method'] or "暂无烹饪方法",
                    "is_vegetarian": bool(item['is_vegetarian']),
                    "vegetarian_text": "是" if item['is_vegetarian'] else "否",
                    "allergens": item['allergens'] if item['allergens'] and item['allergens'].strip() else "暂无过敏原",
                    "is_available": bool(item['is_available'])
                }
                processed_menu.append(processed_item)
            logger.info(f'查询菜品列表成功，共 {len(processed_menu)} 条')
            return processed_menu


    except Exception as e:
        logger.error(f'查询菜品列表失败：{e}')
        return []

def test_connection():

    with DataBaseConnection() as db:
        # 测试连接
        db.cursor.execute("SELECT 1")
        test_res = db.cursor.fetchall()

        if test_res:
            logger.info(f'数据库{db.db_name}连接成功, 测试结果为: {test_res}')
        else:
            logger.error(f'数据库{db.db_name}连接失败')


if __name__ == '__main__':
    # test_connection()

    # print('测试所有菜品信息的字符串')
    # menu_item_str = get_all_menu_items()
    # print(menu_item_str)

    print('前端展示')
    menu_item_list = get_menu_item()
    for index,item in enumerate(menu_item_list, 1):
        print(f'当前是第{index}个菜品，结构{item}')