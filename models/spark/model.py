# coding:utf-8
import json
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

with open('./config.json', 'r') as conf_file:
    config = json.load(conf_file)
    config  = config['spark']

#星火认知大模型Spark Max的URL值，其他版本大模型URL值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_URL = config['spark_url']
#星火认知大模型调用秘钥信息，请前往讯飞开放平台控制台（https://console.xfyun.cn/services/bm35）查看
SPARKAI_APP_ID = config['appid']
SPARKAI_API_SECRET = config['api_secret']
SPARKAI_API_KEY = config['api_key']
#星火认知大模型Spark Max的domain值，其他版本大模型domain值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_DOMAIN = '4.0Ultra'

spark = ChatSparkLLM(
        spark_api_url=SPARKAI_URL,
        spark_app_id=SPARKAI_APP_ID,
        spark_api_key=SPARKAI_API_KEY,
        spark_api_secret=SPARKAI_API_SECRET,
        spark_llm_domain=SPARKAI_DOMAIN,
        streaming=False,
    )

def spark_turtlebot(input):
    messages = [ChatMessage(role="system", content=
                            '''
                            只可调用以下这些方法(不要重新定义这些方法,不需要重新定义类),根据以下需求生成对应的Python代码段(必须使用self前缀!!!),控制移动机器人按照指定的动作执行(只需要输出控制代码段!!只需要输出控制代码段!!只需要输出控制代码段!!): self.forward(x) #机器人前进x米; self.backward(x) #机器人后退x米: self.left(x) #机器人左转x度; self.right(x) #机器人右转x度: self.stop() #机器人停下。  
                            示例1:
                            输入: 前进5米, 左转90度, 再后退3米, 最后停下。
                            输出：
                            ```python
                            self.forward(5)
                            self.left(90)
                            self.backward(3)
                            self.stop()
                            ```
                            示例2:
                            输入: 走一个边长为0.5米的等边三角形。
                            输出：
                            ```python
                            self.forward(0.5)
                            self.left(120)
                            self.forward(0.5)
                            self.left(120)
                            self.forward(0.5)
                            self.stop()
                            ```
                            '''),
                ChatMessage(role="user",content=input)]
    handler = ChunkPrintHandler()
    a = spark.generate([messages], callbacks=[handler])
    print(a.flatten()[0].generations[0][0].text)
    return a.flatten()[0].generations[0][0].text

def spark_tello(input):
    messages = [ChatMessage(role="system", content=
                            '''
                            你将使用python为一个无人机编写一段控制程序，控制无人机用户指定的动作执行。无人机提供了以下api可以供你调用。
                            api:
                            flip(direction: str) #在竖直方向上，无人机翻转一圈，可向前后左右四个方向翻转；参数direction取值："forward"、"back"、"left"、"right"
                            land() #无人机降落
                            takeoff() #无人机起飞
                            move(direction: str, x: int) #无人机移动，可向前后左右上下六个方向移动；参数direction取值："forward"、"back"、"left"、"right"、"up", "down"；参数x取值：20-500，单位为厘米
                            get_height() #获取无人机当前高度，返回值单位为厘米
                            rotate_right(x: int) #在水平方向上，无人机向右旋转x度，参数x取值：1-360
                            rotate_left(x: int) #在水平方向上，无人机向左旋转x度，参数x取值：1-360
                            示例1:
                            输入: 起飞，接着向上飞行0.5米，然后向左旋转90度，最后降落。
                            输出：
                            ```python
                            takeoff()
                            move("up", 50)
                            rotate_left(90)
                            land()
                            ```
                            示例2:
                            输入: 在水平方向上飞一个边长为0.5米的等边三角形。
                            输出：
                            ```python
                            move("forward", 50)
                            rotate_right(120)
                            move("forward", 50)
                            rotate_right(120)
                            move("forward", 50)
                            ```
                            示例3:
                            输入: 飞行到2米的高度，连续向右翻转3次，然后在水平方向上飞一个边长为0.5米的正方形。
                            输出：
                            ```python
                            # 飞行到2米的高度，连续向右翻转3次，然后在水平方向上飞一个边长为0.6米的正方形
                            height_now = get_height()
                            distance_to_2m = 200 - height_now
                            if (distance_to_2m > 0):
                                move("up", distance_to_2m)
                            elif (distance_to_2m < 0):
                                move("down", -distance_to_2m)
                            for i in range(3):
                                flip("right")
                            move("forward", 60)
                            rotate_left(90)
                            move("forward", 60)
                            rotate_left(90)
                            move("forward", 60)
                            rotate_left(90)
                            move("forward", 60)
                            ```
                            '''),
                ChatMessage(role="user",content=input)]
    handler = ChunkPrintHandler()
    a = spark.generate([messages], callbacks=[handler])
    print(a.flatten()[0].generations[0][0].text)
    return a.flatten()[0].generations[0][0].text

def spark_default(input, prompt="你是一个智能的AI"):
    messages = [ChatMessage(role="system", content=prompt),
                ChatMessage(role="user",content=input)]
    handler = ChunkPrintHandler()
    a = spark.generate([messages], callbacks=[handler])
    print(a.flatten()[0].generations[0][0].text)
    return a.flatten()[0].generations[0][0].text

if __name__ == '__main__':
    # print(spark_tello('起飞，然后向左连续翻转5次，最后降落。'))
    print(spark_default('你好'))