# 需要引入使用的函数
from function.nowtime import auto_nowtime as query_nowtime
from function.weather import auto_weather as query_weather

# 编辑 functions
functions = [
  {
    "name": "query_nowtime",
    "description": "查询当前时间。",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": ["status"]
    }
  },
  {
    "name": "query_weather",
    "description": "Query weather.",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "Witch city wants to search."
        }
      },
      "required": ["weather"]
    }
  }
]