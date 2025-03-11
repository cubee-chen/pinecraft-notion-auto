class Graph:
    '''
    This class is used for Modified Topological Sort.
    '''
    def __init__(self, vertices):
        
        from collections import defaultdict
        self.V = vertices
        self.graph = defaultdict(list)
    
    def addEdge(self, u, v):
        self.graph[u].append(v)
    
    def allPaths(self, start, end):
        # ----- Return a list of all paths from start to end -----
        result = []
        path = []
        self._dfsPaths(start, end, path, result)
        return result
    
    def _dfsPaths(self, current, end, path, result):
        path.append(current)
        
        # ----- If we reached the target, record the path -----
        if current == end:
            result.append(path.copy())
        else:
            # Continue DFS for all adjacent nodes.
            for nxt in self.graph[current]:
                self._dfsPaths(nxt, end, path, result)

        # Backtrack
        path.pop()