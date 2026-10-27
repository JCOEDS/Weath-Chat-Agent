import os
import requests

from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_deepseek import ChatDeepSeek

# 初始化DeepSeek模型
model = ChatDeepSeek(
    model="deepseek-flash",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
)

#城市经纬度坐标，参考自https://www.latlong.net/category/cities-236-15.html
CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
}

#WMO天气代码映射表，参考自https://open-meteo.com/en/docs#api_form
WEATHER_CODE_MAP = {
    0: "晴",
    1: "大部分晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "毛毛雨",
    53: "中毛毛雨",
    55: "大毛毛雨",
    56: "轻度冻毛毛雨",
    57: "重度冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻度冻雨",
    67: "重度冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷阵雨（无冰雹）",
    96: "轻度雷阵雨伴有冰雹",
    99: "重度雷阵雨伴有冰雹",
}

#get_weather工具，用于查询指定城市的天气
@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气，当用户询问某个城市天气时调用此工具""" 
    if city not in CITY_COORDS:
        return f"暂未收录{city}的天气信息,目前仅支持：北京、上海、广州。"

    coords= CITY_COORDS[city]
    try:    
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0],
                "longitude": coords[1],
                "current_weather": True,
            },
            timeout=5,      #防止程序长时间等待
        )
        resp.raise_for_status()  #如果响应状态码不是200，将抛出异常
        data = resp.json() 
        current = data["current_weather"]
        code = current["weathercode"]
        #将天气代码映射为中文描述，如果没有对应的描述，则返回未知天气
        weather_text = WEATHER_CODE_MAP.get(code, f"未知天气({code})")
        #返回天气信息字符串
        return f"{city}当前天气为{weather_text},气温{current['temperature']}°C，风速{current['windspeed']} km/h。"
    
    except Exception as e:              #捕获异常，返回错误信息
        return f"查询{city}天气时发生错误({type(e).__name__}): {str(e)}"

#创建一个DeepSeek智能体，集成get_weather工具
agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="你是deepseek，你是一个天气查询助手，用户会询问某个城市的天气，你需要调用get_weather工具来获取天气信息。",
    checkpointer=InMemorySaver(),
)

#配置智能体的线程ID，确保每次对话都是独立的
config = {"configurable": {"thread_id": "user-chat-1"}}

#开始对话的标志
print("对话开始，输入quit退出")

#用户输入循环，直到用户输入"quit"结束
while True:
    user_input = input("用户: ")
    if user_input.strip().lower() == "quit": #避免大小写和空格影响判断
        break

#调用智能体进行对话，传入用户输入和配置
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
    )

#打印助手的回复
    print(f"助手: {result['messages'][-1].content}")