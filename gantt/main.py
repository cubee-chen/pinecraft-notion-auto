from collections import defaultdict
from datetime import timedelta
from pprint import pprint

class GanttGenerator:
    '''
    This class is used for a single project
    (i.e. one Notion page in prjDB)
    for EACH USER
    '''
    def __init__(self, start_date, end_date, N, btm_mission_dict, nested_mission_dict):
        self.start_date = start_date  # start date of project
        self.end_date = end_date  # end date of project
        self.N = N  # number of bottom missions
        self.btm_mission_dict = btm_mission_dict
        self.nested_mission_dict = nested_mission_dict

    def _error_handling(self, msg):
        return {
            "success": False,
            "error_msg": str(msg),
            "result": None
        }

    def main_algo(self):
        
        from graph import Graph
        # ----- Initialize Graph -----
        start_node = 0
        end_node = self.N+1
        g = Graph(self.N+2)   
        Num_depend_used = []

        # ----- Add Edges -----
        for i in range(self.N):
            i += 1
            depend_list = self.btm_mission_dict[i]["depend_list"]

            # Add start edge
            if len(depend_list) == 0:
                g.addEdge(start_node, i)
            # Add middle edge
            else:
                for j in range(len(depend_list)):
                    g.addEdge(depend_list[j], i)
                    Num_depend_used.append(depend_list[j])

        #　Add end edge
        miss_num = [x for x in range(1, self.N+1) if x not in Num_depend_used]
        for i in range(len(miss_num)):
            g.addEdge(miss_num[i], end_node)

        # Get all paths
        all_paths = g.allPaths(start_node, end_node)
            
        # ----- identify critical path -----
        critical_spend = 0
        
        for path in all_paths:
            path = path[1:-1] # omit start and end node
            
            total_spend = 0
            for node in path:
                total_spend += self.btm_mission_dict[node]["spend"]
                
            if total_spend > critical_spend:
                critical_spend = total_spend
                critical_path = path

                # Add start and end node back to critical path since we omitted them earlier.
                critical_path.insert(0, start_node)
                critical_path.append(end_node)

        # Move critical path to the end of all_paths, so that it will overwrite other paths at the end.
        all_paths.remove(critical_path)
        all_paths.append(critical_path)

        # print(f"critical_path:{critical_path}")

        # ====================================
        #  Calculating ES & EF with propogation
        #  Store Bottom mission in "date_dict"
        #  Store Parent and Child in "nested_mission_dict"       
        # ====================================

        date_dict = defaultdict(dict)
        # ----- Calculate ES & EF for bottom mission -----
        for path in all_paths:
            path = path[1:-1] # omit start and end node

            # forward propagation
            current_start = self.start_date
            for node in path:            
                ES = current_start
                EF = ES + timedelta(days=self.btm_mission_dict[node]["spend"])
                current_start = EF
                date_dict[node]["ES"] = ES.strftime("%Y-%m-%d")
                date_dict[node]["EF"] = EF.strftime("%Y-%m-%d")

            # backward propagation
            current_end = self.end_date
            for node in reversed(path):
                LF = current_end
                LS = LF - timedelta(days=self.btm_mission_dict[node]["spend"])
                current_end = LS
                date_dict[node]["LS"] = LS.strftime("%Y-%m-%d")
                date_dict[node]["LF"] = LF.strftime("%Y-%m-%d")
                
            #print("path", path, "propogation done successfully")

        # pprint(date_dict)

        # ----- Calculate ES & EF for Parent and Child mission -----
        for p in range(len(self.nested_mission_dict)):
            for c in range(len(self.nested_mission_dict[p])-3): # omit 'ES', 'EF', 'parent_page_id'
                btm_list = self.nested_mission_dict[p][c]["btm_node"]
                smallest_c_es = min(date_dict[node]["ES"] for node in btm_list)
                largest_c_ef = max(date_dict[node]["EF"] for node in btm_list)

                self.nested_mission_dict[p][c]["ES"] = smallest_c_es
                self.nested_mission_dict[p][c]["EF"] = largest_c_ef
            
            child_list = [child for child in self.nested_mission_dict[p]][3:]
            smallest_p_es = min(self.nested_mission_dict[p][child]["ES"] for child in child_list)
            largest_p_ef = max(self.nested_mission_dict[p][child]["EF"] for child in child_list)
            self.nested_mission_dict[p]["ES"] = smallest_p_es
            self.nested_mission_dict[p]["EF"] = largest_p_ef   
            
        # -----------------------
        return {
            "success": True,
            "error_msg": None,
            "result":{
                "critical_path": critical_path,
                "date_dict": date_dict,
                "btm_mission_dict": self.btm_mission_dict,
                "nested_mission_dict": self.nested_mission_dict,
            }
        }

    def clear_all(self) ->None:
        for i in range(self.N):
            i += 1
            self.btm_mission_dict[i]['title'] = self.btm_mission_dict[i]['title'].lstrip("$")

    def run(self):
        self.clear_all()
        return self.main_algo()

