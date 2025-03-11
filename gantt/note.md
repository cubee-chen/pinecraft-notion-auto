## GanttGenerator使用說明
- 20250311 commit

複製整個 gantt directory，因為main.py需要呼叫graph.py(modified topological sort)。

call_gantt.py (__dirpath__ = ./test/)
此檔案展示lifeos_system如何import並呼叫GanttGenerator。

FetchData Class已經寫好（包在lifeos_system裡面），用於抓取初始化ganttGenerator所需的所有資料。但get_project_info()這個method 前是抓一個page裡面的projectDB的property，但現在我們改了，所以可能會噴error(?)
UpdateData Class也已經寫好（包在lifeos_system裡面），將output的gantt 傳回notion。

error handling 還沒有全部完成。