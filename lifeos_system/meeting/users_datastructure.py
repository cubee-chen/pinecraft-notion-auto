'''
for ddm:

users 是一個list of dictionary,每一組dictionary包含三的元素:
    1.user的email
    2.user的課表(timetable_db)，這個就是直接把整個database的json放進來就好
    3.user的行事曆(calender_db)，這個也是直接把整個database的json放進來就好
所以要把一個project內的user的資料都放進來

呼叫部分只有 def main_algorithm_meeting_time(users: list[dict[str, str]]):   


'''

users = [
    {
        "email": "alice@example.com",
        "timetable_db": {
            "results": [
                {
                    "properties": {
                        "時段": { "title": [ { "plain_text": "09:00-10:00" } ] },
                        "星期一": { "rich_text": [ { "plain_text": "有課" } ] },
                        "星期二": { "rich_text": [] },
                        "星期三": { "rich_text": [] },
                        "星期四": { "rich_text": [] },
                        "星期五": { "rich_text": [] },
                        "星期六": { "rich_text": [] },
                        "星期日": { "rich_text": [] },
                    }
                },
                ...
            ]
        },
        "calender_db": {
            "results": [
                {
                    "properties": {
                        "Date": { 
                            "date": { 
                                "start": "2025-03-03T09:00:00.000Z", 
                                "end":   "2025-03-03T10:00:00.000Z"
                            } 
                        }
                    }
                },
                ...
            ]
        }
    },
    ...
]
