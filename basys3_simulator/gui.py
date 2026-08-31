"""
Pygame Interactive GUI for Digilent Basys 3 FPGA Board Simulator.
Features:
- Well-proportioned Basys 3 PCB layout (16 switches, 16 LEDs, 5 pushbuttons, 4-digit 7-segment display).
- Collapsible right-side System Console drawer for live signal logging and design status.
- High-contrast, clean sans-serif typography with anti-aliasing.
"""

import os
import sys
import datetime

if os.environ.get("HEADLESS") == "1":
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from typing import Dict, Tuple, Optional, List
from .engine import SimulationEngine
from .xdc_parser import XDCParser
from .bitstream_loader import BitstreamLoader


# Color Palette
COLOR_BG = (22, 26, 33)            # Dark modern background
COLOR_BOARD = (14, 68, 44)         # Digilent PCB Emerald Green
COLOR_BOARD_BORDER = (8, 48, 30)   # Outer PCB edge
COLOR_TRACE = (22, 88, 58)         # PCB Traces
COLOR_CHIP = (26, 28, 32)          # Artix-7 Chip Black
COLOR_TEXT_MAIN = (240, 245, 250)
COLOR_TEXT_MUTED = (160, 175, 190)
COLOR_TEXT_GOLD = (235, 190, 70)

COLOR_PANEL_BG = (30, 36, 46)      # Console Panel Background
COLOR_PANEL_HEADER = (20, 24, 32)
COLOR_BUTTON = (52, 100, 150)
COLOR_BUTTON_HOVER = (70, 130, 190)
COLOR_BUTTON_ACTIVE = (30, 160, 100)

COLOR_LED_OFF = (45, 10, 10)
COLOR_LED_ON = (255, 45, 45)      # Bright Red LED Glow
COLOR_SEG_OFF = (32, 34, 38)
COLOR_SEG_ON = (255, 60, 60)      # Red 7-Segment Glow
COLOR_SW_OFF = (50, 55, 65)
COLOR_SW_ON = (0, 180, 230)       # Cyan Active Switch


class Basys3GUI:
    def __init__(self, base_width: int = 1000, height: int = 720):
        pygame.init()
        pygame.font.init()

        self.base_width = base_width
        self.console_width = 330
        self.console_open = True
        self.height = height

        self._update_window_size()
        pygame.display.set_caption("Digilent Basys 3 FPGA Board Simulator")

        # Fonts - clean sans-serif system fonts
        font_name = "segoeui,arial,helvetica,sans-serif"
        self.font_title = pygame.font.SysFont(font_name, 22, bold=True)
        self.font_header = pygame.font.SysFont(font_name, 15, bold=True)
        self.font_label = pygame.font.SysFont(font_name, 12, bold=True)
        self.font_console = pygame.font.SysFont("consolas,monospace", 12)

        self.engine = SimulationEngine()
        self.xdc_parser = XDCParser()
        self.loader = BitstreamLoader(self.engine, self.xdc_parser)

        self.status_msg = "Ready. Load a Bitstream, Verilog, or XDC file."
        self.loaded_filename = "None"

        # Console Logs
        self.logs: List[str] = []
        self.console_scroll = 0
        self.add_log("Basys 3 Simulator initialized.")
        self.add_log("Ready for bitstream / Verilog loading.")

        self.clock_ticks = 0
        self.auto_clock = False

        self.sw_rects: Dict[str, pygame.Rect] = {}
        self.btn_rects: Dict[str, pygame.Rect] = {}
        self.action_rects: Dict[str, pygame.Rect] = {}

        self._init_layout()

    def add_log(self, msg: str):
        """Adds a timestamped message to the system console log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {msg}")
        # Auto scroll to latest
        if len(self.logs) > 30:
            self.console_scroll = max(0, len(self.logs) - 25)

    def _update_window_size(self):
        curr_width = self.base_width + (self.console_width if self.console_open else 0)
        self.screen = pygame.display.set_mode((curr_width, self.height))

    def _init_layout(self):
        """Calculates perfectly aligned positions for board elements."""
        # Main PCB Board Rect
        self.board_rect = pygame.Rect(40, 75, 920, 580)

        # 16 Switches & 16 LEDs across bottom of PCB
        start_x = 75
        spacing = 52
        y_led = 475
        y_sw = 530

        for i in range(16):
            sw_idx = 15 - i
            actual_sw = f"SW{sw_idx}"
            x = start_x + i * spacing
            self.sw_rects[actual_sw] = pygame.Rect(x, y_sw, 34, 50)

        # Push Buttons (Top Right of Board - well above LEDs)
        btn_center_x = 780
        btn_center_y = 230
        sz = 38

        self.btn_rects["BTNC"] = pygame.Rect(btn_center_x, btn_center_y, sz, sz)
        self.btn_rects["BTNU"] = pygame.Rect(btn_center_x, btn_center_y - 48, sz, sz)
        self.btn_rects["BTND"] = pygame.Rect(btn_center_x, btn_center_y + 48, sz, sz)
        self.btn_rects["BTNL"] = pygame.Rect(btn_center_x - 48, btn_center_y, sz, sz)
        self.btn_rects["BTNR"] = pygame.Rect(btn_center_x + 48, btn_center_y, sz, sz)

        # Top Control Bar Action Buttons
        self.action_rects["LOAD"] = pygame.Rect(40, 18, 170, 38)
        self.action_rects["LOAD_XDC"] = pygame.Rect(220, 18, 110, 38)
        self.action_rects["CLK_PULSE"] = pygame.Rect(340, 18, 120, 38)
        self.action_rects["TOGGLE_AUTO_CLK"] = pygame.Rect(470, 18, 140, 38)
        self.action_rects["RESET"] = pygame.Rect(620, 18, 80, 38)
        self.action_rects["TOGGLE_CONSOLE"] = pygame.Rect(780, 18, 180, 38)

    def draw(self):
        """Renders simulator UI, PCB, hardware elements, and side console."""
        self.screen.fill(COLOR_BG)

        # 1. Top Control Bar
        self._draw_control_bar()

        # 2. Main Basys 3 Board PCB
        self._draw_pcb_board()

        # 3. Hardware Components
        self._draw_7segment_display()
        self._draw_artix7_chip()
        self._draw_buttons()
        self._draw_leds()
        self._draw_switches()

        # 4. Right Side Console Drawer
        if self.console_open:
            self._draw_console_panel()

        # 5. Status Footer
        status_text = f"File: {self.loaded_filename}  |  {self.status_msg}"
        status_surf = self.font_label.render(status_text, True, COLOR_TEXT_MUTED)
        self.screen.blit(status_surf, (40, 670))

        pygame.display.flip()

    def _draw_control_bar(self):
        mouse_pos = pygame.mouse.get_pos()

        for act, rect in self.action_rects.items():
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) else COLOR_BUTTON

            if act == "TOGGLE_AUTO_CLK" and self.auto_clock:
                color = COLOR_BUTTON_ACTIVE

            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, (100, 140, 180), rect, width=1, border_radius=6)

            lbl_text = act
            if act == "LOAD": lbl_text = "Load Bitstream / .v"
            elif act == "LOAD_XDC": lbl_text = "Load .XDC"
            elif act == "CLK_PULSE": lbl_text = "CLK Step (P)"
            elif act == "TOGGLE_AUTO_CLK": lbl_text = f"Auto CLK: {'ON' if self.auto_clock else 'OFF'}"
            elif act == "RESET": lbl_text = "Reset"
            elif act == "TOGGLE_CONSOLE": lbl_text = "Console <<" if self.console_open else "Console >>"

            lbl = self.font_header.render(lbl_text, True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl, (rect.x + (rect.width - lbl.get_width()) // 2, rect.y + (rect.height - lbl.get_height()) // 2))

    def _draw_pcb_board(self):
        """Draws realistic FPGA Emerald Green PCB board with details."""
        # Shadow
        shadow_rect = self.board_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(self.screen, (10, 12, 16), shadow_rect, border_radius=16)

        # PCB Green Body
        pygame.draw.rect(self.screen, COLOR_BOARD, self.board_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLOR_BOARD_BORDER, self.board_rect, width=4, border_radius=16)

        # PCB Corner Screw Holes
        for hx, hy in [(60, 95), (935, 95), (60, 635), (935, 635)]:
            pygame.draw.circle(self.screen, (180, 180, 180), (hx, hy), 7)
            pygame.draw.circle(self.screen, (30, 30, 30), (hx, hy), 4)

        # PCB Decorative Gold/Copper Traces
        pygame.draw.line(self.screen, COLOR_TRACE, (80, 160), (920, 160), width=2)
        pygame.draw.line(self.screen, COLOR_TRACE, (80, 435), (920, 435), width=2)

        # PCB Header Labels
        title_surf = self.font_title.render("DIGILENT BASYS 3", True, COLOR_TEXT_MAIN)
        sub_surf = self.font_label.render("Artix-7 FPGA Trainer Board Simulation", True, COLOR_TEXT_GOLD)
        self.screen.blit(title_surf, (80, 100))
        self.screen.blit(sub_surf, (80, 130))

    def _draw_artix7_chip(self):
        """Renders central Artix-7 FPGA Chip."""
        chip_rect = pygame.Rect(415, 190, 150, 150)
        pygame.draw.rect(self.screen, COLOR_CHIP, chip_rect, border_radius=8)
        pygame.draw.rect(self.screen, (60, 65, 75), chip_rect, width=2, border_radius=8)

        # Chip orientation pin 1 dot
        pygame.draw.circle(self.screen, (120, 120, 120), (430, 205), 4)

        lbl1 = self.font_header.render("XILINX", True, (210, 210, 210))
        lbl2 = self.font_label.render("Artix-7", True, (160, 160, 160))
        lbl3 = self.font_label.render("XC7A35T", True, (130, 130, 130))
        lbl4 = self.font_label.render("CPG236", True, (110, 110, 110))

        self.screen.blit(lbl1, (460, 220))
        self.screen.blit(lbl2, (465, 248))
        self.screen.blit(lbl3, (460, 270))
        self.screen.blit(lbl4, (465, 290))

    def _draw_7segment_display(self):
        """Renders 4-Digit 7-Segment Display module."""
        box_rect = pygame.Rect(80, 190, 270, 150)
        pygame.draw.rect(self.screen, (16, 18, 22), box_rect, border_radius=8)
        pygame.draw.rect(self.screen, (70, 75, 85), box_rect, width=2, border_radius=8)

        lbl = self.font_header.render("7-SEGMENT DISPLAY", True, COLOR_TEXT_MAIN)
        self.screen.blit(lbl, (140, 202))

        # Render 4 Digits
        for digit in range(4):
            an_name = f"AN{3 - digit}"
            an_active = (self.engine.get_output(an_name) == 0)

            x_off = box_rect.x + 25 + digit * 58
            y_off = box_rect.y + 38

            # Digit label below (AN3..AN0)
            an_lbl = self.font_label.render(f"AN{3-digit}", True, COLOR_TEXT_MUTED)
            self.screen.blit(an_lbl, (x_off + 8, y_off + 80))

            self._draw_single_digit(x_off, y_off, an_active)

    def _draw_single_digit(self, x: int, y: int, active: bool):
        """Renders single 7-segment digit with glow."""
        segs = {
            'A':  (self.engine.get_output("CA") == 0),
            'B':  (self.engine.get_output("CB") == 0),
            'C':  (self.engine.get_output("CC") == 0),
            'D':  (self.engine.get_output("CD") == 0),
            'E':  (self.engine.get_output("CE") == 0),
            'F':  (self.engine.get_output("CF") == 0),
            'G':  (self.engine.get_output("CG") == 0),
            'DP': (self.engine.get_output("DP") == 0),
        }

        def col(seg_name):
            if active and segs[seg_name]:
                return COLOR_SEG_ON
            return COLOR_SEG_OFF

        w, h, t = 28, 56, 6

        # Segment A, G, D
        pygame.draw.rect(self.screen, col('A'), (x + t, y, w, t), border_radius=2)
        pygame.draw.rect(self.screen, col('G'), (x + t, y + h//2 - t//2, w, t), border_radius=2)
        pygame.draw.rect(self.screen, col('D'), (x + t, y + h - t, w, t), border_radius=2)

        # Segment F, B, E, C
        pygame.draw.rect(self.screen, col('F'), (x, y + t, t, h//2 - t), border_radius=2)
        pygame.draw.rect(self.screen, col('B'), (x + w + t, y + t, t, h//2 - t), border_radius=2)
        pygame.draw.rect(self.screen, col('E'), (x, y + h//2 + t//2, t, h//2 - t), border_radius=2)
        pygame.draw.rect(self.screen, col('C'), (x + w + t, y + h//2 + t//2, t, h//2 - t), border_radius=2)

        # Decimal Point
        pygame.draw.circle(self.screen, col('DP'), (x + w + t + 10, y + h - 2), 4)

    def _draw_buttons(self):
        """Renders push button cross layout."""
        lbl_header = self.font_header.render("PUSH BUTTONS", True, COLOR_TEXT_MAIN)
        self.screen.blit(lbl_header, (732, 140))

        mouse_pos = pygame.mouse.get_pos()

        for btn_name, rect in self.btn_rects.items():
            val = self.engine.inputs.get(btn_name, 0)
            is_hover = rect.collidepoint(mouse_pos)

            if val == 1:
                color = (0, 200, 255)
            elif is_hover:
                color = (100, 110, 125)
            else:
                color = (70, 75, 88)

            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, width=2, border_radius=8)

            lbl = self.font_header.render(btn_name.replace("BTN", ""), True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl, (rect.x + (rect.width - lbl.get_width()) // 2, rect.y + (rect.height - lbl.get_height()) // 2))

    def _draw_leds(self):
        """Renders 16 LEDs across bottom of board."""
        start_x = 75
        spacing = 52
        y_led = 450

        for i in range(16):
            led_idx = 15 - i
            led_name = f"LED{led_idx}"
            x = start_x + i * spacing

            val = self.engine.get_output(led_name)
            color = COLOR_LED_ON if val == 1 else COLOR_LED_OFF

            # Label above LED (LD15..LD0)
            lbl = self.font_label.render(f"L{led_idx}", True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl, (x + 17 - lbl.get_width() // 2, y_led - 18))

            # LED Outer Glow
            if val == 1:
                pygame.draw.circle(self.screen, (255, 100, 100), (x + 17, y_led + 10), 13)
            pygame.draw.circle(self.screen, color, (x + 17, y_led + 10), 9)
            pygame.draw.circle(self.screen, (220, 220, 220), (x + 17, y_led + 10), 9, width=1)

    def _draw_switches(self):
        """Renders 16 Toggle Switches across bottom of board."""
        for i in range(16):
            sw_idx = 15 - i
            sw_name = f"SW{sw_idx}"
            rect = self.sw_rects[sw_name]
            val = self.engine.inputs.get(sw_name, 0)

            # Switch Socket Body
            pygame.draw.rect(self.screen, (22, 24, 28), rect, border_radius=6)
            pygame.draw.rect(self.screen, (60, 65, 75), rect, width=1, border_radius=6)

            # Switch Slider Handle
            knob_y = rect.y + 4 if val == 1 else rect.y + rect.height - 22
            knob_color = COLOR_SW_ON if val == 1 else COLOR_SW_OFF
            pygame.draw.rect(self.screen, knob_color, (rect.x + 4, knob_y, rect.width - 8, 18), border_radius=4)
            pygame.draw.rect(self.screen, (220, 220, 220), (rect.x + 4, knob_y, rect.width - 8, 18), width=1, border_radius=4)

            # Switch Label Below (SW15..SW0)
            lbl = self.font_label.render(f"SW{sw_idx}", True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl, (rect.x + 17 - lbl.get_width() // 2, rect.y + rect.height + 6))

    def _draw_console_panel(self):
        """Renders collapsible right side system console panel."""
        console_x = self.base_width
        panel_rect = pygame.Rect(console_x, 0, self.console_width, self.height)

        pygame.draw.rect(self.screen, COLOR_PANEL_BG, panel_rect)
        pygame.draw.line(self.screen, (50, 60, 75), (console_x, 0), (console_x, self.height), width=2)

        # Console Header
        header_rect = pygame.Rect(console_x, 0, self.console_width, 60)
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, header_rect)
        pygame.draw.line(self.screen, (50, 60, 75), (console_x, 60), (console_x + self.console_width, 60), width=1)

        title = self.font_header.render("SYSTEM CONSOLE & LOGS", True, COLOR_TEXT_MAIN)
        self.screen.blit(title, (console_x + 15, 20))

        # Log Output Area
        y_pos = 75
        visible_logs = self.logs[self.console_scroll:]
        for log in visible_logs[:32]:
            log_surf = self.font_console.render(log, True, (190, 210, 230))
            self.screen.blit(log_surf, (console_x + 15, y_pos))
            y_pos += 18

    def handle_click(self, pos: Tuple[int, int]):
        """Handles mouse interactions."""
        # 1. Toggle Switches
        for sw_name, rect in self.sw_rects.items():
            if rect.collidepoint(pos):
                curr = self.engine.inputs.get(sw_name, 0)
                new_val = 1 - curr
                self.engine.set_input(sw_name, new_val)
                self.engine.update_signals()
                self.add_log(f"{sw_name} set to {new_val}")
                return

        # 2. Action Buttons
        for act, rect in self.action_rects.items():
            if rect.collidepoint(pos):
                if act == "CLK_PULSE":
                    self.pulse_clock()
                elif act == "TOGGLE_AUTO_CLK":
                    self.auto_clock = not self.auto_clock
                    self.add_log(f"Auto Clock turned {'ON' if self.auto_clock else 'OFF'}")
                elif act == "RESET":
                    self.engine.reset()
                    self.engine.update_signals()
                    self.status_msg = "Engine Reset to default."
                    self.add_log("FPGA Simulation Engine Reset.")
                elif act == "TOGGLE_CONSOLE":
                    self.console_open = not self.console_open
                    self._update_window_size()
                elif act == "LOAD" or act == "LOAD_XDC":
                    self.status_msg = f"Drag and drop file or pass as CLI parameter to load {act}."
                return

    def pulse_clock(self):
        """Pulses CLK high then low."""
        self.engine.set_input("CLK", 1)
        self.engine.update_signals()
        self.engine.set_input("CLK", 0)
        self.engine.update_signals()
        self.clock_ticks += 1
        self.add_log(f"Clock Pulse (Cycle #{self.clock_ticks})")

    def handle_file_drop(self, filepath: str):
        """Processes files dragged and dropped into the window."""
        if self.loader.load_file(filepath):
            self.loaded_filename = os.path.basename(filepath)
            self.status_msg = f"Successfully loaded {self.loaded_filename}"
            self.add_log(f"Loaded file: {self.loaded_filename}")
            self.engine.update_signals()
        else:
            self.status_msg = f"Failed to parse file: {os.path.basename(filepath)}"
            self.add_log(f"ERROR: Failed to load {os.path.basename(filepath)}")

    def run(self):
        """Main Pygame Event Loop."""
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                        for btn_name, rect in self.btn_rects.items():
                            if rect.collidepoint(event.pos):
                                self.engine.set_input(btn_name, 1)
                                self.engine.update_signals()
                                self.add_log(f"Button {btn_name} Pressed")
                    elif event.button == 4:  # Scroll Up
                        if self.console_open:
                            self.console_scroll = max(0, self.console_scroll - 2)
                    elif event.button == 5:  # Scroll Down
                        if self.console_open:
                            self.console_scroll = min(max(0, len(self.logs) - 20), self.console_scroll + 2)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        for btn_name in self.btn_rects:
                            if self.engine.inputs.get(btn_name) == 1:
                                self.engine.set_input(btn_name, 0)
                                self.engine.update_signals()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p or event.key == pygame.K_SPACE:
                        self.pulse_clock()
                    elif event.key == pygame.K_c:
                        self.console_open = not self.console_open
                        self._update_window_size()
                elif event.type == pygame.DROPFILE:
                    self.handle_file_drop(event.file)

            if self.auto_clock:
                self.pulse_clock()

            self.draw()
            clock.tick(60)

        pygame.quit()
