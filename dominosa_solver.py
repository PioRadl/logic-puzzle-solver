import igraph as ig
from igraph import Graph
from collections import defaultdict
from queue import deque
from functools import reduce
from itertools import combinations

def display_with_marked_pairs(board, pairs):
    pairs = set([tuple(sorted([get_coords(n1, board), get_coords(n2, board)])) for n1, n2 in pairs])
    board_w, board_h = len(board[0]), len(board)
    digits = 1 if board_h * board_h <= 110 else 2
    for y in range(board_h):
        for x in range(board_w):
            print(f" {board[y][x]: <{digits}} ", end="")
            if ((y, x), (y, x+1)) in pairs:
                print("—", end="")
            else:
                print(" ", end="")
        print()
        for x in range(board_w):
            print(f" {'|' if ((y, x), (y+1, x)) in pairs else ' '}{' '*(digits-1)}  ", end="")
        
        print()

def init_graph_from_board(board):
    board_w, board_h = len(board[0]), len(board)
    game_size = max([max(row)for row in board]) + 1
    g = Graph.Lattice(dim=[board_w, board_h], circular=False)

    node_to_number_mapping = [board[i//board_w][i%board_w] for i in range(board_w*board_h)]
    number_to_nodes_mapping = [[] for i in range(game_size)]
    for i, num in enumerate(node_to_number_mapping):
        number_to_nodes_mapping[num].append(i)
    
    return g, node_to_number_mapping, number_to_nodes_mapping

def find_pair_occurences(graph, number_to_nodes_mapping, num1, num2):
    result = []
    occurences1, occurences2 = number_to_nodes_mapping[num1], number_to_nodes_mapping[num2]
    # print(occurences1, occurences2)
    for occ in occurences1:
        neis = graph.neighbors(occ)
        common = set(neis).intersection(set(occurences2))
        result.extend(tuple(sorted([occ, a])) for a in common)

    return result


# Queues to use:
# - queue 1: pairs of numbers that have only one remaining occurence on the board 
# - queue 2: pairs of numbers that can only appear in a few places, where all of these places have a shared node
# - queue 3: nodes that have only one way out
# - queue -: nodes that have more than one way out but all of these ways out have the same number as neighbour  actually i dont need this one since itll be covered by grouping
# - queue 4: nodes that are separators between 2 components

def init_dicts_and_queues(graph, node_to_number_mapping):
    pairs_dict = defaultdict(set)       # occurence of a given pair of numbers
    # grouping_dict = defaultdict(list)    # list of list of numbers neighboring given number (change them to sets during the grouping algo, and add the -1s) 

    # iterate only over the odd nodes because thats enough to get all the connections without repeats
    for node, number in enumerate(node_to_number_mapping):
        for nei in graph.neighbors(node):
            number2 = node_to_number_mapping[nei]
            pair = tuple(sorted((number, number2)))
            pairs_dict[pair].add(tuple(sorted([node, nei])))

    q1 = deque()
    q2 = deque()
    q3 = deque()    # this is empty for now
    q4 = deque()    # this as well
    
    for key, val in pairs_dict.items():
        if len(val) == 1:
            q1.append(key)   
        elif len(val) < 4 and (common := list(reduce(set.intersection, map(set, val)))) and len(val) < len(graph.neighbors(common[0])):
            q2.append((key, common[0]))
        
    queues = [q1, q2, q3, q4]

    return pairs_dict, queues


def delete_connections(graph, edges, node_to_number_mapping, pairs_dict, queues):
    q1, q2, q3, q4 = queues

    for node1, node2 in edges:
        num1, num2 = node_to_number_mapping[node1], node_to_number_mapping[node2]
        sorted_nums = tuple(sorted([num1, num2]))

        # actual removing
        graph.delete_edges([(node1, node2)])
        pairs_dict[sorted_nums].remove(tuple(sorted([node1, node2])))

    for node1, node2 in edges:
        num1, num2 = node_to_number_mapping[node1], node_to_number_mapping[node2]
        sorted_nums = tuple(sorted([num1, num2]))

        # updating the queues
        val = pairs_dict[sorted_nums]

        if len(val) == 1:
            q1.append(sorted_nums)
        elif len(val) > 1 and len(val) < 4 and (common := list(reduce(set.intersection, map(set, val)))) and len(val) < len(graph.neighbors(common[0])): 
            q2.append((sorted_nums, common[0]))
        if len(graph.neighbors(node1)) == 1:
            q3.append(node1)
        if len(graph.neighbors(node2)) == 1:
            q3.append(node2)
        if graph.is_separator(node1):
            q4.append(node1)
        if graph.is_separator(node2):
            q4.append(node2)
    
    

def delete_domino(graph, node_to_number_mapping, number_to_nodes_mapping, node1, node2, pairs_dict, queues, look_for_other_occurences=True, log=False):   # this will also delete all the repeating connections 
    deleted_edges = set()
    additional_edges = set()
    num1, num2 = node_to_number_mapping[node1], node_to_number_mapping[node2]
    deleted_edges.add(tuple(sorted([node1, node2])))

    for nei in graph.neighbors(node1):
        if nei != node2 and graph.are_adjacent(nei, node1):
            deleted_edges.add(tuple(sorted([node1, nei])))
    for nei in graph.neighbors(node2):
        if nei != node1 and graph.are_adjacent(nei, node2):
            deleted_edges.add(tuple(sorted([node2, nei])))

    if look_for_other_occurences:
        occurences = find_pair_occurences(graph, number_to_nodes_mapping, num1, num2)
        for occ in occurences:
            if occ != tuple(sorted([node1, node2])) and graph.are_adjacent(*occ):
                if occ not in deleted_edges:
                    deleted_edges.add(occ)   # these are always sorted so no need to worry
                    additional_edges.add(occ)
                
    delete_connections(graph, deleted_edges, node_to_number_mapping, pairs_dict, queues)
        
    return additional_edges


def get_coords(node_num, board):
    board_w = len(board[0])
    return node_num//board_w, node_num%board_w


def solve_loop(board, graph, pairs_dict, queues, node_to_number_mapping, number_to_nodes_mapping, log=False):
    pairs = []
    q1, q2, q3, q4 = queues
    checked_all_groups = False
    game_size = len(number_to_nodes_mapping)

    while any(queues) or not checked_all_groups:
        connections_to_delete = []
        dominos_to_delete = []
        # FINDING CHANGES SECTION
        if q3:
            node1 = q3.popleft()
            if len(graph.neighbors(node1)) == 0:
                # print("Repeated entry in the queue, skipping")
                continue
            node2 = graph.neighbors(node1)[0]

            if log:
                print("---Rule #1---")
                print(f"Tile on the position {get_coords(node1, board)} can only connect to the {get_coords(node2, board)}")
            dominos_to_delete.append((node1, node2, True))
        
            pairs.append((node1, node2))
            checked_all_groups = False
    
        elif q1:
            nums = q1.popleft()

            if len(pairs_dict[nums]) == 0:
                # print("Repeated entry in the queue, skipping")
                continue

            node1, node2 = next(iter(pairs_dict[nums]))
            if log:
                print("---Rule #2---")
                print(f"Placed a domino {nums} on positions {get_coords(node1, board)} {get_coords(node2, board)} because it was the only viable position")
            dominos_to_delete.append((node1, node2, False))
            
            pairs.append((node1, node2))
            checked_all_groups = False  # do this each time there is a change
            
        elif q2:
            nums, common_node = q2.popleft()

            if len(pairs_dict[nums]) == 0 or len(pairs_dict[nums]) == graph.neighbors(common_node):
                # print("Repeated entry in the queue, skipping")
                continue

            common_num = node_to_number_mapping[common_node]
            other_num = nums[0] if nums[1] == common_num else nums[1]

            if log:
                print("---Rule #3 ---")
                print(f"Domino {nums} has to involve a tile on position {get_coords(common_node, board)}, deleting all other outgoing connections from that tile")

            for nei in graph.neighbors(common_node):
                nei_num = node_to_number_mapping[nei]
                if nei_num != other_num:
                    connections_to_delete.append((common_node, nei))
                    if log:
                        print(f"Deleted connection between {get_coords(common_node, board)} {get_coords(nei, board)}")
            
            checked_all_groups = False

        elif q4:
            node = q4.popleft()
            
            if len(graph.neighbors(node)) < 2:
                # print("Repeated entry in the queue, skipping")
                continue
                
            neis = graph.neighbors(node)
            temp_graph = graph.copy()
            # temp_graph.delete_vertices(node)  # this shifts all the node names lol
            temp_graph.delete_edges(temp_graph.incident(node))
            print("---Rule #4---")
            print(f"Tile on a position {get_coords(node, board)} would create {len(neis)} subcomponents if it were to be deleted. Connection from it must go toward the subcomponent with odd number of tiles.")
            for nei in neis:
                size = len(temp_graph.subcomponent(nei))
                if log:
                    print(f"Component on the side of tile {get_coords(nei, board)} has size {size}")

                if size % 2 == 0:
                    connections_to_delete.append((node, nei))
                    if log:
                        print(f"Deleted connection between {get_coords(node, board)} {get_coords(nei, board)}")

            checked_all_groups = False

        elif not checked_all_groups:
            changed_something = False
            temp_to_delete = set()
            max_combs = 5   # for game_size 41 combinations of size 6 take too long already
            for i in range(game_size):
                sets = {}
                for node in number_to_nodes_mapping[i]:
                    if len(graph.neighbors(node)) == 0:
                        continue
                    unique_neis = set([node_to_number_mapping[nei] for nei in graph.neighbors(node)])
                    if i in unique_neis:
                        unique_neis.add(-1)
                    sets[node] = unique_neis
                
                for size in range(1, min(len(sets) - 1, max_combs)):
                    combs = combinations(sets, size)
                    for comb in combs:
                        merged_set = reduce(set.union, [sets[x] for x in comb])
                        if len(merged_set) == size:
                            for node, vals in sets.items():
                                if node in comb:
                                    continue
                                for nei in graph.neighbors(node):
                                    if node_to_number_mapping[nei] in merged_set:
                                        temp_to_delete.add(tuple(sorted([node, nei])))
                                        changed_something = True

                            if changed_something:
                                if log:
                                    print("---Rule #5---")
                                    print(f"Tiles with {i} on positions {[get_coords(pos, board) for pos in comb]} form a following group {merged_set}. Deleting unnecessary connections from other tiles with {i}")
                                    for n1, n2 in temp_to_delete:
                                        print(f"Deleted connection between {get_coords(n1, board)} {get_coords(n2, board)}")
                                connections_to_delete.extend(list(temp_to_delete))
                                break
                        if changed_something:
                            break
                    if changed_something:
                        break
                if changed_something:
                    break

            if not changed_something:
                checked_all_groups = True

        else:
            print("The loop shouldnt get to this point")
            break



        # DELETING AND MODIFYING SECTION
        for node1, node2, check_occurs in dominos_to_delete:
            edges = delete_domino(graph, node_to_number_mapping, number_to_nodes_mapping, node1, node2, pairs_dict, queues, check_occurs, log=True)
            if log:
                for tile1, tile2 in edges:
                    print(f"Additionally deleted connection between {get_coords(tile1, board)} and {get_coords(tile2, board)}")
        delete_connections(graph, connections_to_delete, node_to_number_mapping, pairs_dict, queues)


    return pairs


def solve(board, log=False):
    # this will just run all other logic so its easy to use from other scripts
    graph, node_to_number_mapping, number_to_nodes_mapping =  init_graph_from_board(board)
    pairs_dict, queues = init_dicts_and_queues(graph, node_to_number_mapping)
    pairs = solve_loop(board, graph, pairs_dict, queues, node_to_number_mapping, number_to_nodes_mapping, log=log)
    return pairs


def check_solution(board, pairs):
    pairs = set([tuple(sorted([get_coords(n1, board), get_coords(n2, board)])) for n1, n2 in pairs])
    found_pairs = defaultdict(int)
    used_tiles = defaultdict(int)
    for node1, node2 in pairs:
        y1, x1, y2, x2 = *node1, *node2
        pair = tuple(sorted([board[y1][x1], board[y2][x2]]))
        found_pairs[pair] += 1
        used_tiles[node1] += 1
        used_tiles[node2] += 1

    game_size = max([max(row)for row in board]) + 1
    for i in range(game_size):
        for j in range(i, game_size):
            if found_pairs[(i, j)] != 1:
                print(f"Test failed! Pair {(i, j)} was found {found_pairs[(i, j)]} times!")
                return False
    
    for key, val in used_tiles.items():
        if val != 1:
            print(f"Test failed! Tile {key} was used {val} times!")
            return False
    
    return True
    
