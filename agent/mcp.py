"""
LangChain中各个工具的定义， 三个：常规，菜品，距离配送范围
"""
import logging
import os

from langchain_core.tools import tool, ToolException
from tools.llm_tool import call_llm
from tools.pinecone_tool import search_menu_items_with_ids
from tools.amap_tool import check_delivery_range, PathInputModel
from typing import Dict, Any




def load_prompt_template(prompt_file_name) -> str:
    """加载指定目录下提示词文件"""
    try:
        # 1. 定位当前文件目录
        current_file_path = os.path.abspath(__file__)
        # print(current_file_path) # /Users/zjm/PycharmProjects/LLM_2026_demo/SmartOrder/agent/mcp.py
        # print(repr(current_file_path)) # '/Users/zjm/PycharmProjects/LLM_2026_demo/SmartOrder/agent/mcp.py'
        current_dir_dir = os.path.dirname(current_file_path) # agent
        project_dir = os.path.dirname(current_dir_dir) # SmartOrder

        # 2.拼接提示词目录
        prompt_path = os.path.join(project_dir, 'prompt', f'{ prompt_file_name }.txt') # /Users/zjm/PycharmProjects/LLM_2026_demo/SmartOrder/prompt

        # 3.读取指定路径下的文件
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f'无法加载指定文件{prompt_file_name}的提示词文件，原因是{e}')
        return '无法加载到指定的提示词内容，请根据用户的问题，直接提供帮助'


@tool
def general_inquiry(query: str,) -> str:
    """
        常规问询工具

        处理用户的一般性问题，包括但不限于：
        - 餐厅介绍和服务信息
        - 营业时间和联系方式
        - 优惠活动和会员服务
        - 其他非菜品相关的咨询

        Args:
            query: 用户的问询内容
            # context: 可选的上下文信息，用于提供更精准的回复

        Returns:
            str: 针对用户问询的智能回复

        Raises:
            ToolException: 当处理查询时发生错误
    """
    try:
        # 1.加载常规问题提示词
        prompt_template = load_prompt_template('general_inquiry')

        # 记忆组件内容 TODO
        """
        context = "记忆组件"
        full_query = f'当前历史对话的内容{context}, 当前用户问题{query}, 请基于以上上下文信息来回答用户问题' if context \
        else f'当前没有历史对话，{query},基于一般信息来回答用户问题'
        """
        # 2.LLM调用
        llm_response = call_llm(query, prompt_template)

        # QA写入记忆组件 TODO

        # 3.返回（组装自定义数据）
        return llm_response
    except Exception as e:
        raise ToolException(f'常规问询工具处理查询时发生错误，原因是{e}')


@tool
def menu_inquiry(query: str) -> Dict[str, Any]:
    """
    智能菜品咨询工具

    专门处理与菜品相关的所有查询，包括：
    - 菜品介绍和详细信息
    - 价格和营养信息
    - 菜品推荐和搭配建议
    - 过敏原和饮食限制相关问题
    - 菜品可用性和特色介绍

    该工具会自动通过语义搜索找到最相关的菜品信息，然后基于这些信息回答用户问题。

    Args:
        query: 用户关于菜品的具体问题

    Returns:
        Dict[str, Any]: 包含推荐建议和菜品ID的字典
        {
            "recommendation": "基于菜品信息的推荐建议",
            "menu_ids": ["菜品ID1", "菜品ID2"]
        }

    Raises:
        ToolException: 当处理菜品查询时发生错误
    """
    # 1.加载提示词模版
    prompt_template = load_prompt_template('menu_inquiry')

    # 2.上下文（向量数据库）
    similar_result = search_menu_items_with_ids(query)
    if similar_result and similar_result['contents']:
        menu_content_context ='\n'.join([f' -{item}' for item in similar_result['contents']])
        # 当前从向量数据库中检索到的菜品信息:

        # -{菜品1}
        # -{菜品2}

        # 当前用户问题:
        # {query}

        # 请基于以上的上下文信息来回答用户问题
        full_query = f"当前从向量数据库中检索到的菜品信息:\n\n{menu_content_context}\n当前用户问题:\n{query}\n\n请基于以上的上下文信息来回答用户问题"

    else:
        full_query = f"暂无相关菜品信息:\n\n当前用户问题:\n{query}\n\n请基于一般的菜品知识信息来回答用户提出的相关问题"

    # 3.调用
    llm_response = call_llm(full_query, prompt_template)

    # 4.字典
    return {
        "recommendation": llm_response, # 菜品推荐建议
        "menu_ids": similar_result['ids'] # 前端得到id来框选相关，所以应该用response的结果用正则来筛选结果，此处略
        # 因为topk=2，所以query问推荐宫保鸡丁时候，获取了两个id，可能有一个不是宫保鸡丁，但是模型调用时候回答会剔除
    }


@tool
def delivery_check_tool(address: str, travel_mode: PathInputModel) -> str:
    """
    配送范围检查工具

    检查指定地址是否在配送范围内，并提供距离信息。

    Args:
        address: 配送地址
        travel_mode: 距离计算方式 (1=步行距离, 2=骑行距离, 3=驾车距离)

    Returns:
        str: 配送检查结果的格式化信息

    Raises:
        ToolException: 当配送检查失败时
    """

    # 调用配送检查功能:不用调用模型，调用已有工具amap
    check_delivery_range_result  = check_delivery_range(address , travel_mode)
    # 处理返回
    MODE_MAPPING = {
        "1": "步行距离",
        "2": "骑行距离",
        "3": "驾车距离",

    }
    try:
        if check_delivery_range_result["status"] == "success":
            status_text = "✅ 可以配送" if check_delivery_range_result["in_range"] else "❌ 超出配送范围"
            response = f"""
                配送信息查询结果：
            
                配送地址：{check_delivery_range_result['formatted_address']}
                配送距离：{check_delivery_range_result['distance']}公里 ({MODE_MAPPING[travel_mode]})
                配送状态：{status_text}
                        """.strip()
        else:
            response = f"❌ 配送查询失败：{check_delivery_range_result['message']}"
        return response
    except Exception as e:
        raise ToolException(f"配送检查失败: {str(e)}")




if __name__ == '__main__':
    # print(f'1.常规查询：\n')
    # general_inquiry_result1 = general_inquiry.invoke(input='请问你们餐厅营业时间是什么时候？')
    # general_inquiry_result2 = general_inquiry.invoke('请问你们餐厅营业时间是什么时候？')
    # general_inquiry_result3 = general_inquiry.invoke({"query": '请问你们餐厅营业时间是什么时候？'}) # 必须是query
    # print(general_inquiry_result1)
    # print(general_inquiry_result2)
    # print(general_inquiry_result3)

    # print(f'2.菜品推荐：\n')
    # menu_inquiry_result = menu_inquiry.invoke({'query': '请给我推荐一些素食的菜品'})
    # print(f'菜品推荐工具结果：{menu_inquiry_result}')

    # 菜品推荐工具结果：{'recommendation': '您好！根据您的素食需求，我为您精心挑选了以下几款美味又健康的素食菜品：
    # \n\n1. 清炒时蔬（¥15.00）\n- 这道菜选用当季最新鲜的时令蔬菜，经过简单清炒保留了蔬菜最原始的营养和清甜口感。\n- 蒜蓉的加入不仅提升了菜品的香气，还增加了风味层次。\n- 口感清爽，非常适合追求健康饮食的朋友。
    # \n\n2. 蒜蓉西兰花（¥12.00）\n- 选用新鲜的西兰花，富含维生素C和膳食纤维，非常适合作为减肥期间的健康选择。\n- 配以新鲜蒜蓉和少量橄榄油，保留了食材本身的营养成分。\n- 蒸炒的方式最大程度地锁住了食材的营养，同时保持了脆嫩的口感。
    # \n\n这两道菜都属于素食类别，不含有任何动物性成分，且均标注为“无过敏源”，您可以放心食用。如果您想要更加清淡爽口的选择，我会更推荐清炒时蔬；如果想尝试更有营养密度的菜肴，蒜蓉西兰花会是个不错的选择。
    # \n\n此外，我们所有的素食菜品都是现点现做，确保您品尝到最新鲜的食材。您还可以搭配我们的糙米粥或豆浆作为主食，形成更均衡的餐食组合。
    # \n\n请问您对哪一道菜更感兴趣？或者需要我提供更多关于这些菜品的信息吗？', 'menu_ids': ['3', '5']}

    print(f'3.菜品配送范围\n')
    delivery_check_result = delivery_check_tool.invoke({'address': '海淀区清华大学', 'travel_mode': '1'})
    # data={'address': '海淀区清华大学', 'travel_mode': 1}
    # delivery_check_result2 = delivery_check_tool(**data)
    print(f'配送范围工具结果：{delivery_check_result}')
    # print(f'配送范围工具结果：{delivery_check_result2}')



