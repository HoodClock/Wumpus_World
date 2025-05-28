import pygame
import sys
import random
import math
from collections import deque
import heapq

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
GRID_SIZE = 500
CELL_SIZE = GRID_SIZE // 4
MARGIN = 50
INFO_WIDTH = SCREEN_WIDTH - GRID_SIZE - 3 * MARGIN
FONT = pygame.font.SysFont('Arial', 18)
TITLE_FONT = pygame.font.SysFont('Arial', 32, bold=True)

# Colors
BACKGROUND = (25, 30, 40)
GRID_BG = (35, 45, 55)
GRID_LINES = (70, 85, 100)
AGENT_COLOR = (0, 180, 240)
AGENT_EYE = (255, 255, 255)
WUMPUS_COLOR = (200, 50, 50)
PIT_COLOR = (40, 40, 50)
GOLD_COLOR = (255, 215, 0)
STENCH_COLOR = (180, 160, 50, 150)
BREEZE_COLOR = (170, 220, 255, 150)
SAFE_COLOR = (50, 180, 100, 100)
VISITED_COLOR = (80, 120, 180, 100)
DANGER_COLOR = (200, 60, 60, 150)
TEXT_COLOR = (220, 220, 220)
BUTTON_COLOR = (70, 100, 140)
BUTTON_HOVER = (90, 130, 180)
PANEL_BG = (40, 50, 65, 220)

class WumpusWorld:
    def __init__(self):
        self.size = 4
        self.grid = [[{'pit': False, 'wumpus': False, 'gold': False, 
                      'stench': False, 'breeze': False} 
                      for _ in range(self.size)] for _ in range(self.size)]
        
        # Agent state
        self.agent_pos = (0, 0)
        self.agent_dir = 'east'  # east, west, north, south
        self.has_arrow = True
        self.has_gold = False
        self.wumpus_alive = True
        self.game_over = False
        self.win = False
        self.visited = set([(0, 0)])
        self.safe_cells = set([(0, 0)])
        self.kb = {
            'stench': set(),
            'breeze': set(),
            'possible_wumpus': set(),
            'possible_pits': set()
        }
        
        # Initialize the world
        self.initialize_world()
        
        # Search algorithms
        self.search_algorithms = ['A*', 'BFS', 'DFS', 'IDS', 'Greedy']
        self.current_algorithm = 'A*'
        
        # Pathfinding
        self.path = []
        self.current_path_index = 0
        self.target = None
        self.searching = False
        
    def initialize_world(self):
        # Place Wumpus (avoid start position)
        wumpus_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
        while wumpus_pos == (0, 0):
            wumpus_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
        self.grid[wumpus_pos[0]][wumpus_pos[1]]['wumpus'] = True
        
        # Place Gold (avoid start and wumpus positions)
        gold_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
        while gold_pos == (0, 0) or gold_pos == wumpus_pos:
            gold_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
        self.grid[gold_pos[0]][gold_pos[1]]['gold'] = True
        
        # Place Pits (3 pits, avoid start and gold positions)
        num_pits = 3
        pit_positions = []
        for _ in range(num_pits):
            pit_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
            while pit_pos == (0, 0) or pit_pos == gold_pos or pit_pos == wumpus_pos or pit_pos in pit_positions:
                pit_pos = (random.randint(0, self.size-1), random.randint(0, self.size-1))
            self.grid[pit_pos[0]][pit_pos[1]]['pit'] = True
            pit_positions.append(pit_pos)
        
        # Calculate stenches and breezes
        for i in range(self.size):
            for j in range(self.size):
                if self.grid[i][j]['wumpus']:
                    for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                        ni, nj = i + dx, j + dy
                        if 0 <= ni < self.size and 0 <= nj < self.size:
                            self.grid[ni][nj]['stench'] = True
                
                if self.grid[i][j]['pit']:
                    for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                        ni, nj = i + dx, j + dy
                        if 0 <= ni < self.size and 0 <= nj < self.size:
                            self.grid[ni][nj]['breeze'] = True
    
    def get_current_percepts(self):
        x, y = self.agent_pos
        cell = self.grid[x][y]
        percepts = []
        
        if cell['stench']: percepts.append('Stench')
        if cell['breeze']: percepts.append('Breeze')
        if cell['gold']: percepts.append('Glitter')
        
        return percepts
    
    def update_kb(self):
        x, y = self.agent_pos
        percepts = self.get_current_percepts()
        
        # Update percept knowledge
        if 'Stench' in percepts: 
            self.kb['stench'].add((x, y))
        if 'Breeze' in percepts: 
            self.kb['breeze'].add((x, y))
        
        # Mark current position as safe
        self.safe_cells.add((x, y))
        self.visited.add((x, y))
        
        # Update possible dangers
        self.update_dangers()
    
    def update_dangers(self):
        # Reset possible dangers
        self.kb['possible_wumpus'] = set()
        self.kb['possible_pits'] = set()
        
        # For stench locations, adjacent cells are possible wumpus locations
        for sx, sy in self.kb['stench']:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = sx + dx, sy + dy
                if (0 <= nx < self.size and 0 <= ny < self.size and 
                    (nx, ny) not in self.safe_cells and 
                    (nx, ny) not in self.visited):
                    self.kb['possible_wumpus'].add((nx, ny))
        
        # For breeze locations, adjacent cells are possible pit locations
        for bx, by in self.kb['breeze']:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = bx + dx, by + dy
                if (0 <= nx < self.size and 0 <= ny < self.size and 
                    (nx, ny) not in self.safe_cells and 
                    (nx, ny) not in self.visited):
                    self.kb['possible_pits'].add((nx, ny))
    
    def get_adjacent(self, pos):
        x, y = pos
        adjacent = []
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                adjacent.append((nx, ny))
        return adjacent
    
    def move_forward(self):
        if self.game_over or not self.path:
            return False
            
        next_pos = self.path[self.current_path_index]
        x, y = self.agent_pos
        
        # Check if we can move to the next position
        if next_pos in self.get_adjacent((x, y)):
            self.agent_pos = next_pos
            self.current_path_index += 1
            
            # Check for dangers
            cell = self.grid[self.agent_pos[0]][self.agent_pos[1]]
            if cell['wumpus'] and self.wumpus_alive:
                self.game_over = True
                return True
            if cell['pit']:
                self.game_over = True
                return True
                
            # Update KB
            self.update_kb()
            
            # Check for gold
            if cell['gold']:
                self.has_gold = True
                cell['gold'] = False  # Collect gold
                
            # Check if we've reached the target
            if self.agent_pos == self.target:
                self.searching = False
                self.path = []
                self.current_path_index = 0
                
            return True
        return False
    
    def shoot_arrow(self):
        if not self.has_arrow or not self.wumpus_alive:
            return False
            
        self.has_arrow = False
        x, y = self.agent_pos
        dx, dy = 0, 0
        
        if self.agent_dir == 'east': dy = 1
        elif self.agent_dir == 'west': dy = -1
        elif self.agent_dir == 'north': dx = -1
        elif self.agent_dir == 'south': dx = 1
        
        # Check along the arrow path
        nx, ny = x, y
        while 0 <= nx < self.size and 0 <= ny < self.size:
            nx += dx
            ny += dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                if self.grid[nx][ny]['wumpus']:
                    self.wumpus_alive = False
                    # Remove the wumpus
                    self.grid[nx][ny]['wumpus'] = False
                    # Remove stenches
                    for i in range(self.size):
                        for j in range(self.size):
                            self.grid[i][j]['stench'] = False
                    return True
        return False
    
    def climb_out(self):
        if self.agent_pos == (0, 0) and self.has_gold:
            self.win = True
            self.game_over = True
            return True
        return False
    
    def find_path(self, target):
        start = self.agent_pos
        self.target = target
        self.searching = True
        
        if self.current_algorithm == 'A*':
            self.path = self.astar(start, target)
        elif self.current_algorithm == 'BFS':
            self.path = self.bfs(start, target)
        elif self.current_algorithm == 'DFS':
            self.path = self.dfs(start, target)
        elif self.current_algorithm == 'IDS':
            self.path = self.ids(start, target)
        elif self.current_algorithm == 'Greedy':
            self.path = self.greedy(start, target)
        
        self.current_path_index = 0
        return self.path is not None
    
    def bfs(self, start, goal):
        queue = deque([(start, [])])
        visited = set()
        
        while queue:
            pos, path = queue.popleft()
            if pos == goal:
                return path
            
            if pos in visited:
                continue
            visited.add(pos)
            
            for neighbor in self.get_adjacent(pos):
                if neighbor in visited:
                    continue
                if neighbor in self.safe_cells or neighbor == goal:
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def dfs(self, start, goal, path=None, visited=None):
        if path is None:
            path = [start]
        if visited is None:
            visited = set([start])
        
        if start == goal:
            return path[1:]  # Exclude start position
        
        for neighbor in self.get_adjacent(start):
            if neighbor not in visited and (neighbor in self.safe_cells or neighbor == goal):
                visited.add(neighbor)
                new_path = self.dfs(neighbor, goal, path + [neighbor], visited)
                if new_path:
                    return new_path
        
        return None
    
    def ids(self, start, goal, max_depth=10):
        for depth in range(1, max_depth + 1):
            result = self.dls(start, goal, depth)
            if result is not None:
                return result
        return None
    
    def dls(self, start, goal, depth, path=None, visited=None):
        if path is None:
            path = [start]
        if visited is None:
            visited = set([start])
        
        if start == goal:
            return path[1:]  # Exclude start position
        
        if depth <= 0:
            return None
        
        for neighbor in self.get_adjacent(start):
            if neighbor not in visited and (neighbor in self.safe_cells or neighbor == goal):
                visited.add(neighbor)
                new_path = self.dls(neighbor, goal, depth - 1, path + [neighbor], visited)
                if new_path:
                    return new_path
        
        return None
    
    def greedy(self, start, goal):
        def heuristic(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        
        heap = [(heuristic(start), start, [])]
        visited = set()
        
        while heap:
            h_val, pos, path = heapq.heappop(heap)
            if pos == goal:
                return path
            
            if pos in visited:
                continue
            visited.add(pos)
            
            for neighbor in self.get_adjacent(pos):
                if neighbor in visited:
                    continue
                if neighbor in self.safe_cells or neighbor == goal:
                    heapq.heappush(heap, (heuristic(neighbor), neighbor, path + [neighbor]))
        
        return None
    
    def astar(self, start, goal):
        def heuristic(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        
        heap = [(0 + heuristic(start), 0, start, [])]
        visited = set()
        
        while heap:
            f_val, g_val, pos, path = heapq.heappop(heap)
            if pos == goal:
                return path
            
            if pos in visited:
                continue
            visited.add(pos)
            
            for neighbor in self.get_adjacent(pos):
                if neighbor in visited:
                    continue
                if neighbor in self.safe_cells or neighbor == goal:
                    new_g = g_val + 1
                    new_f = new_g + heuristic(neighbor)
                    heapq.heappush(heap, (new_f, new_g, neighbor, path + [neighbor]))
        
        return None

class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
        
    def draw(self, surface):
        color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (120, 160, 200), self.rect, 2, border_radius=8)
        
        text_surf = FONT.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered and self.action:
                return self.action()
        return False

class WumpusVisualizer:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Wumpus World AI Agent")
        self.clock = pygame.time.Clock()
        self.world = WumpusWorld()
        
        # Create buttons
        button_width = 150
        button_height = 40
        button_x = GRID_SIZE + 2 * MARGIN
        button_y = 400
        button_spacing = 50
        
        self.buttons = [
            Button(button_x, button_y, button_width, button_height, "Move Forward", self.move_forward),
            Button(button_x, button_y + button_spacing, button_width, button_height, "Shoot Arrow", self.shoot_arrow),
            Button(button_x, button_y + 2*button_spacing, button_width, button_height, "Climb Out", self.climb_out),
            Button(button_x, button_y + 3*button_spacing, button_width, button_height, "New World", self.new_world)
        ]
        
        # Algorithm selection buttons
        algo_y = 200
        self.algo_buttons = []
        for i, algo in enumerate(self.world.search_algorithms):
            btn = Button(button_x + (i % 2) * (button_width + 20), 
                         algo_y + (i // 2) * (button_height + 10),
                         button_width, button_height, algo, 
                         lambda a=algo: self.set_algorithm(a))
            self.algo_buttons.append(btn)
        
        # Auto-explore button
        self.auto_button = Button(button_x, 300, button_width, button_height, "Auto Explore", self.auto_explore)
        
        # Game state
        self.message = "Welcome to Wumpus World!"
        self.auto_mode = False
        
    def set_algorithm(self, algo):
        self.world.current_algorithm = algo
        self.message = f"Search algorithm set to: {algo}"
        return True
        
    def move_forward(self):
        if self.world.game_over:
            self.message = "Game over! Start a new world."
            return False
            
        if not self.world.path and not self.auto_mode:
            # Find a safe unvisited cell
            unvisited_safe = [cell for cell in self.world.safe_cells 
                             if cell not in self.world.visited and cell != self.world.agent_pos]
            if unvisited_safe:
                target = unvisited_safe[0]
                if self.world.find_path(target):
                    self.message = f"Moving to ({target[0]}, {target[1]}) using {self.world.current_algorithm}"
                else:
                    self.message = "No path found to target!"
            else:
                self.message = "No safe unvisited cells!"
            return False
            
        if self.world.move_forward():
            self.message = f"Moved to ({self.world.agent_pos[0]}, {self.world.agent_pos[1]})"
            
            # Check for game over
            if self.world.game_over:
                if self.world.win:
                    self.message = "You won! Climbed out with gold."
                else:
                    if self.world.grid[self.world.agent_pos[0]][self.world.agent_pos[1]]['wumpus']:
                        self.message = "Game Over! Eaten by Wumpus."
                    else:
                        self.message = "Game Over! Fell into a pit."
            return True
        return False
        
    def shoot_arrow(self):
        if self.world.shoot_arrow():
            self.message = "Arrow shot! Wumpus killed!" if not self.world.wumpus_alive else "Arrow shot but missed!"
            return True
        self.message = "Cannot shoot arrow now!"
        return False
        
    def climb_out(self):
        if self.world.climb_out():
            self.message = "You climbed out with the gold! You win!"
            return True
        self.message = "Can only climb out at (0,0) with gold!"
        return False
        
    def new_world(self):
        self.world = WumpusWorld()
        self.message = "New world generated!"
        self.auto_mode = False
        return True
        
    def auto_explore(self):
        self.auto_mode = not self.auto_mode
        self.message = "Auto-explore started!" if self.auto_mode else "Auto-explore stopped"
        return True
        
    def draw_grid(self):
        # Draw grid background
        grid_rect = pygame.Rect(MARGIN, MARGIN, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(self.screen, GRID_BG, grid_rect)
        
        # Draw grid lines
        for i in range(5):
            # Vertical lines
            pygame.draw.line(self.screen, GRID_LINES, 
                            (MARGIN + i * CELL_SIZE, MARGIN),
                            (MARGIN + i * CELL_SIZE, MARGIN + GRID_SIZE), 2)
            # Horizontal lines
            pygame.draw.line(self.screen, GRID_LINES, 
                            (MARGIN, MARGIN + i * CELL_SIZE),
                            (MARGIN + GRID_SIZE, MARGIN + i * CELL_SIZE), 2)
        
        # Draw cell contents
        for i in range(4):
            for j in range(4):
                cell_rect = pygame.Rect(MARGIN + j * CELL_SIZE + 2, 
                                       MARGIN + i * CELL_SIZE + 2, 
                                       CELL_SIZE - 4, CELL_SIZE - 4)
                
                # Draw visited cells
                if (i, j) in self.world.visited:
                    s = pygame.Surface((CELL_SIZE - 4, CELL_SIZE - 4), pygame.SRCALPHA)
                    s.fill(VISITED_COLOR)
                    self.screen.blit(s, cell_rect.topleft)
                
                # Draw safe cells
                if (i, j) in self.world.safe_cells:
                    pygame.draw.rect(self.screen, SAFE_COLOR, cell_rect, 2)
                
                # Draw possible dangers
                if (i, j) in self.world.kb['possible_wumpus']:
                    s = pygame.Surface((CELL_SIZE - 4, CELL_SIZE - 4), pygame.SRCALPHA)
                    s.fill(DANGER_COLOR)
                    self.screen.blit(s, cell_rect.topleft)
                    danger_text = FONT.render("W?", True, (255, 200, 200))
                    self.screen.blit(danger_text, (cell_rect.centerx - 10, cell_rect.centery - 10))
                
                if (i, j) in self.world.kb['possible_pits']:
                    s = pygame.Surface((CELL_SIZE - 4, CELL_SIZE - 4), pygame.SRCALPHA)
                    s.fill(DANGER_COLOR)
                    self.screen.blit(s, cell_rect.topleft)
                    danger_text = FONT.render("P?", True, (255, 200, 200))
                    self.screen.blit(danger_text, (cell_rect.centerx - 10, cell_rect.centery - 10))
                
                # Draw pits
                if self.world.grid[i][j]['pit']:
                    pygame.draw.circle(self.screen, PIT_COLOR, cell_rect.center, CELL_SIZE // 3)
                    pit_text = FONT.render("Pit", True, (220, 220, 220))
                    self.screen.blit(pit_text, (cell_rect.centerx - 15, cell_rect.centery - 10))
                
                # Draw wumpus (if alive)
                if self.world.grid[i][j]['wumpus'] and self.world.wumpus_alive:
                    pygame.draw.circle(self.screen, WUMPUS_COLOR, cell_rect.center, CELL_SIZE // 3)
                    wumpus_text = FONT.render("Wumpus", True, (240, 240, 240))
                    self.screen.blit(wumpus_text, (cell_rect.centerx - 30, cell_rect.centery - 10))
                
                # Draw gold
                if self.world.grid[i][j]['gold']:
                    pygame.draw.circle(self.screen, GOLD_COLOR, cell_rect.center, CELL_SIZE // 4)
                    gold_text = FONT.render("Gold", True, (40, 30, 10))
                    self.screen.blit(gold_text, (cell_rect.centerx - 20, cell_rect.centery - 10))
                
                # Draw stench
                if self.world.grid[i][j]['stench']:
                    stench_rect = pygame.Rect(cell_rect.left + 10, cell_rect.top + 10, 20, 20)
                    pygame.draw.rect(self.screen, STENCH_COLOR, stench_rect)
                    stench_text = FONT.render("S", True, (120, 100, 30))
                    self.screen.blit(stench_text, (stench_rect.centerx - 5, stench_rect.centery - 10))
                
                # Draw breeze
                if self.world.grid[i][j]['breeze']:
                    breeze_rect = pygame.Rect(cell_rect.right - 30, cell_rect.top + 10, 20, 20)
                    pygame.draw.rect(self.screen, BREEZE_COLOR, breeze_rect)
                    breeze_text = FONT.render("B", True, (60, 100, 140))
                    self.screen.blit(breeze_text, (breeze_rect.centerx - 5, breeze_rect.centery - 10))
        
        # Draw agent
        agent_x = MARGIN + self.world.agent_pos[1] * CELL_SIZE + CELL_SIZE // 2
        agent_y = MARGIN + self.world.agent_pos[0] * CELL_SIZE + CELL_SIZE // 2
        pygame.draw.circle(self.screen, AGENT_COLOR, (agent_x, agent_y), CELL_SIZE // 4)
        
        # Draw agent direction indicator
        dir_x, dir_y = 0, 0
        if self.world.agent_dir == 'east': dir_x = 1
        elif self.world.agent_dir == 'west': dir_x = -1
        elif self.world.agent_dir == 'north': dir_y = -1
        elif self.world.agent_dir == 'south': dir_y = 1
        
        eye_x = agent_x + dir_x * (CELL_SIZE // 5)
        eye_y = agent_y + dir_y * (CELL_SIZE // 5)
        pygame.draw.circle(self.screen, AGENT_EYE, (eye_x, eye_y), CELL_SIZE // 10)
        
        # Draw path if exists
        if self.world.path:
            for idx, pos in enumerate(self.world.path):
                if idx >= self.world.current_path_index:
                    path_x = MARGIN + pos[1] * CELL_SIZE + CELL_SIZE // 2
                    path_y = MARGIN + pos[0] * CELL_SIZE + CELL_SIZE // 2
                    pygame.draw.circle(self.screen, (100, 200, 100, 150), (path_x, path_y), 5)
        
        # Draw grid coordinates
        for i in range(4):
            coord_text = FONT.render(str(i), True, TEXT_COLOR)
            # Row labels (left)
            self.screen.blit(coord_text, (MARGIN - 20, MARGIN + i * CELL_SIZE + CELL_SIZE // 2 - 10))
            # Column labels (top)
            self.screen.blit(coord_text, (MARGIN + i * CELL_SIZE + CELL_SIZE // 2 - 5, MARGIN - 30))
    
    def draw_info_panel(self):
        panel_rect = pygame.Rect(GRID_SIZE + 2 * MARGIN - 10, MARGIN - 10, 
                                INFO_WIDTH, SCREEN_HEIGHT - 2 * MARGIN)
        
        # Draw semi-transparent panel
        s = pygame.Surface((INFO_WIDTH, SCREEN_HEIGHT - 2 * MARGIN), pygame.SRCALPHA)
        s.fill(PANEL_BG)
        self.screen.blit(s, panel_rect.topleft)
        
        # Draw panel border
        pygame.draw.rect(self.screen, (90, 110, 140), panel_rect, 2, border_radius=10)
        
        # Draw title
        title = TITLE_FONT.render("Wumpus World AI", True, (0, 180, 240))
        self.screen.blit(title, (panel_rect.centerx - title.get_width() // 2, MARGIN))
        
        # Draw game state
        state_y = MARGIN + 60
        state_text = [
            f"Agent Position: ({self.world.agent_pos[0]}, {self.world.agent_pos[1]})",
            f"Direction: {self.world.agent_dir.capitalize()}",
            f"Has Gold: {'Yes' if self.world.has_gold else 'No'}",
            f"Has Arrow: {'Yes' if self.world.has_arrow else 'No'}",
            f"Wumpus Alive: {'Yes' if self.world.wumpus_alive else 'No'}",
            f"Visited Cells: {len(self.world.visited)}/16",
            f"Safe Cells: {len(self.world.safe_cells)}",
            "",
            f"Current Algorithm: {self.world.current_algorithm}",
            "",
            "Percepts: " + ", ".join(self.world.get_current_percepts()) if not self.world.game_over else "",
            "",
            f"Message: {self.message}"
        ]
        
        for text in state_text:
            text_surf = FONT.render(text, True, TEXT_COLOR)
            self.screen.blit(text_surf, (panel_rect.left + 20, state_y))
            state_y += 30
            
        # Draw algorithm selection label
        algo_label = FONT.render("Select Search Algorithm:", True, TEXT_COLOR)
        self.screen.blit(algo_label, (panel_rect.left + 20, 150))
    
    def draw(self):
        self.screen.fill(BACKGROUND)
        self.draw_grid()
        self.draw_info_panel()
        
        # Draw buttons
        for button in self.buttons:
            button.draw(self.screen)
        
        # Draw algorithm buttons
        for button in self.algo_buttons:
            button.draw(self.screen)
            # Highlight current algorithm
            if button.text == self.world.current_algorithm:
                pygame.draw.rect(self.screen, (0, 200, 100), button.rect, 3, border_radius=8)
        
        # Draw auto explore button
        self.auto_button.draw(self.screen)
        if self.auto_mode:
            pygame.draw.rect(self.screen, (0, 200, 100), self.auto_button.rect, 3, border_radius=8)
        
        # Draw game over message
        if self.world.game_over:
            game_over_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            game_over_surf.fill((0, 0, 0, 180))
            self.screen.blit(game_over_surf, (0, 0))
            
            if self.world.win:
                message = "Congratulations! You won!"
                color = (50, 200, 50)
            else:
                message = "Game Over! You lost."
                color = (200, 50, 50)
                
            text = TITLE_FONT.render(message, True, color)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 
                                   SCREEN_HEIGHT // 2 - text.get_height() // 2))
            
            restart = FONT.render("Click 'New World' to play again", True, (220, 220, 220))
            self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 
                                      SCREEN_HEIGHT // 2 + 50))
        
        pygame.display.flip()
    
    def run(self):
        running = True
        last_auto_move = pygame.time.get_ticks()
        
        while running:
            current_time = pygame.time.get_ticks()
            mouse_pos = pygame.mouse.get_pos()
            
            # Check button hovers
            for button in self.buttons + self.algo_buttons + [self.auto_button]:
                button.check_hover(mouse_pos)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Handle button events
                for button in self.buttons + self.algo_buttons + [self.auto_button]:
                    button.handle_event(event)
            
            # Auto-explore mode
            if self.auto_mode and not self.world.game_over:
                if current_time - last_auto_move > 1000:  # Move every second
                    if not self.world.path:
                        # Find a safe unvisited cell
                        unvisited_safe = [cell for cell in self.world.safe_cells 
                                         if cell not in self.world.visited and cell != self.world.agent_pos]
                        if unvisited_safe:
                            target = random.choice(unvisited_safe)
                            if self.world.find_path(target):
                                self.message = f"Auto: Moving to ({target[0]}, {target[1]})"
                            else:
                                self.message = "Auto: No path found!"
                        else:
                            # If no safe unvisited cells, try to climb out
                            if self.world.agent_pos == (0, 0) and self.world.has_gold:
                                self.climb_out()
                            else:
                                self.message = "Auto: No safe unvisited cells!"
                                self.auto_mode = False
                    
                    self.move_forward()
                    last_auto_move = current_time
            
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    visualizer = WumpusVisualizer()
    visualizer.run()