from notion_client import Client
import os
from dotenv import load_dotenv

import pandas as pd
from datetime import datetime, timedelta
import re
import asyncio #誘因結構西西
from collections import defaultdict
import json
import bisect

import sys
sys.stdout.reconfigure(encoding='utf-8') #用來處理一些特殊符號在terminal的print


#已測試完
def filter_pages_calender(response,today , one_week_later):
    ## 會把response裡面的page過濾掉，只留下符合日期的page
    ## 會把沒有end date的刪掉
    filtered_pages = []
    
    for page in response['results']:
        date_info = page['properties']['Date']['date']
        start_date = datetime.fromisoformat(date_info['start']).date()
        end_date = None
        if date_info.get('end'):
            end_date = datetime.fromisoformat(date_info['end']).date()

        # 檢查 start date 是否在範圍內,檢查 end date 是否在範圍內
        if today <= start_date <= one_week_later:
            if end_date and today <= end_date <= one_week_later:
                filtered_pages.append(page)

    return filtered_pages

#已測試完
def convert_pages_to_timeslots(filtered_pages, p_time_start, p_time_end, p_today, p_one_week_later):

    time_slots = defaultdict(list)

    for page in filtered_pages:
        date_property = page["properties"]["Date"]["date"]

        # 將 ISO 格式的時間字串轉為 datetime
        start = datetime.fromisoformat(date_property.get("start"))
        end   = datetime.fromisoformat(date_property.get("end"))

        #start_date = start.strftime("%Y-%m-%d")
        start_date = max(p_today , start.date()) #type:datetime
        end_date   = min(p_one_week_later, end.date()) #type:datetime
        print(f"start date = {start_date}")
        print(f"end date = {end_date}")

        start_time = max(datetime.strptime(p_time_start, "%H:%M").time(), start.time()).strftime("%H:%M") #type:str
        if end.time() == datetime.strptime("00:00", "%H:%M").time():
            end_time = (datetime.strptime(p_time_end, "%H:%M")+timedelta(minutes=5)).time().strftime("%H:%M")
        else:
            end_time = min((datetime.strptime(p_time_end, "%H:%M")+timedelta(minutes=5)).time(), end.time()).strftime("%H:%M")     #type:str

        period = (end_date - start_date).days
        print(f"Period = {period}")
        #print(f"type = {type(period)}")

        if(period == 0): #ok
            time_slots[start_date.strftime("%Y-%m-%d")].append(f"{start_time}-{end_time}")
        elif(period == 1):
            time_slots[start_date.strftime("%Y-%m-%d")].append(f"{start_time}-{p_time_end}")
            time_slots[end_date.strftime("%Y-%m-%d")].append(f"{p_time_start}-{end_time}")

        else:
            time_slots[start_date.strftime("%Y-%m-%d")].append(f"{start_time}-{p_time_end}")
            time_slots[end_date.strftime("%Y-%m-%d")].append(f"{p_time_start}-{end_time}")
            for i in range(1,period):
                date_key = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                time_slots[date_key].append(f"{p_time_start}-{p_time_end}")

    return dict(time_slots)

def calender_to_time(calender_db: dict[str, list[str]], para_date_start, para_date_period, para_time_start, para_time_end)   -> dict[str, list[str]]:
    today = para_date_start.date()
    one_week_later = today + timedelta(days=para_date_period-1)
    calender_db_filter = filter_pages_calender(calender_db, today, one_week_later)
    result = convert_pages_to_timeslots(calender_db_filter, para_time_start, para_time_end, today, one_week_later)
    return result

#已完成
def normalize_time_slot(slot: str): #slot = "09:00-10:00", "9:00-10:00", "09：00-10：00", "09:00~10:00", "09:00 - 10:00".
    # Step 1: Replace Chinese colon to English colon
    slot = slot.replace('：', ':')
    # Step 2: Remove extra spaces
    slot = slot.replace(' ', '')
    # Step 3: Replace various separators (~, –, —, etc.) with "-"
    slot = re.sub(r'[~–—−]', '-', slot)
    # Step 4: Split by "-" to get start and end
    try:
        start, end = slot.split('-')
    except ValueError:
        print(f"Warning: Cannot parse slot '{slot}'")
        return None, None

    # Step 5: Normalize start and end time to "HH:MM" format 
    start = f"{int(start.split(':')[0]):02}:{start.split(':')[1]}"
    end =   f"{int(end.split(':')[0]):02}:{end.split(':')[1]}"

    return f"{start}-{end}" 

#已完成，self，尚未驗證
def timetable_to_time(timetable_db: dict[str, list[str]], all_dates) -> dict[str, list[str]]:

    date_start = datetime.today()
    date_start_weekday = date_start.weekday() #0~6,0 is Monday, 6 is Sunday
    string_of_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    result = {date: [] for date in all_dates}
    timetable_db_result = timetable_db["results"]

    for page in timetable_db_result:
        properties = page["properties"]
        slot_origianl = properties["時段"]["title"][0]["plain_text"] #填錯可能會抱錯 #有空的資料
        slot = normalize_time_slot(slot_origianl)

        i = (7 - date_start_weekday)%7                 #key的順序
        for weekday in string_of_weekday:
            if(properties[weekday]["rich_text"] and properties[weekday]["rich_text"][0]["plain_text"].strip() != ""):      #欄位不為空
                date_i = (date_start + timedelta(days=i)).strftime("%Y-%m-%d")
                result[date_i].append(slot) #!!!!抓這裡的bug 可以先測試
            i+=1
            i = i%7    
    return result

class UserSchedule:
    def __init__(self, user: dict[str, str], all_dates, para_date_start, para_date_period, para_time_start, para_time_end):
        self.email = user["email"]
        timetable_db = user["timetable_db"]
        calender_db  = user["calender_db"]
        self.schdule = calender_to_time(calender_db, para_date_start, para_date_period, para_time_start, para_time_end)
        self.timetable = timetable_to_time(timetable_db, all_dates)
    
    '''
    def update_timetable(self, timetable_db):
        self.timetable = timetable_to_time(timetable_db)
    
    def update_calender(self, calender_db):
        self.schdule = calender_to_time(calender_db)    
    '''

class UsersList:
    def __init__(self, users: list[dict[str, str]], all_dates, para_date_start, para_date_period, para_time_start, para_time_end): 
        self.userdata = {user["email"]: UserSchedule(user, all_dates, para_date_start, para_date_period, para_time_start, para_time_end) for user in users}

    '''
    def update_users(self, new_users: list[dict[str, str]]):
        for user in new_users:
            if user["email"] not in self.pollers:
                self.pollers[user["email"]] = UserSchedule(user)   
    '''

#還沒檢查!!!!!
def get_unavailable_list(users_list: UsersList):
    result = dict()

    for email, user_schedule in users_list.userdata.items():
        result[email] = dict()
        combined_schedule = defaultdict(list)

        # Combine calendar schedule
        for date, slots in user_schedule.schdule.items():
            combined_schedule[date].extend(slots)

        # Combine timetable schedule
        for date, slots in user_schedule.timetable.items():
            combined_schedule[date].extend(slots)

        # Remove duplicates and sort the slots for each date
        for date, slots in combined_schedule.items():
            # Remove None entries (in case normalize_time_slot returned None)
            clean_slots = list(filter(lambda x: x is not None, slots))
            # Sort and remove duplicates
            clean_slots = sorted(set(clean_slots))
            result[email][date] = clean_slots

    return result


def main_algorithm_meeting_time(users: list[dict[str, str]]):   
    
    #Step 0: Parameters setup
    para_date_start  = datetime.today()  #排定會議的開始日期 (now)
    para_date_period = 7                 #一個list包含開始到結束的日期 (int)
    para_time_start = "09:00"            #排定會議的開始時刻
    para_time_end   = "23:00"            #排定會議的結束時刻 (不能設超過23:30)
    para_time_freq  = "30min"            #使用者不要條哈哈

    # Step 1: Time slots (30-min intervals)
    time_slots = pd.date_range(para_time_start, para_time_end, freq=para_time_freq).strftime("%H:%M").tolist()
    time_slots_dt = [datetime.strptime(t, "%H:%M") for t in time_slots]

    # Step 2: Generate next 7 days' dates  
    all_dates = [(para_date_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(para_date_period)]

    #print("Dates:", all_dates)  # Debug: Show generated dates

    # Step 3: 
    users_list = UsersList(users, all_dates, para_date_start, para_date_period, para_time_start, para_time_end)
    user_unavailable = get_unavailable_list(users_list)

    # Step 4: Initialize result DataFrame
    result_df = pd.DataFrame(0, index=time_slots, columns=all_dates)
    
    for date in all_dates:
        # Temp DataFrame for this date
        temp_df = pd.DataFrame(0, index=time_slots, columns=user_unavailable.keys())
        
        # Fill unavailable slots
        for user, user_dates in user_unavailable.items():
            if date in user_dates:
                for slot in user_dates[date]:
                    start, end = slot.split("-")
                    start = f"{int(start.split(':')[0]):02}:{start.split(':')[1]}"
                    end = f"{int(end.split(':')[0]):02}:{end.split(':')[1]}"
                    start_dt = datetime.strptime(start, "%H:%M")
                    end_dt = datetime.strptime(end, "%H:%M")

                    try:
                        start_idx = bisect.bisect_right(time_slots_dt, start_dt) - 1
                        end_idx = bisect.bisect_left(time_slots_dt, end_dt)
                        temp_df.iloc[start_idx:end_idx, temp_df.columns.get_loc(user)] = 1
                    except ValueError: #!!!這裡有bug 請撰寫一個可以把時間補滿的判斷
                        print(f"Warning: {start} or {end} not found in time slots")
        
        # Count available users
        available_count = (temp_df == 0).sum(axis=1)
        
        # Fill into result DataFrame
        result_df[date] = available_count
    
    return result_df #yang:輸出dictionary之類的時間 
    #!!!輸出格式要用啥呢




#------------------------------------------------------------------

if __name__ == "__main__":
    
    load_dotenv()
    NOTION_API_TOKEN = os.getenv("ADMIN_TOKEN") 
    notion = Client(auth=NOTION_API_TOKEN)


    
        # Step 1: 設定多個使用者資訊 (token & db_id)
    users_info = [
        {
            "email": "user1",
            "calendar_db_id": "1bd832c707fa805ca059f06e110f984d",
            "timetable_db_id": "1bd832c707fa8040b109f18d88ac3303"
        },
        {
            "email": "user2",
            "calendar_db_id": "1bd832c707fa818f9422ea93936becc7",
            "timetable_db_id": "1bd832c707fa81b098ecccc0dc99d11e"
        },
        {
            "email": "user3",
            "calendar_db_id": "1bd832c707fa81a2a485cb2ed2e49298",
            "timetable_db_id": "1bd832c707fa8150b76efbbd78ecaff6"
        }        
        # 可再加更多
    ]

    # Step 2: 從 Notion 讀取每位使用者的 database
    users = []
    
    for user in users_info:
        print(f"Fetching data for {user['email']} ...")
        calendar_db  = notion.databases.query(database_id = user['calendar_db_id'])
        timetable_db = notion.databases.query(database_id = user['timetable_db_id'])

        if calendar_db is None or timetable_db is None:
            print(f"Failed to fetch for {user['email']}, skipping.")
            continue

        # Step 3: 整理成 main_algorithm 所需格式
        user_entry = {
            "email": user['email'],
            "calender_db": calendar_db,
            "timetable_db": timetable_db
        }
        users.append(user_entry)
    
    #formatted_output = json.dumps(users, indent=4, ensure_ascii=False)
    #print(formatted_output)
    
    # Step 4: 呼叫主算法
    print("Calculating available meeting time slots...")
    result_df = main_algorithm_meeting_time(users)

    # Step 5: 輸出
    print(result_df)


