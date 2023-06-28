import requests
import time


def auto_weather(city: str, record):
    try:
        res = requests.get(
            url=f"https://api.seniverse.com/v3/weather/daily.json?key=SCYrvkytJze9qyzOh&location={city}"
        ).json().get("results")[0].get("daily")
        res[0]["date"] = "今天 " + time.strftime('%Y-%m-%d', time.localtime())
        res[1]["date"] = "明天 " + time.strftime('%Y-%m-%d', time.localtime(time.time()+86400))
        res[2]["date"] = "后天 " + time.strftime('%Y-%m-%d', time.localtime(time.time()+172800))
        return res
    except Exception as e:
        print(e)
        return "Fail"
