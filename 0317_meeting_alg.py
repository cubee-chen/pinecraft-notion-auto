import pandas as pd
from datetime import datetime, timedelta
import re
import asyncio #誘因結構西西
from collections import defaultdict

#已測試完
def filter_pages_calender(response,today , one_week_later):
    ## 會把response裡面的page過濾掉，只留下符合日期的page
    ## 會把沒有enddate的刪掉
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
        end_time   = max(datetime.strptime(p_time_end, "%H:%M").time(), end.time()).strftime("%H:%M")     #type:str
           
        

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

#已完成，chatgpt，尚未驗證
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
        slot_origianl = properties["時段"]["title"][0]["plain_text"] #填錯可能會抱錯
        slot = normalize_time_slot(slot_origianl)

        i = (7 - date_start_weekday)%7                 #key的順序
        for weekday in string_of_weekday:
            if(properties[weekday]["rich_text"] and properties[weekday]["rich_text"][0]["plain_text"].strip() != ""):      #欄位不為空
                date_i = date_start + timedelta(days=i)
                result[date_i].append(slot)
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
    para_time_end   = "23:00"            #排定會議的結束時刻
    para_time_freq  = "30min"

    # Step 1: Time slots (30-min intervals)
    time_slots = pd.date_range(para_time_start, para_time_end, freq=para_time_freq).strftime("%H:%M").tolist()

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
                    
                    try:
                        start_idx = time_slots.index(start)
                        end_idx = time_slots.index(end)
                        temp_df.iloc[start_idx:end_idx, temp_df.columns.get_loc(user)] = 1
                    except ValueError:
                        print(f"Warning: {start} or {end} not found in time slots")
        
        # Count available users
        available_count = (temp_df == 0).sum(axis=1)
        
        # Fill into result DataFrame
        result_df[date] = available_count
    
    return result_df #yang:輸出dictionary之類的時間

#result: 最快會議日期、最佳會議日期、最佳線上會議時間、最慢會議日期
'''

    先自動做一個像是timeline的表格
    把時間做成一個一個block，合格的block需要包含(主要負責人、大於)

    問題:線上與實體會議
    地點問題，有可能那個地點根本排不出來，也有可能



    最快會議日期:找出
    最佳會議日期:找出包含負責人/人最多/地點
    最佳線上會議時間:前後空出10分鐘
    最慢會議日期

    

    開會時程



    9點~12點

    15hr
    90 單位
    14*90總共
'''





