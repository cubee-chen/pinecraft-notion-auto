import asyncio

'''
3/10 to ddm
I.  不知道接收trigger這件事是誰要做，我猜是ddm，然後如果有被trigger到的話就可以啟用我的演算法這樣
II. 目前會在ddm程式出現的應該只有:
        1.為單個project創建user_list，內容包含email和user的兩個關於時間的db
        2.main_algorithm_meeting_time
III.關於會議排程的output我還沒想好怎麼做，我的想法是丟出可以的時間以及系統判別的最佳時間排列的一個表格之類的，然後使用者再去手動再行事曆加入會議，或者是我們跳出一個可以讓使用者選擇的欄位(超難)


'''


def timetable_to_time(timetable_db: dict[str, str]):
        #ddm: 這裡我會需要user_notion裡面的"課表"整個databasequery的dictionary
            #(感覺不用整理直接整包丟過來也可以)

    result = None
    return result

def calender_to_time(calender_db: dict[str, str]):
    #ddm: 這裡我會需要user_notion裡面的"行事曆"整個databasequery的dictionary
        # (看你要不要整理完再丟過來，畢竟calender_db內容會隨著使用者使用而線性增長，如果你在設計儲存資料時就有聰明data_structure的話也可以依你那邊為準)

    #yang: 這邊會篩選出1.距離當天兩周內或一周內的時間2.不是任務或是工作的項目(如果是工作的話就會被擋住)
    result = None
    return result


class UserSchedule:
    def __init__(self, user: dict[str, str]):
        self.email = user["email"]
        timetable_db = user["timetable_db"]
        calender_db  = user["calender_db"]
        self.schdule = calender_to_time(calender_db)
        self.timetable = timetable_to_time(timetable_db)
    
    '''
    def update_timetable(self, timetable_db):
        self.timetable = timetable_to_time(timetable_db)
    
    def update_calender(self, calender_db):
        self.schdule = calender_to_time(calender_db)    
    '''



class UsersList:
    def __init__(self, users: list[dict[str, str]]): 
        self.userdata = {user["email"]: UserSchedule(user) for user in users}
    #ddm: users包含一個prj內所有人各自的email, 行事曆的總資料dictionary與課表的總資料dictionary
    #ddm: 到時候可能就是創立這個class而已

    
    '''
    def update_users(self, new_users: list[dict[str, str]]):
        for user in new_users:
            if user["email"] not in self.pollers:
                self.pollers[user["email"]] = UserSchedule(user)   
    '''


def main_algorithm_meeting_time(project_users: UsersList):
    result = None    
    return result #yang:輸出dictionary之類的時間





