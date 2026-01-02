import pygame
import heapq
import sys
import math
import random
import string

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1400, 900
GRID_COLS, GRID_ROWS = 35, 28  # Slightly reduced to fit margins
CELL_SIZE = 28
UI_WIDTH = 360
GRID_OFFSET_X = 50  # Margin for Row Numbers
GRID_OFFSET_Y = 50  # Margin for Column Letters
FPS = 60

# --- CYBERPUNK PALETTE ---
C_BG = (5, 5, 10)
C_GRID_LINES = (30, 35, 45)
C_GRID_TEXT = (0, 150, 200)   # Cyan for coordinates
C_WALL = (45, 50, 55)
C_WIND_ZONE = (200, 160, 0)
C_SCAN_WAVE = (0, 255, 128)
C_PATH_GLOW = (0, 210, 255)
C_PATH_CORE = (220, 250, 255)
C_DRONE = (0, 255, 255)
C_FIRE = (255, 60, 60)
C_UI_BG = (12, 14, 18)
C_UI_BORDER = (0, 90, 90)
C_TEXT_MAIN = (210, 230, 240)
C_TEXT_DIM = (100, 120, 130)
C_BUTTON_HOVER = (0, 70, 70)
C_LOG_TEXT = (0, 255, 150)    # Matrix green for logs

# Costs
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
        color = C_PATH_GLOW if active else (C_BUTTON_HOVER if self.hovered else self.base_color)
        
        # Glassy Background
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        s.fill((*color[:3], 40 if not active else 80))
        screen.blit(s, (self.rect.x, self.rect.y))
        
        pygame.draw.rect(screen, color, self.rect, 2 if active else 1, border_radius=4)
        
        txt_surf = font.render(self.text, True, C_TEXT_MAIN if active else C_TEXT_DIM)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def check_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

class FlytBaseDashboard:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FLYTBASE // STRATEGIC COMMAND v5.0")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_head = pygame.font.SysFont("impact", 32)
        self.font_ui = pygame.font.SysFont("consolas", 14)
        self.font_mono = pygame.font.SysFont("consolas", 12)
        self.font_tiny = pygame.font.SysFont("consolas", 10) # For coordinates
        self.font_btn = pygame.font.SysFont("arial", 13, bold=True)

        self.buttons = []
        self._init_buttons()
        self.log_history = ["SYSTEM INITIALIZED...", "AWAITING OPERATOR INPUT..."]
        
        self.reset_system()
        self.radar_angle = 0 # For the sweeping line
        
        # Pre-render visual assets
        self.scanline_surf = self._create_scanlines()
        
        # Generate Coordinate Labels (A, B, C...)
        self.col_labels = [self._get_col_label(i) for i in range(GRID_COLS)]

    def _get_col_label(self, idx):
        # A, B... Z, AA, AB...
        if idx < 26: return string.ascii_uppercase[idx]
        return string.ascii_uppercase[idx // 26 - 1] + string.ascii_uppercase[idx % 26]

    def _init_buttons(self):
        bx = WIDTH - UI_WIDTH + 25
        bw = UI_WIDTH - 50
        by = 160
        gap = 42
        
        self.buttons.append(Button(bx, by, bw, 35, "[1] DEPLOY OBSTACLES", 'wall'))
        self.buttons.append(Button(bx, by+gap, bw, 35, "[2] MAP WIND ZONES", 'wind'))
        self.buttons.append(Button(bx, by+gap*2, bw, 35, "[3] RELOCATE DRONE", 'drone'))
        self.buttons.append(Button(bx, by+gap*3, bw, 35, "[4] RELOCATE TARGET", 'fire'))
        
        self.buttons.append(Button(bx, by+gap*5, bw, 45, "[SPACE] EXECUTE FLIGHT PLAN", 'run', C_PATH_GLOW))
        self.buttons.append(Button(bx, by+gap*6.3, bw, 35, "[R] RESET GRID", 'reset', C_FIRE))

    def _create_scanlines(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(s, (0, 0, 0, 40), (0, y), (WIDTH, y))
        return s

    def log(self, msg):
        self.log_history.append(f"> {msg}")
        if len(self.log_history) > 14: # Keep last 14 lines
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
        self.telemetry = {"BAT": 98.0, "SIG": 100.0, "WIND": 12.0}
        self.log("GRID RESET COMPLETE.")

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            
            # Keyboard
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: self.execute_command('wall')
                elif event.key == pygame.K_2: self.execute_command('wind')
                elif event.key == pygame.K_3: self.execute_command('drone')
                elif event.key == pygame.K_4: self.execute_command('fire')
                elif event.key == pygame.K_SPACE: self.execute_command('run')
                elif event.key == pygame.K_r: self.execute_command('reset')

            # Mouse Click (UI)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if mx > WIDTH - UI_WIDTH:
                    for btn in self.buttons:
                        if btn.hovered: self.execute_command(btn.action_code)

        # Mouse Drag (Grid)
        mx, my = pygame.mouse.get_pos()
        if mx < WIDTH - UI_WIDTH:
            # Adjust mouse pos for grid offset
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
            self.log(f"TOOL SELECTED: {code.upper()}")

    def use_tool(self, gx, gy, erase=False):
        if self.algo_running: return
        
        # Convert pixel to grid index
        if gx < 0 or gy < 0: return # Ignore clicks in margins
        
        c, r = gx // CELL_SIZE, gy // CELL_SIZE
        if not (0 <= r < GRID_ROWS and 0 <= c < GRID_COLS): return
        
        if (r, c) in [self.start, self.end] and self.tool not in ['drone', 'fire']: return

        # Log change only on initial click (to avoid spamming log while dragging)
        # simplified for this demo to avoid complex state tracking
        
        if erase:
            self.grid[r][c] = 0
        else:
            if self.tool == 'wall': self.grid[r][c] = 1
            elif self.tool == 'wind': self.grid[r][c] = 2
            elif self.tool == 'drone': 
                self.grid[r][c] = 0; self.start = (r, c)
                self.log(f"DRONE RELOCATED TO [{self.col_labels[c]}-{r:02d}]")
            elif self.tool == 'fire': 
                self.grid[r][c] = 0; self.end = (r, c)
                self.log(f"TARGET RELOCATED TO [{self.col_labels[c]}-{r:02d}]")

    def run_dijkstra(self):
        self.algo_running = True
        self.path = []
        self.visited_cells = []
        self.scan_index = 0
        self.log("CALCULATING OPTIMAL PATH...")
        
        pq = [(0, self.start)]
        visited_costs = {}
        parent_map = {}
        
        while pq:
            cost, curr = heapq.heappop(pq)
            if curr in visited_costs and visited_costs[curr] <= cost: continue
            visited_costs[curr] = cost
            self.visited_cells.append(curr)
            
            if curr == self.end:
                self.reconstruct_path(parent_map)
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
        
        self.log("ERROR: NO VIABLE PATH FOUND.")
        self.algo_running = False

    def reconstruct_path(self, parent_map):
        curr = self.end
        while curr in parent_map:
            self.path.append(curr)
            curr = parent_map[curr]
            if curr == self.start: break
        self.path.append(self.start)
        self.path.reverse()
        self.log(f"PATH LOCKED. DISTANCE: {len(self.path)} NODES")

    def update(self):
        # Update Radar Line
        self.radar_angle = (self.radar_angle + 2) % 360
        
        # Telemetry Jitter
        if pygame.time.get_ticks() % 15 == 0:
            self.telemetry["BAT"] = max(10, min(100, self.telemetry["BAT"] + random.uniform(-0.1, 0.1)))
            self.telemetry["SIG"] = max(80, min(100, self.telemetry["SIG"] + random.uniform(-1.5, 1.5)))
            self.telemetry["WIND"] = max(0, min(40, self.telemetry["WIND"] + random.uniform(-0.5, 0.5)))

        if self.algo_running:
            if self.scan_index < len(self.visited_cells):
                self.scan_index += 40
            else:
                if self.path and "DEPLOYING" not in self.log_history[-1]:
                     self.log("DATA UPLOADED. DRONE DEPLOYING.")

    def draw(self):
        self.screen.fill(C_BG)
        
        # --- DRAW RULERS (Coordinates) ---
        # Draw Column Letters (Top)
        for c in range(GRID_COLS):
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE//2
            lbl = self.font_tiny.render(self.col_labels[c], True, C_GRID_TEXT)
            self.screen.blit(lbl, (cx - 4, GRID_OFFSET_Y - 20))
        
        # Draw Row Numbers (Left)
        for r in range(GRID_ROWS):
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE//2
            lbl = self.font_tiny.render(f"{r:02d}", True, C_GRID_TEXT)
            self.screen.blit(lbl, (GRID_OFFSET_X - 25, cy - 6))

        # --- GRID OFFSET CONTEXT ---
        # Everything below draws relative to GRID_OFFSET_X/Y
        
        # 1. Grid Lines & Cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                
                # Faint Grid Box
                pygame.draw.rect(self.screen, C_GRID_LINES, (x, y, CELL_SIZE, CELL_SIZE), 1)
                
                val = self.grid[r][c]
                if val == 1: # Wall
                    pygame.draw.rect(self.screen, C_WALL, (x+1, y+1, CELL_SIZE-2, CELL_SIZE-2), border_radius=2)
                elif val == 2: # Wind
                    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s.fill((*C_WIND_ZONE, 80))
                    self.screen.blit(s, (x, y))

        # 2. Scanning Visuals
        limit = min(self.scan_index, len(self.visited_cells))
        for i in range(limit):
            r, c = self.visited_cells[i]
            if (r,c) != self.start and (r,c) != self.end:
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                alpha = max(0, 160 - (self.scan_index - i)*3)
                if alpha > 0:
                    s.fill((*C_SCAN_WAVE, alpha))
                    self.screen.blit(s, (x, y))

        # 3. Path
        if self.scan_index >= len(self.visited_cells) and len(self.path) > 1:
            points = [(GRID_OFFSET_X + c*CELL_SIZE + CELL_SIZE//2, 
                       GRID_OFFSET_Y + r*CELL_SIZE + CELL_SIZE//2) for r,c in self.path]
            if len(points) > 1:
                pygame.draw.lines(self.screen, (*C_PATH_GLOW, 80), False, points, 10)
                pygame.draw.lines(self.screen, C_PATH_CORE, False, points, 2)

        # 4. Radar Sweep (Visual Only)
        rx = GRID_OFFSET_X + (GRID_COLS * CELL_SIZE) // 2
        ry = GRID_OFFSET_Y + (GRID_ROWS * CELL_SIZE) // 2
        sweep_len = max(WIDTH, HEIGHT)
        dx = rx + math.cos(math.radians(self.radar_angle)) * sweep_len
        dy = ry + math.sin(math.radians(self.radar_angle)) * sweep_len
        pygame.draw.line(self.screen, (0, 50, 0), (rx, ry), (dx, dy), 1)

        # 5. Entities
        sr, sc = self.start
        sx, sy = GRID_OFFSET_X + sc*CELL_SIZE, GRID_OFFSET_Y + sr*CELL_SIZE
        pygame.draw.rect(self.screen, C_DRONE, (sx+4, sy+4, CELL_SIZE-8, CELL_SIZE-8), border_radius=4)
        
        er, ec = self.end
        ex, ey = GRID_OFFSET_X + ec*CELL_SIZE, GRID_OFFSET_Y + er*CELL_SIZE
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2
        rad = (CELL_SIZE//2 - 3) + (pulse * 3)
        pygame.draw.circle(self.screen, C_FIRE, (ex+CELL_SIZE//2, ey+CELL_SIZE//2), int(rad))

        # --- SIDEBAR UI ---
        ui_x = WIDTH - UI_WIDTH
        pygame.draw.rect(self.screen, C_UI_BG, (ui_x, 0, UI_WIDTH, HEIGHT))
        pygame.draw.line(self.screen, C_UI_BORDER, (ui_x, 0), (ui_x, HEIGHT), 2)

        # Header
        head_txt = self.font_head.render("FLYTBASE OPS", True, C_DRONE)
        self.screen.blit(head_txt, (ui_x + 25, 30))
        sub_txt = self.font_mono.render("TACTICAL DRONE COMMAND", True, C_TEXT_DIM)
        self.screen.blit(sub_txt, (ui_x + 27, 70))

        # Buttons
        for btn in self.buttons:
            is_active = (btn.action_code == self.tool)
            btn.draw(self.screen, self.font_btn, active=is_active)

        # Mission Log (Scrolling Text)
        log_y = HEIGHT - 240
        pygame.draw.rect(self.screen, (8, 8, 12), (ui_x + 20, log_y, UI_WIDTH - 40, 220)) # Log BG
        pygame.draw.rect(self.screen, C_UI_BORDER, (ui_x + 20, log_y, UI_WIDTH - 40, 220), 1)
        
        log_title = self.font_tiny.render("MISSION LOG", True, C_TEXT_DIM)
        self.screen.blit(log_title, (ui_x + 25, log_y - 15))

        for i, msg in enumerate(self.log_history):
            # Fade older messages
            alpha = 255 if i == len(self.log_history)-1 else 150
            txt = self.font_mono.render(msg, True, (*C_LOG_TEXT, alpha))
            self.screen.blit(txt, (ui_x + 30, log_y + 10 + i * 14))

        # Telemetry
        ty = HEIGHT - 380
        self._draw_telemetry_row("BATTERY", f"{self.telemetry['BAT']:.1f}%", C_SCAN_WAVE, ty, ui_x)
        self._draw_telemetry_row("SIGNAL", f"{self.telemetry['SIG']:.1f} dB", C_PATH_GLOW, ty + 30, ui_x)
        self._draw_telemetry_row("WIND", f"{self.telemetry['WIND']:.1f} km/h", C_WIND_ZONE, ty + 60, ui_x)

        # Scanlines
        self.screen.blit(self.scanline_surf, (0, 0))
        pygame.display.flip()

    def _draw_telemetry_row(self, label, value, color, y, offset_x):
        x = offset_x + 30
        lbl = self.font_mono.render(label, True, C_TEXT_DIM)
        val = self.font_ui.render(value, True, color)
        self.screen.blit(lbl, (x, y))
        self.screen.blit(val, (x + 160, y))

if __name__ == "__main__":
    app = FlytBaseDashboard()
    app.run()