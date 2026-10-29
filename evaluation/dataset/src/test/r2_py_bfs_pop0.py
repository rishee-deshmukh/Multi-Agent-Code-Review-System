def shortest_path(graph, start, goal):
    queue = [(start, [start])]
    seen = {start}
    while queue:
        node, path = queue.pop(0)  # @label quadratic medium -- list.pop(0) is O(n); use collections.deque
        if node == goal:
            return path
        for neighbour in graph.get(node, ()):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append((neighbour, path + [neighbour]))
    return None
