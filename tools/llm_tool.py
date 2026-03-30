"""
提供了通用的LLM调用
"""
import os
from langchain_openai import ChatOpenAI
# from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
load_dotenv()




def call_llm(query, system_instruction:str) -> str:
    """
    通用LLM处理
    :param query: 问题
    :param system_instruction: 某个业务对应的提示词是什么system
    :return:
    """
    # 1.定义模型实例
    api_key = os.getenv("DASHSCOPE_API_KEY")
    api_base = os.getenv("DASHSCOPE_API_BASE")
    model_name = os.getenv("DASHSCOPE_MODEL_NAME")

    if not api_key or not api_base or not model_name:
        raise ValueError("模型配置信息不全")

    # llm = init_chat_model(model='', model_provider='', api_key=api_key,base_url=api_base) # 除了deepseek国内模型不能
    llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key,openai_api_base=api_base)
    # 2.定义提示词模板对象(PromptTemplate ChatPromptTemplate)
    # 实例化， 调用类方法
    #role:AI/Human/System
    chat_prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{query}")
    ])

    # chat_prompt.from_template(system_instruction='AI专家', query='AI好就业吗？')
    # 3.定义Chain -> LCEL语法 管道符 "" ｜ "" ｜ JSON
    chain = chat_prompt_template | llm

    # 4.执行链 Runnable(可运行) --> invoke() (llm template chain tool) (给服务端发请求)
    response = chain.invoke({'system_instruction': system_instruction, 'query': query}) # 1.先去调用chat_prompt_template的invoke('模板中的变量')：结果：格式化后的模板（变量已经赋值了） --> llm.invoke()
    # response 是AIMessage类型 -> content 包含大模型结果
    # 5.解析结果
    return response.content


if __name__ == '__main__':
    result = call_llm(query="当下AI就业环境到底怎么样？",system_instruction="您是一位AI就业分析的市场专家，请客观回答用户咨询的就业问题")
    print(result)





