import json
import string

tools = [
    {
        "type": "function",
        "function":{
            "name": "get_weather",
            "description": "Get today's weather of a location, the user should supply a location first.",
            "parameters":{
                "type": "object",
                "properties":{
                    "location":{
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Retrieve the current user's profile information, including their name, premium status, and saved preferences.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    
]



def get_weather(location: str, **kwargs)->str:
    return f"The weather in {location} is sunny!"


def get_user_profile(**kwargs):
    # 无需外部 API，直接返回系统设定好的 Mock 数据
    user_data = {
        "username": "Alex",
        "membership": "VIP",
        "language_preference": "English",
        "home_city": "Beijing",
        "interests": ["AI Technology", "Sci-Fi Movies"]
    }
    return json.dumps(user_data)


available_tools = {
    "get_weather": get_weather,
    "get_user_profile": get_user_profile
}