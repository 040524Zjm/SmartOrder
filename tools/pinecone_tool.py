"""
向量数据库
存储查询菜品信息的向量化数据
"""
import os
from dotenv import load_dotenv
from openai import vector_stores
from pinecone import Pinecone
from pinecone import ServerlessSpec
from typing import List, Dict, Any
import dashscope
from http import HTTPStatus

load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




class PineconeVectorDB:
    """Pinecone向量数据库操作"""
    def __init__(self):
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY', '')
        self.dashscope_api_key = os.getenv('DASHSCOPE_API_KEY', '')
        self.pinecone_env = os.getenv('PINECONE_ENV', 'us-east-1')

        # 配置索引名字，嵌入模型名字、嵌入模型维度
        self.index_name = 'menu-item-index'
        self.embedding_model = 'text-embedding-v4'
        self.dimension = 1536

        # 配置pinecone客户端对象以及索引对象
        self.pc = None
        self.index = None


    def initialize_connection(self):
        """初始化PineCone向量数据库客户端对象以及索引对象"""
        try:
            # 初始化客户端对象
            if not self.pinecone_api_key:
                logger.error('PineCone API_KEY not found!')
                return False

            self.pc = Pinecone(api_key=self.pinecone_api_key)

            # 初始化索引对象
            if not self.pc.has_index(self.index_name):
                self.pc.create_index(
                    name=self.index_name,
                    vector_type='dense',
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=self.pinecone_env
                    )
                )

            # 获取并赋值
            self.index = self.pc.Index(self.index_name)

            logger.info('初始化向量数据库pinecone客户端及索引对象')
            return True

        except Exception as e:
            logger.error(f"初始化PineCone向量数据库客户端对象失败", {e})
            return False


    def clean_index_vector(self):
        """清空指定索引下的向量数据库[索引结构保留，只是数据丢]"""
        try:
            if not self.index and not self.initialize_connection():
                logger.error('索引不存在')
                return False

            # 判断，是否已有向量数据，如果有则删除
            vector_status = self.index.describe_index_stats()
            count = vector_status['total_vector_count']
            if count > 0:
                logger.info(f'该索引下不存在任何向量数据。')
                return True

            self.index.delete(delete_all=True)

            logger.info("成功删除索引下所有的向量数据")
            return True

        except Exception as e:
            logger.error(f"清空索引向量数据失败", {e})
            return False

    def _embedding_content(self, content:str) -> List[float]:
        """
        对文本向量化
        :param content: 文本
        :return: [0.11, 0.23, ...]
        """
        try:
            # 1.判断api key
            if not self.dashscope_api_key:
                logger.error("dashscope api_key not found!")
                return None

            # 2.发请求
            resp = dashscope.TextEmbedding.call(
                api_key=self.dashscope_api_key,
                model=self.embedding_model,
                input=content,
                dimension=self.dimension,
            )
            # 3.解析
            if resp.status_code == HTTPStatus.OK:  # 200
                logger.info(f"文本:{content}向量化成功")
                return resp.get('output').get('embeddings')[0].get('embedding')
            else:
                logger.error(f"文本:{content}向量化失败")
                return None
        except Exception as e:
            logger.error(f"文本:{content}向量化失败原因{e}")
            return None

    def _validate_datasource(self, validation_content: str) -> bool:
        """
        校验数据源
        """
        # 1.有没有
        if not validation_content:
            logger.error('数据源不存在')
            return False
        # 2.是否能用
        validate_result_str = ('当前无可用的菜品信息','查询菜品信息失败')
        # 3.判断
        return not validation_content.startswith(validate_result_str)

    def _split_content(self, split_content:str) -> List[str]:
        """切割菜品信息"""
        try:
            # 定义 递归文本切分器
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            text_spliter = RecursiveCharacterTextSplitter(
                chunk_size=100,
                chunk_overlap=0,
                separators=["\n"],
                length_function=len,
            )
            # 切
            docs = text_spliter.create_documents([split_content])
            # 切后文档列表
            clean_docs = []
            for doc in docs:
                # 提取文档对象内容
                page_content = doc.page_content
                # 小清洗
                clean_content = page_content.strip()
                clean_docs.append(clean_content)
            print(f'切割后块数：{len(clean_docs)}')
            return clean_docs
        except Exception as e:
            logger.error(f"文本切分失败", {e})
            return []
    def upsert_menu_data(self,menu_data: str = None, batch_size: int = 100, clear_existing: bool = True):
        """
        文本向量存储到PineCone向量数据库
        :param menu_data: 菜品信息
        :param batch_size: 攒够一批，大小
        :param clear_existing: 是否清空，之前索引库的向量数据
        :return:
        """

        try:

            if not menu_data:
                # 0.清除现有
                if clear_existing:
                    self.clean_index_vector()
                # 1.从数据库中查
                from tools.db_tool import get_all_menu_items
                menu_item_str = get_all_menu_items()
                # 2.校验
                if not self._validate_datasource(menu_item_str):
                    logger.error('校验数据源失败')
                    return False
                # 3.切分加载
                embedding_chunks = self._split_content(menu_item_str)
                if not embedding_chunks:
                    logger.error('切分文本数据失败')
                    return False
                # 4.向量化
                batch = []
                for line_num, chunk in enumerate(embedding_chunks, 1):
                    vectors_content = self._embedding_content(chunk)
                    # 判断向量结果
                    if not vectors_content or len(vectors_content)!=self.dimension:
                        logger.error('向量值不匹配或者维度不匹配')
                        return False
                    # 判断索引对象
                    if not self.index and not self.initialize_connection():
                        logger.error('索引不存在')
                        return False
                    # 准备元数据
                    menu_medata = {
                        'content': chunk,
                        'line_number':line_num,
                        'dis_id':f'菜品id:{line_num}', # 应该是正则表达 提取id
                        'type':'menu_item'
                    }
                    # 准备向量数据的唯一标识(假设)
                    unique_vector_id = str(line_num)
                    batch.append((unique_vector_id, vectors_content, menu_medata))
                    # 将文本向量的结果插入到向量数据库中
                    if len(batch) >= batch_size:
                        # 可以插入
                        self.index.upsert(vectors=batch)
                        batch = []
                if batch:
                    self.index.upsert(vectors=batch)

                logger.info('切分之后的文本内容成功存储到向量数据库中')
                return True

            else:
                logger.info('处理文本数据')
                logger.info('向量化文本数据')
                logger.info('向量结果存储到向量数据库')
                return False




        except Exception as e:
            logger.error(f'同步数据到向量数据库失败：{e}')
            return False

    def search_similar_menu_item(self, query: str, top_k: int = 2) -> List[Dict[str,Any]]:
        """相似性检索
        Q - A  (A -> embed(自己带向量的或传入再做) - 文档embed)
        """
        try:
            # 1.确保索引存在
            if not self.index and not self.initialize_connection():
                logger.error('索引不存在')
                return False
            # 2.对Query向量
            query_vector = self._embedding_content(query)
            # 3.判断向量是否有效
            if not query_vector or len(query_vector) != self.dimension:
                logger.error('向量值不存在或者维度不匹配')
                return False
            # 4.执行语意搜索
            similar_result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            # 5.提取相似文档结果
            matches_result = similar_result['matches']

            if not matches_result:
                logger.info('暂无查询到相似性文档')
                return []

            final_matches_result = []
            for item in matches_result:
                match_item = {
                    "id": item['id'],
                    "score": item['score'],
                    "content": item['metadata']['content'], # 原始文本
                    "line_number": item['metadata']['line_number']
                }
                final_matches_result.append(match_item)

            logger.info(f'查询到相似的文档命中个数{len(final_matches_result)}')
            return final_matches_result



        except Exception as e:
            logger.error(f'相似性检索失败：{e}')


# 定义全局实例
pinecone_db = PineconeVectorDB()

# 定义全局同步向量数据库操作方法
def pinecone_input(menu_data: str = None, clear_existing: bool = True) -> bool:
    """
    将菜品数据输入到Pinecone向量数据库

    Args:
        menu_data: 菜品数据字符串，每行一个菜品的完整信息。如果为None，则从数据库获取
        clear_existing: 是否在插入前清除现有数据，默认为True

    Returns:
        bool: 是否输入成功
    """
    return pinecone_db.upsert_menu_data(menu_data, clear_existing=clear_existing)
# 定义全局查询向量数据库操作方法
def search_menu_items(query: str, top_k: int = 2) -> List[str]:
    """
    根据查询搜索相关菜品

    Args:
        query: 查询文本
        top_k: 返回结果数量

    Returns:
        List[str]: 相关菜品信息列表
    """
    matches_result = pinecone_db.search_similar_menu_item(query, top_k=top_k)
    if not matches_result:
        return []
    return [ item['content'] for item in matches_result ]

# 前端展示使用
def search_menu_items_with_ids(query: str, top_k: int = 2) -> Dict[str, Any]:
    """
        根据查询文本搜索相似的菜品
        Args:
            query: str: 查询文本
            top_k: int: 返回的结果数量

        Returns:
            Dict[str,Any]:包含菜品内容列表和真实菜品ID列表的字典
            {
                "contents": [菜品内容列表],
                "ids": [真实菜品ID列表],
                "scores": [相似度分数列表]
            }
    """
    match_result = pinecone_db.search_similar_menu_item(query, top_k=top_k)
    if not match_result:
        return []

    ids = []
    for item in match_result:
        content = item['content']
        import re
        re_match = re.search(r"菜品ID:(\d+)",content) # 捕获组(), \d数字 +一次或者多次 r''不让python识别到符号
        id = re_match.group(1) if re_match else item['id'] # group(1)第一组
        ids.append(id)

    return {
        "contents": [item['content'] for item in match_result],
        "ids": ids,
        "scores": [item['score'] for item in match_result]
    }









if __name__ == '__main__':
    # print('\n1.测试pinecone客户端和索引的创建')
    # pinecone_db.initialize_connection()

    # print('\n2.上传菜品信息到向量数据库')
    # pinecone_db.upsert_menu_data(menu_data=None, batch_size=10)

    # print('\n3.相似性检索')
    # match_result = pinecone_db.search_similar_menu_item(query='请给我推荐川菜系列的菜品', top_k=3)
    #
    # for match in match_result:
    #     print(match)

    # print('\n4.全局方法')
    # similar_content = search_menu_items(query='请给我推荐素食系列的菜品', top_k=1)
    # for item_content in similar_content:
    #     print(item_content)

    print('\n4.菜品相似性全局检索')
    similar_content = search_menu_items_with_ids(query='请给我推荐素食系列的菜品', top_k=2)
    print(similar_content)




