import pygame
import heapq
import sys
import math
import random
import string
import time
import datetime

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1400, 900
GRID_COLS, GRID_ROWS = 35, 28
CELL_SIZE = 28
UI_WIDTH = 380
GRID_OFFSET_X = 50
GRID_OFFSET_Y = 50
FPS = 60

# --- THEME: SPECIAL OPS ---
C_BG = (5, 6, 8)
C_GRID_LINES = (25, 30, 40)
C_GRID_TEXT = (0, 180, 220)
C_WALL = (40, 45, 50)
C_WIND_ZONE = (220, 160, 0)
C_SCAN_WAVE = (0, 255, 140)
C_PATH_GLOW = (0, 200, 255)
C_PATH_CORE = (230, 250, 255)
C_DRONE = (0, 255, 255)
C_FIRE = (255, 50, 50)
C_UI_BG = (10, 12, 15)
C_UI_BORDER = (0, 100, 100)
C_TEXT_MAIN = (220, 230, 240)
C_TEXT_DIM = (100, 110, 120)

# Log Colors
C_LOG_INFO = (0, 255, 150)    # Green
C_LOG_WARN = (255, 180, 0)    # Orange
C_LOG_ERR = (255, 50, 50)     # Red

COST_CLEAR = 1
COST_WIND = 5

class Button:
    def __init__(self, x, y, w, h, text, action_code, color=C_UI_BORDER):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action_code = action_code
        self.base_color = color
        self.hovered = False

    def draw(self, screen, font, active=False):
        color = C_PATH_GLOW if active else (C_UI_BORDER if self.hovered else self.base_color)
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        s.fill((*color[:3], 50 if active else 30))
        screen.blit(s, (self.rect.x, self.rect.y))
        pygame.draw.rect(screen, color, self.rect, 2 if active else 1, border_radius=3)
        
        txt_surf = font.render(self.text, True, C_TEXT_MAIN if active else C_TEXT_DIM)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def check_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

class FlytBaseDashboard:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FLYTBASE // ADVANCED TACTICAL LINK v6.0")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_head = pygame.font.SysFont("impact", 30)
        self.font_ui = pygame.font.SysFont("consolas", 14)
        self.font_mono = pygame.font.SysFont("consolas", 11) # Smaller for logs
        self.font_tiny = pygame.font.SysFont("consolas", 10)
        self.font_btn = pygame.font.SysFont("arial", 12, bold=True)

        self.buttons = []
        self._init_buttons()
        
        # Enhanced Logging System: stores (text, color) tuples
        self.log_history = [] 
        
        self.reset_system()
        self.radar_angle = 0
        self.scanline_surf = self._create_scanlines()
        self.col_labels = [self._get_col_label(i) for i in range(GRID_COLS)]
        
        # Boot sequence logs
        self.log("KERNEL INIT...", C_TEXT_DIM)
        self.log("GRID COORDINATES LOCKED.", C_LOG_INFO)
        self.log("WAITING FOR MISSION PARAMETERS...", C_TEXT_MAIN)

    def _get_col_label(self, idx):
        if idx < 26: return string.ascii_uppercase[idx]
        return string.ascii_uppercase[idx // 26 - 1] + string.ascii_uppercase[idx % 26]

    def _init_buttons(self):
        bx = WIDTH - UI_WIDTH + 25
        bw = UI_WIDTH - 50
        by = 150
        gap = 40
        
        self.buttons.append(Button(bx, by, bw, 32, "[1] DEPLOY OBSTACLES", 'wall'))
        self.buttons.append(Button(bx, by+gap, bw, 32, "[2] MAP WIND ZONES", 'wind'))
        self.buttons.append(Button(bx, by+gap*2, bw, 32, "[3] RELOCATE DRONE", 'drone'))
        self.buttons.append(Button(bx, by+gap*3, bw, 32, "[4] RELOCATE TARGET", 'fire'))
        
        self.buttons.append(Button(bx, by+gap*5, bw, 45, "[SPACE] EXECUTE SOLVER", 'run', C_PATH_GLOW))
        self.buttons.append(Button(bx, by+gap*6.4, bw, 32, "[R] RESET GRID", 'reset', C_FIRE))

    def _create_scanlines(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(s, (0, 0, 0, 40), (0, y), (WIDTH, y))
        return s

    def log(self, msg, color=C_LOG_INFO):
        # Add Timestamp [HH:MM:SS]
        ts = datetime.datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{ts} {msg}"
        self.log_history.append((full_msg, color))
        if len(self.log_history) > 16: # Max lines
            self.log_history.pop(0)

    def reset_system(self):
        self.grid = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.start = (4, 4)
        self.end = (20, 25)
        self.tool = 'wall'
        self.algo_running = False
        self.path = []
        self.visited_cells = []
        self.scan_index = 0
        self.telemetry = {"BAT": 98.0, "SIG": 100.0, "CPU": 12}
        self.log("SYSTEM RESET CONFIRMED.", C_LOG_WARN)

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: self.execute_command('wall')
                elif event.key == pygame.K_2: self.execute_command('wind')
                elif event.key == pygame.K_3: self.execute_command('drone')
                elif event.key == pygame.K_4: self.execute_command('fire')
                elif event.key == pygame.K_SPACE: self.execute_command('run')
                elif event.key == pygame.K_r: self.execute_command('reset')

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if mx > WIDTH - UI_WIDTH:
                    for btn in self.buttons:
                        if btn.hovered: self.execute_command(btn.action_code)

        # Mouse Drag (Grid)
        mx, my = pygame.mouse.get_pos()
        if mx < WIDTH - UI_WIDTH:
            gx, gy = mx - GRID_OFFSET_X, my - GRID_OFFSET_Y
            buttons = pygame.mouse.get_pressed()
            if buttons[0]: self.use_tool(gx, gy, erase=False)
            elif buttons[2]: self.use_tool(gx, gy, erase=True)
        else:
            for btn in self.buttons: btn.check_hover(mx, my)

    def execute_command(self, code):
        if code == 'run': self.run_dijkstra()
        elif code == 'reset': self.reset_system()
        else: 
            self.tool = code

    def use_tool(self, gx, gy, erase=False):
        if self.algo_running: return
        if gx < 0 or gy < 0: return 
        
        c, r = gx // CELL_SIZE, gy // CELL_SIZE
        if not (0 <= r < GRID_ROWS and 0 <= c < GRID_COLS): return
        if (r, c) in [self.start, self.end] and self.tool not in ['drone', 'fire']: return

        if erase: self.grid[r][c] = 0
        else:
            if self.tool == 'wall': self.grid[r][c] = 1
            elif self.tool == 'wind': self.grid[r][c] = 2
            elif self.tool == 'drone': 
                self.grid[r][c] = 0; self.start = (r, c)
            elif self.tool == 'fire': 
                self.grid[r][c] = 0; self.end = (r, c)

    def run_dijkstra(self):
        self.algo_running = True
        self.path = []
        self.visited_cells = []
        self.scan_index = 0
        
        # TECHNICAL LOGGING
        self.log("INITIATING PATHFINDING ALGORITHM...", C_TEXT_MAIN)
        start_time = time.time()
        
        pq = [(0, self.start)]
        visited_costs = {}
        parent_map = {}
        nodes_expanded = 0
        
        while pq:
            cost, curr = heapq.heappop(pq)
            if curr in visited_costs and visited_costs[curr] <= cost: continue
            
            visited_costs[curr] = cost
            self.visited_cells.append(curr)
            nodes_expanded += 1
            
            if curr == self.end:
                execution_time = (time.time() - start_time) * 1000 # in ms
                self.reconstruct_path(parent_map, execution_time, cost, nodes_expanded)
                return

            r, c = curr
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS and self.grid[nr][nc] != 1:
                    weight = COST_WIND if self.grid[nr][nc] == 2 else COST_CLEAR
                    new_cost = cost + weight
                    if (nr, nc) not in visited_costs or new_cost < visited_costs[(nr, nc)]:
                        heapq.heappush(pq, (new_cost, (nr, nc)))
                        parent_map[(nr, nc)] = curr
        
        self.log("FATAL ERROR: TARGET UNREACHABLE.", C_LOG_ERR)
        self.algo_running = False

    def reconstruct_path(self, parent_map, exec_time, total_cost, expansions):
        curr = self.end
        while curr in parent_map:
            self.path.append(curr)
            curr = parent_map[curr]
            if curr == self.start: break
        self.path.append(self.start)
        self.path.reverse()
        
        # TECHNICAL SUCCESS LOGS
        self.log(f"PATH OPTIMIZED IN {exec_time:.2f}ms", C_LOG_INFO)
        self.log(f"NODES EXPANDED: {expansions} | COST: {total_cost}", C_TEXT_MAIN)
        self.log(f"VECTOR LOCKED: {len(self.path)} SEGMENTS", C_LOG_WARN)

    def update(self):
        self.radar_angle = (self.radar_angle + 1.5) % 360
        
        # Telemetry Jitter
        if pygame.time.get_ticks() % 20 == 0:
            self.telemetry["BAT"] = max(10, min(100, self.telemetry["BAT"] + random.uniform(-0.05, 0.05)))
            self.telemetry["SIG"] = max(80, min(100, self.telemetry["SIG"] + random.uniform(-1, 1)))
            self.telemetry["CPU"] = random.randint(10, 40)

        if self.algo_running:
            if self.scan_index < len(self.visited_cells):
                self.scan_index += 45
            else:
                if self.path and "UPLOADING" not in str(self.log_history[-1]):
                    self.log("UPLOADING FLIGHT PLAN TO DRONE...", C_TEXT_DIM)

    def draw(self):
        self.screen.fill(C_BG)
        
        # --- RULERS ---
        for c in range(GRID_COLS):
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE//2
            lbl = self.font_tiny.render(self.col_labels[c], True, C_GRID_TEXT)
            self.screen.blit(lbl, (cx - 3, GRID_OFFSET_Y - 18))
        
        for r in range(GRID_ROWS):
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE//2
            lbl = self.font_tiny.render(f"{r:02d}", True, C_GRID_TEXT)
            self.screen.blit(lbl, (GRID_OFFSET_X - 22, cy - 5))

        # --- GRID & CELLS ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                
                pygame.draw.rect(self.screen, C_GRID_LINES, (x, y, CELL_SIZE, CELL_SIZE), 1)
                
                val = self.grid[r][c]
                if val == 1: 
                    pygame.draw.rect(self.screen, C_WALL, (x+1, y+1, CELL_SIZE-2, CELL_SIZE-2), border_radius=2)
                elif val == 2:
                    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s.fill((*C_WIND_ZONE, 80))
                    self.screen.blit(s, (x, y))

        # --- SCANNER ---
        limit = min(self.scan_index, len(self.visited_cells))
        for i in range(limit):
            r, c = self.visited_cells[i]
            if (r,c) != self.start and (r,c) != self.end:
                x, y = GRID_OFFSET_X + c * CELL_SIZE, GRID_OFFSET_Y + r * CELL_SIZE
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                alpha = max(0, 160 - (self.scan_index - i)*3)
                if alpha > 0:
                    s.fill((*C_SCAN_WAVE, alpha))
                    self.screen.blit(s, (x, y))

        # --- FLASHING PATH ---
        if self.scan_index >= len(self.visited_cells) and len(self.path) > 1:
            points = [(GRID_OFFSET_X + c*CELL_SIZE + CELL_SIZE//2, 
                    GRID_OFFSET_Y + r*CELL_SIZE + CELL_SIZE//2) for r,c in self.path]
            
            # Pulse Logic: Uses Sine wave based on time
            pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2 # 0.0 to 1.0
            
            # Inner Core (White/Bright) - Stable
            pygame.draw.lines(self.screen, C_PATH_CORE, False, points, 2)
            
            # Middle Glow (Cyan) - Pulses Width
            width_pulse = 4 + (pulse * 6) # Oscillates between 4px and 10px
            pygame.draw.lines(self.screen, (*C_PATH_GLOW, 150), False, points, int(width_pulse))
            
            # Outer Haze (Transparent) - Pulses Alpha
            s_path = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha_pulse = 50 + (pulse * 100) # Oscillates alpha
            if len(points) > 1:
                pygame.draw.lines(s_path, (*C_PATH_GLOW, int(alpha_pulse)), False, points, 15)
            self.screen.blit(s_path, (0,0))

        # --- RADAR & ENTITIES ---
        rx, ry = GRID_OFFSET_X + (GRID_COLS*CELL_SIZE)//2, GRID_OFFSET_Y + (GRID_ROWS*CELL_SIZE)//2
        dx = rx + math.cos(math.radians(self.radar_angle)) * 1000
        dy = ry + math.sin(math.radians(self.radar_angle)) * 1000
        pygame.draw.line(self.screen, (0, 60, 30), (rx, ry), (dx, dy), 1)

        # Start/End
        sr, sc = self.start
        sx, sy = GRID_OFFSET_X + sc*CELL_SIZE, GRID_OFFSET_Y + sr*CELL_SIZE
        pygame.draw.rect(self.screen, C_DRONE, (sx+4, sy+4, CELL_SIZE-8, CELL_SIZE-8), border_radius=4)
        
        er, ec = self.end
        ex, ey = GRID_OFFSET_X + ec*CELL_SIZE, GRID_OFFSET_Y + er*CELL_SIZE
        pygame.draw.circle(self.screen, C_FIRE, (ex+CELL_SIZE//2, ey+CELL_SIZE//2), CELL_SIZE//2 - 2)

        # --- UI PANEL ---
        ui_x = WIDTH - UI_WIDTH
        pygame.draw.rect(self.screen, C_UI_BG, (ui_x, 0, UI_WIDTH, HEIGHT))
        pygame.draw.line(self.screen, C_UI_BORDER, (ui_x, 0), (ui_x, HEIGHT), 2)

        # Header
        head_txt = self.font_head.render("FLYTBASE OPS", True, C_DRONE)
        self.screen.blit(head_txt, (ui_x + 25, 30))
        sub_txt = self.font_mono.render("AUTONOMOUS RESPONSE SQUADRON", True, C_TEXT_DIM)
        self.screen.blit(sub_txt, (ui_x + 27, 70))

        # Buttons
        for btn in self.buttons:
            is_active = (btn.action_code == self.tool)
            btn.draw(self.screen, self.font_btn, active=is_active)

        # --- ENHANCED MISSION LOG ---
        log_y = HEIGHT - 280
        # Background for logs
        pygame.draw.rect(self.screen, (5, 8, 10), (ui_x + 20, log_y, UI_WIDTH - 40, 260))
        pygame.draw.rect(self.screen, C_UI_BORDER, (ui_x + 20, log_y, UI_WIDTH - 40, 260), 1)
        
        log_title = self.font_tiny.render("MISSION TELEMETRY LOG", True, C_TEXT_DIM)
        self.screen.blit(log_title, (ui_x + 25, log_y - 15))

        # Render Log History
        for i, (msg, color) in enumerate(self.log_history):
            # Calculate opacity (fade old logs)
            alpha = 255 if i > len(self.log_history) - 4 else 120
            
            txt = self.font_mono.render(msg, True, color)
            txt.set_alpha(alpha)
            self.screen.blit(txt, (ui_x + 30, log_y + 10 + i * 15))

        # --- TELEMETRY GRAPHS ---
        ty = HEIGHT - 420
        self._draw_telemetry_bar("BATTERY", self.telemetry['BAT'], C_SCAN_WAVE, ty, ui_x)
        self._draw_telemetry_bar("SIGNAL", self.telemetry['SIG'], C_PATH_GLOW, ty + 35, ui_x)
        self._draw_telemetry_bar("CPU LOAD", self.telemetry['CPU'], C_WIND_ZONE, ty + 70, ui_x)

        self.screen.blit(self.scanline_surf, (0, 0))
        pygame.display.flip()

    def _draw_telemetry_bar(self, label, value, color, y, offset_x):
        x = offset_x + 30
        # Label
        lbl = self.font_mono.render(f"{label}", True, C_TEXT_DIM)
        val_txt = self.font_btn.render(f"{int(value)}%", True, color)
        self.screen.blit(lbl, (x, y))
        self.screen.blit(val_txt, (x + 280, y))
        
        # Bar Background
        pygame.draw.rect(self.screen, (20, 30, 40), (x, y+15, 310, 6))
        # Active Bar
        bar_w = int((value / 100) * 310)
        pygame.draw.rect(self.screen, color, (x, y+15, bar_w, 6))

if __name__ == "__main__":
    app = FlytBaseDashboard()
    app.run()