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
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from json import JSONDecodeError
from tools.llm_tool import call_llm
from typing import Dict, Any
from agent.mcp import general_inquiry, menu_inquiry, delivery_check_tool
import time
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

        self.max_retries = 3 # 最大重试次数
        self.backoff = 1 # 间隔

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
        # 1.markdown '```json {}```'
        if llm_response_content.startswith('```json'):
            llm_response_content = llm_response_content[7:]
        if llm_response_content.endswith('```'):
            llm_response_content = llm_response_content[:-3]

        # 2.json嵌套(有效json) '{"tool_name": {"name": "tom"}, "format_query": "营业时间"}'
        start_index = llm_response_content.find('{') # 左第一个
        end_index = llm_response_content.rfind('}') # 右第一个

        if start_index != -1 and end_index != -1 and end_index > start_index:
            clean_response = llm_response_content[start_index:end_index+1]
            return clean_response
        raise ValueError(f'不是一个有效的json格式字符串')


    def _analyse_intention_fallback(self, user_query: str) -> Dict[str, Any]:
        """基于关键词列表规则 来降级处理"""
        # todo 列表匹配 - 正则匹配 - 语义相似性匹配（嵌入模型：语义在空间距离） - LLM相似性匹配（文本模型） - 经典机器学习算法（泛化弱，提前标准数据）
        """兜底意图分析"""
        logger.info("使用兜底意图分析")
        # 1.配送相关关键词
        delivery_keywords = ["配送", "送达", "送到", "送货", "外卖", "地址", "区域", "范围"]
        # 2.菜单相关关键词
        menu_keywords = ["菜单", "菜品", "推荐", "点餐", "招牌", "特色", "什么好吃", "有什么菜"]
        # 3.常规咨询关键词
        # general_keywords = ["营业", "时间", "电话", "预约", "预订", "位置", "在哪", "多少钱", "优惠", "活动"]
        # 检查配送意图
        if any(keyword in user_query for keyword in delivery_keywords):

            return {"tool_name": "delivery_check_tool", "format_query": user_query}

        # 检查菜单意图
        elif any(keyword in user_query for keyword in menu_keywords):
            return {"tool_name": "menu_inquiry", "format_query": user_query}

        # 默认常规咨询
        else:
            return {"tool_name": "general_inquiry", "format_query": user_query}

    def _analyze_intention(self, user_query: str, last_error: str) -> Dict[str, Any]:
        """意图分析"""
        instruction = self.instruction
        # 1.是有有错
        if last_error:
            instruction += f"\n\n上次解析失败，错误信息：{last_error}\n请根据错误信息修正JSON格式，确保返回正确的JSON。"
        # 2.调用模型
        llm_response = call_llm(user_query, instruction)
        # 解析str -> json # 必须得是非常干净的字符串才可以，但llm可能错
        # 3.简单清洗
        clean_response = self._clean_llm_response(llm_response)
        # 4.解析
        llm_response_dict = json.loads(clean_response)
        # 5.校验字典key是否有效
        if not all(key in llm_response_dict for key in ['tool_name', 'format_query']):
            raise ValueError(f'json格式错误，缺少字段.{llm_response_dict}')
        # 6.校验工具名是否在工具集中
        if llm_response_dict['tool_name'] not in self.tools:
            raise ValueError(f'工具不存在: {llm_response_dict["tool_name"]}')
        # 7.返回模型结果
        return llm_response_dict


    def analyse_intention_with_retry(self, user_query: str) -> Dict[str, Any]:
        """
        带重试的意图分析， 以及手动降级
        :param user_query:
        :return:
        """
        logger.info(f'带重试的意图分析')
        last_error = None
        # 1.重试
        for i in range(self.max_retries): # 0 1 2
            try:
                llm_response_dict = self._analyze_intention(user_query, last_error)
                logger.info(f'意图分析成功: {llm_response_dict}')
                return llm_response_dict
            except(ValueError, JSONDecodeError) as e:
                last_error =str(e)
                logger.warning(f'意图分析失败,开始第{i+1}次重试') # 异常吃掉
                if i < self.max_retries - 1:
                    time.sleep(self.backoff)
        logger.error(f'重试次数已经达到了最大{self.max_retries}')

        # 2.走降级
        self._analyse_intention_fallback(user_query)


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
        structured_tool = self.analyse_intention_with_retry(user_query)
        # 1.1工具名字
        tool_name = structured_tool['tool_name']
        # 1.2工具参数
        tool_param = structured_tool['format_query']
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
        assistant_response = assistant.invoke(user_query or "介绍一下您们餐厅的基本信息")
        print(f'小助手的回复：\n{assistant_response}')
        # 3.返回小助手的结果
        return assistant_response
    except Exception as e:
        raise Exception(f'服务内部故障，暂不可用：{e}')






if __name__ == '__main__':
    print(f'1.常规问题')
    chat_with_assistant(user_query='你们餐厅的联系方式是什么？')
    print(f'2.菜品推荐问题对话')
    chat_with_assistant(user_query='鲁菜系列的菜品')
    print(f'3.配送范围问题')
    chat_with_assistant(user_query='海淀区大学能送到吗？')