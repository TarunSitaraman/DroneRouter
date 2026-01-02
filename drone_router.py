import pygame
import heapq
import sys
import math
import random

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1400, 900  # Widescreen for dashboard
GRID_COLS, GRID_ROWS = 40, 30
CELL_SIZE = 28
UI_WIDTH = 350  # Width of the sidebar
FPS = 60

# --- CYBERPUNK PALETTE ---
C_BG = (4, 4, 8)              # Deep Space
C_GRID = (25, 25, 35)         # Faint Grid
C_WALL = (40, 44, 50)         # Architecture Grey
C_WIND_ZONE = (180, 140, 0)   # Gold/Amber
C_SCAN_WAVE = (0, 255, 128)   # Data Green
C_PATH_GLOW = (0, 190, 255)   # Electric Blue
C_PATH_CORE = (200, 240, 255) # White Hot
C_DRONE = (0, 255, 255)       # Cyan
C_FIRE = (255, 40, 40)        # Alert Red
C_UI_BG = (10, 12, 16)        # Dark Panel
C_UI_BORDER = (0, 80, 80)     # Teal Border
C_TEXT_MAIN = (200, 220, 230)
C_TEXT_DIM = (100, 110, 120)
C_BUTTON_HOVER = (0, 60, 60)

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
        # Dynamic color logic
        color = C_PATH_GLOW if active else (C_BUTTON_HOVER if self.hovered else self.base_color)
        border_width = 2 if active or self.hovered else 1
        
        # Draw background with low opacity
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        s.fill((*color[:3], 30 if not active else 60))
        screen.blit(s, (self.rect.x, self.rect.y))
        
        # Draw Border
        pygame.draw.rect(screen, color, self.rect, border_width, border_radius=4)
        
        # Draw Text
        txt_surf = font.render(self.text, True, C_TEXT_MAIN if active else C_TEXT_DIM)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def check_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

class FlytBaseDashboard:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FLYTBASE // AI COMMAND LINK v4.0")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_header = pygame.font.SysFont("impact", 32)
        self.font_ui = pygame.font.SysFont("consolas", 14)
        self.font_mono = pygame.font.SysFont("consolas", 12)
        self.font_btn = pygame.font.SysFont("arial", 14, bold=True)

        # UI Setup
        self.buttons = []
        self._init_buttons()
        
        # System State
        self.reset_system()
        
        # Aesthetic: Pre-render scanlines
        self.scanline_surf = self._create_scanlines()

    def _init_buttons(self):
        bx = WIDTH - UI_WIDTH + 20
        bw = UI_WIDTH - 40
        by = 180
        gap = 45
        
        self.buttons.append(Button(bx, by, bw, 35, "[1] BUILD WALLS", 'wall'))
        self.buttons.append(Button(bx, by+gap, bw, 35, "[2] WIND ZONES", 'wind'))
        self.buttons.append(Button(bx, by+gap*2, bw, 35, "[3] MOVE DRONE", 'drone'))
        self.buttons.append(Button(bx, by+gap*3, bw, 35, "[4] MOVE TARGET", 'fire'))
        
        self.buttons.append(Button(bx, by+gap*5, bw, 45, "[SPACE] CALCULATE ROUTE", 'run', C_PATH_GLOW))
        self.buttons.append(Button(bx, by+gap*6.2, bw, 35, "[R] SYSTEM RESET", 'reset', C_FIRE))

    def _create_scanlines(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            pygame.draw.line(s, (0, 0, 0, 50), (0, y), (WIDTH, y))
        return s

    def reset_system(self):
        self.grid = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.start = (5, 8)
        self.end = (20, 25)
        self.tool = 'wall'
        self.algo_running = False
        self.path = []
        self.visited_cells = []
        self.scan_index = 0
        self.telemetry = {"BAT": 98, "SIG": 100, "WIND": 12}
        self.status = "SYSTEM READY"

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            mx, my = pygame.mouse.get_pos()
            
            # Button Hover Checks
            for btn in self.buttons:
                btn.check_hover(mx, my)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
                    # Check UI Buttons
                    clicked_ui = False
                    for btn in self.buttons:
                        if btn.hovered:
                            self.execute_command(btn.action_code)
                            clicked_ui = True
                            break
                    # If not UI, use tool on grid
                    if not clicked_ui and mx < WIDTH - UI_WIDTH:
                        self.use_tool(mx, my)
                
                elif event.button == 3: # Right Click
                    if mx < WIDTH - UI_WIDTH: self.use_tool(mx, my, erase=True)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: self.execute_command('wall')
                elif event.key == pygame.K_2: self.execute_command('wind')
                elif event.key == pygame.K_3: self.execute_command('drone')
                elif event.key == pygame.K_4: self.execute_command('fire')
                elif event.key == pygame.K_SPACE: self.execute_command('run')
                elif event.key == pygame.K_r: self.execute_command('reset')

    def execute_command(self, code):
        if code == 'run': self.run_dijkstra()
        elif code == 'reset': self.reset_system()
        else: self.tool = code

    def use_tool(self, mx, my, erase=False):
        if self.algo_running: return
        c, r = mx // CELL_SIZE, my // CELL_SIZE
        if not (0 <= r < GRID_ROWS and 0 <= c < GRID_COLS): return
        
        # Lock Start/End unless moving them
        if (r, c) in [self.start, self.end] and self.tool not in ['drone', 'fire']: return

        if erase:
            self.grid[r][c] = 0
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
        self.status = "CALCULATING ROUTE..."
        
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
        
        self.status = "ERROR: TARGET UNREACHABLE"
        self.algo_running = False

    def reconstruct_path(self, parent_map):
        curr = self.end
        while curr in parent_map:
            self.path.append(curr)
            curr = parent_map[curr]
            if curr == self.start: break
        self.path.append(self.start)
        self.path.reverse()

    def update(self):
        # Update Telemetry Jitter
        if pygame.time.get_ticks() % 10 == 0:
            self.telemetry["BAT"] = max(10, min(100, self.telemetry["BAT"] + random.uniform(-0.1, 0.1)))
            self.telemetry["SIG"] = max(80, min(100, self.telemetry["SIG"] + random.uniform(-2, 2)))
            self.telemetry["WIND"] = max(0, min(40, self.telemetry["WIND"] + random.uniform(-1, 1)))

        # Animation Speed
        if self.algo_running:
            if self.scan_index < len(self.visited_cells):
                self.scan_index += 35 # High speed scan
            else:
                if self.path: self.status = "PATH OPTIMIZED. DEPLOYING."

    def draw(self):
        self.screen.fill(C_BG)
        
        # --- LAYER 1: GRID & MAP ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x, y = c * CELL_SIZE, r * CELL_SIZE
                
                # Faint Grid Dots
                pygame.draw.circle(self.screen, C_GRID, (x+CELL_SIZE, y+CELL_SIZE), 1)
                
                val = self.grid[r][c]
                if val == 1: # Wall
                    pygame.draw.rect(self.screen, C_WALL, (x+1, y+1, CELL_SIZE-2, CELL_SIZE-2), border_radius=3)
                elif val == 2: # Wind
                    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s.fill((*C_WIND_ZONE, 80))
                    self.screen.blit(s, (x, y))

        # --- LAYER 2: SCANNING EFFECT ---
        limit = min(self.scan_index, len(self.visited_cells))
        for i in range(limit):
            r, c = self.visited_cells[i]
            if (r,c) != self.start and (r,c) != self.end:
                x, y = c * CELL_SIZE, r * CELL_SIZE
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                alpha = max(0, 150 - (self.scan_index - i)*2) # Fade tail
                if alpha > 0:
                    s.fill((*C_SCAN_WAVE, alpha))
                    self.screen.blit(s, (x, y))

        # --- LAYER 3: PATH (NEON) ---
        if self.scan_index >= len(self.visited_cells) and len(self.path) > 1:
            points = [(c*CELL_SIZE + CELL_SIZE//2, r*CELL_SIZE + CELL_SIZE//2) for r,c in self.path]
            if len(points) > 1:
                # Triple Glow
                pygame.draw.lines(self.screen, (*C_PATH_GLOW, 60), False, points, 12)
                pygame.draw.lines(self.screen, (*C_PATH_GLOW, 150), False, points, 6)
                pygame.draw.lines(self.screen, C_PATH_CORE, False, points, 2)

        # --- LAYER 4: ENTITIES ---
        # Drone
        sr, sc = self.start
        dr_rect = (sc*CELL_SIZE+4, sr*CELL_SIZE+4, CELL_SIZE-8, CELL_SIZE-8)
        pygame.draw.rect(self.screen, C_DRONE, dr_rect, border_radius=4)
        pygame.draw.rect(self.screen, (255,255,255), dr_rect, 2, border_radius=4) # Outline
        
        # Fire
        er, ec = self.end
        pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) / 2
        rad = (CELL_SIZE//2 - 4) + (pulse * 3)
        cx, cy = ec*CELL_SIZE+CELL_SIZE//2, er*CELL_SIZE+CELL_SIZE//2
        # Glow
        s = pygame.Surface((CELL_SIZE*2, CELL_SIZE*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*C_FIRE, 100), (CELL_SIZE, CELL_SIZE), int(rad)+4)
        self.screen.blit(s, (cx-CELL_SIZE, cy-CELL_SIZE))
        # Core
        pygame.draw.circle(self.screen, (255, 200, 200), (cx, cy), int(rad)-2)

        # --- LAYER 5: SIDEBAR UI ---
        # Panel BG
        ui_rect = pygame.Rect(WIDTH - UI_WIDTH, 0, UI_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, C_UI_BG, ui_rect)
        pygame.draw.line(self.screen, C_UI_BORDER, (WIDTH - UI_WIDTH, 0), (WIDTH - UI_WIDTH, HEIGHT), 2)

        # Header
        head_txt = self.font_header.render("FLYTBASE OPS", True, C_DRONE)
        self.screen.blit(head_txt, (WIDTH - UI_WIDTH + 20, 30))
        
        sub_txt = self.font_mono.render("AUTONOMOUS RESPONSE SYSTEM S3", True, C_TEXT_DIM)
        self.screen.blit(sub_txt, (WIDTH - UI_WIDTH + 22, 70))

        # Status
        stat_color = C_SCAN_WAVE if "OPTIMIZED" in self.status else (C_FIRE if "ERROR" in self.status else C_TEXT_MAIN)
        stat_lbl = self.font_ui.render(f"STATUS: {self.status}", True, stat_color)
        self.screen.blit(stat_lbl, (WIDTH - UI_WIDTH + 20, 110))

        # Buttons
        for btn in self.buttons:
            is_active = (btn.action_code == self.tool)
            btn.draw(self.screen, self.font_btn, active=is_active)

        # Telemetry Panel (Bottom Right)
        ty = HEIGHT - 200
        pygame.draw.rect(self.screen, (15, 20, 25), (WIDTH - UI_WIDTH + 20, ty, UI_WIDTH - 40, 180), border_radius=5)
        pygame.draw.rect(self.screen, C_UI_BORDER, (WIDTH - UI_WIDTH + 20, ty, UI_WIDTH - 40, 180), 1, border_radius=5)
        
        self._draw_telemetry_row("BATTERY", f"{self.telemetry['BAT']:.1f}%", C_SCAN_WAVE, ty + 20)
        self._draw_telemetry_row("SIGNAL", f"{self.telemetry['SIG']:.1f} dB", C_PATH_GLOW, ty + 60)
        self._draw_telemetry_row("WIND", f"{self.telemetry['WIND']:.1f} km/h", C_WIND_ZONE, ty + 100)
        self._draw_telemetry_row("COORDS", f"[{self.end[0]},{self.end[1]}]", C_TEXT_MAIN, ty + 140)

        # --- LAYER 6: OVERLAYS ---
        self.screen.blit(self.scanline_surf, (0, 0))

        pygame.display.flip()

    def _draw_telemetry_row(self, label, value, color, y):
        x = WIDTH - UI_WIDTH + 40
        lbl = self.font_mono.render(label, True, C_TEXT_DIM)
        val = self.font_ui.render(value, True, color)
        self.screen.blit(lbl, (x, y))
        self.screen.blit(val, (x + 160, y))

if __name__ == "__main__":
    app = FlytBaseDashboard()
    app.run()