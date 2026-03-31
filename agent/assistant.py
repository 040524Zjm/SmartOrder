"""
智能点餐助手主程序
LangChain中Agent组建作用， 根据自然语言选择工具、调用工具
包含工具选择的LLM系统
1.自动选择合适的工具
2.调用相应工具并返回结果
3.提供自然、有好的对话体验
======================================================
1.找到工具2.调用工具（是否输出后再润色）
def 函数描述要准确，模型看
"""

from langchain.agents import create_agent
from tools.llm_tool import call_llm
from typing import Dict, Any
from agent.mcp import general_inquiry, menu_inquiry, delivery_check_tool

import json



class SmartRestaurantAssistant:
    """小助手 类agent"""
    def __init__(self):
        # 给Agent封装工具: tools 未来需要封装工具的名字和工具的对象
        self.tools = {
            "general_inquiry": general_inquiry,
            "menu_inquiry": menu_inquiry,
            "delivery_check_tool": delivery_check_tool
        }
        self.instruction = """你是一个智能餐厅助手的意图分析器。
        请分析用户问题意图，并且选择最合适的工具来处理：

        工具说明：
        1. general_inquiry: 处理餐厅常规咨询（营业时间、地址、电话、优惠活动、预约等）
        2. menu_inquiry: 处理智能菜品推荐和咨询（推荐菜品、介绍菜品、询问菜品信息、点餐等）
        3. delivery_check_tool: 处理配送范围检查（查询某个地址是否在配送范围内、能否送达等）

        你必须严格按照以下JSON格式返回，不要包含任何其他文字：
        {
            "tool_name": "工具名称",
            "format_query": "处理后的用户问题"
        }

        正确示例：
        用户："你们几点营业？" -> {"tool_name": "general_inquiry", "format_query": "营业时间"}
        用户："推荐川菜系列的菜品" -> {"tool_name": "menu_inquiry", "format_query": "推荐川菜"}
        用户："能送到武汉大学吗？" -> {"tool_name": "delivery_check_tool", "format_query": "武汉大学"}

        重要规则：
        - 只返回纯JSON，不要有任何额外字符和解释
        - 确保JSON格式完全正确
        - tool_name必须是以下之一：general_inquiry, menu_inquiry, delivery_check_tool
        - format_query要简洁明了地概括用户问题

        记住：如果你错误的选择工具，系统将会出现崩溃。
        """
        pass

        """
        可能的错误：
        
        ```json
        {
        
        }
        =====================
        如下的json：
        {
        
        }
        """

    def _clean_llm_response(self, llm_response_content: str):
        """清洗LLM输出"""

    def _analyze_intention(self, user_query: str) -> Dict[str, Any]:
        """意图分析"""
        # 1.调用模型
        llm_response_str = call_llm(user_query, self.instruction)
        # 2.解析str -> json # 必须得是非常干净的字符串才可以，但llm可能错
        # 简单清洗

        llm_response_dict = json.loads(llm_response_str)
        # 3.返回
        return llm_response_dict


    def execute_tool(self, tool_name: str, tool_param: str) -> Dict[str, Any]:
        """执行工具"""
        try:
            tool_obj = self.tools[tool_name]
            if self.tools[tool_name] is None:
                raise ValueError(f"Invalid tool name: {tool_name},工具不可用")
            # 调用工具
            if tool_name == 'general_inquiry':
                tool_result = tool_obj.invoke({"query": tool_param}) # str
            elif tool_name == 'menu_inquiry':
                tool_result = tool_obj.invoke({"query": tool_param}) # str
            else:
                tool_result = tool_obj.invoke({"address": tool_param, "travel_mode": "2"}) # Dict 默认用电动车骑行

            return tool_result
        except Exception as e:
            raise Exception(f'查询功能不可用，{e}')

    def invoke(self, user_query: str):
        # 和小助手（Agent）聊天
        # 1.分析用户的意图（找工具）
        structured_tool = self._analyze_intention(user_query)
        # 1.1工具名字
        tool_name = structured_tool['tool_name']
        # 1.2工具参数
        tool_param = structured_tool['format_tool']
        print(f'工具名字：{tool_name}，工具参数：{tool_param}')
        # 2.调用工具
        tool_result = self.execute_tool(tool_name, tool_param)
        # 3.返回工具结果
        return tool_result







# 全局方法 给service用
def chat_with_assistant(user_query: str):
    """智能小助手对话"""
    try:
        # 1.实例化小助手
        assistant = SmartRestaurantAssistant()
        # 2.调用聊天方法
        assistant_response = assistant.invoke(user_query)
        print(f'小助手的回复：\n{assistant_response}')
        # 3.返回小助手的结果
        return assistant_response
    except Exception as e:
        raise Exception(f'服务内部故障，暂不可用：{e}')














