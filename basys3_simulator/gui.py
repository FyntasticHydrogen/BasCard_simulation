"""
Pygame Interactive GUI for Digilent Basys 3 FPGA Board Simulator.
Renders 16 switches, 16 LEDs, 5 pushbuttons, 4-digit 7-segment display, system clock, and bitstream/verilog/XDC load controls.
"""

import os
import sys

# Headless Pygame support for headless testing environments
if os.environ.get("HEADLESS") == "1":
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from typing import Dict, Tuple, Optional, List
from .engine import SimulationEngine
from .xdc_parser import XDCParser
from .bitstream_loader import BitstreamLoader


# Color Palette
COLOR_BG = (30, 34, 42)
COLOR_BOARD = (0, 75, 45)       # Digilent Basys 3 FPGA Green PCB
COLOR_CHIP = (20, 20, 20)       # Artix-7 Chip Black
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DIM = (160, 160, 160)
COLOR_PANEL = (45, 50, 60)
COLOR_BUTTON = (70, 130, 180)
COLOR_BUTTON_HOVER = (100, 160, 210)

COLOR_LED_OFF = (40, 0, 0)
COLOR_LED_ON = (255, 40, 40)    # Bright Red LED
COLOR_SEG_OFF = (35, 35, 35)
COLOR_SEG_ON = (255, 50, 50)    # Red 7-Segment Glow
COLOR_SW_OFF = (60, 60, 60)
COLOR_SW_ON = (0, 180, 252)     # Cyan Active Switch


class Basys3GUI:
    def __init__(self, width: int = 1000, height: int = 700):
        pygame.init()
        pygame.font.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Digilent Basys 3 FPGA Board Simulator")

        self.font_large = pygame.font.SysFont("sans-serif", 24, bold=True)
        self.font_medium = pygame.font.SysFont("sans-serif", 16, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 13)

        self.engine = SimulationEngine()
        self.xdc_parser = XDCParser()
        self.loader = BitstreamLoader(self.engine, self.xdc_parser)

        # File loading status message
        self.status_msg = "Ready. Click 'Load Bitstream / Verilog' or drag & drop file."
        self.loaded_filename = "None"

        # Interactive Element Bounding Boxes
        self.sw_rects: Dict[str, pygame.Rect] = {}
        self.btn_rects: Dict[str, pygame.Rect] = {}
        self.action_rects: Dict[str, pygame.Rect] = {}

        self.clock_ticks = 0
        self.auto_clock = False
        self.clock_hz = 1

        self._init_layout()

    def _init_layout(self):
        """Calculates positions for switches, LEDs, buttons, and 7-segment display."""
        # Board dimensions
        self.board_rect = pygame.Rect(50, 80, 900, 560)

        # 16 Switches & 16 LEDs across bottom of board
        start_x = 90
        spacing = 50
        y_led = 540
        y_sw = 580

        for i in range(16):
            sw_name = f"SW{i}"
            led_name = f"LED{15-i}"
            # Render left-to-right SW15 -> SW0 to match physical Basys 3 hardware layout
            actual_sw = f"SW{15-i}"

            x = start_x + i * spacing
            self.sw_rects[actual_sw] = pygame.Rect(x, y_sw, 32, 45)

        # Push Buttons (BTNC in middle, BTNU top, BTND bottom, BTNL left, BTNR right)
        btn_center_x = 780
        btn_center_y = 440
        sz = 35

        self.btn_rects["BTNC"] = pygame.Rect(btn_center_x, btn_center_y, sz, sz)
        self.btn_rects["BTNU"] = pygame.Rect(btn_center_x, btn_center_y - 45, sz, sz)
        self.btn_rects["BTND"] = pygame.Rect(btn_center_x, btn_center_y + 45, sz, sz)
        self.btn_rects["BTNL"] = pygame.Rect(btn_center_x - 45, btn_center_y, sz, sz)
        self.btn_rects["BTNR"] = pygame.Rect(btn_center_x + 45, btn_center_y, sz, sz)

        # Top Control Bar Action Buttons
        self.action_rects["LOAD"] = pygame.Rect(50, 20, 180, 40)
        self.action_rects["LOAD_XDC"] = pygame.Rect(240, 20, 120, 40)
        self.action_rects["CLK_PULSE"] = pygame.Rect(370, 20, 110, 40)
        self.action_rects["TOGGLE_AUTO_CLK"] = pygame.Rect(490, 20, 140, 40)
        self.action_rects["RESET"] = pygame.Rect(640, 20, 80, 40)

    def draw(self):
        """Renders the entire simulator screen."""
        self.screen.fill(COLOR_BG)

        # 1. Top Control Bar
        self._draw_control_bar()

        # 2. Main Basys 3 Board PCB
        pygame.draw.rect(self.screen, COLOR_BOARD, self.board_rect, border_radius=15)
        pygame.draw.rect(self.screen, (0, 45, 25), self.board_rect, width=4, border_radius=15)

        # Board Title Header on PCB
        title_surf = self.font_large.render("DIGILENT BASYS 3", True, COLOR_TEXT)
        sub_surf = self.font_small.render("Artix-7 FPGA Trainer Board Simulation", True, COLOR_TEXT_DIM)
        self.screen.blit(title_surf, (80, 100))
        self.screen.blit(sub_surf, (80, 130))

        # Artix-7 Chip in Center
        chip_rect = pygame.Rect(400, 240, 140, 140)
        pygame.draw.rect(self.screen, COLOR_CHIP, chip_rect, border_radius=8)
        chip_lbl1 = self.font_medium.render("XILINX", True, (180, 180, 180))
        chip_lbl2 = self.font_small.render("Artix-7", True, (140, 140, 140))
        chip_lbl3 = self.font_small.render("XC7A35T", True, (120, 120, 120))
        self.screen.blit(chip_lbl1, (435, 270))
        self.screen.blit(chip_lbl2, (440, 295))
        self.screen.blit(chip_lbl3, (435, 315))

        # 3. Render Donanım Bileşenleri
        self._draw_leds()
        self._draw_switches()
        self._draw_buttons()
        self._draw_7segment_display()

        pygame.display.flip()

    def _draw_control_bar(self):
        # Draw buttons
        for act, rect in self.action_rects.items():
            mouse_pos = pygame.mouse.get_pos()
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) else COLOR_BUTTON

            if act == "TOGGLE_AUTO_CLK" and self.auto_clock:
                color = (40, 160, 80)

            pygame.draw.rect(self.screen, color, rect, border_radius=6)

            lbl_text = act
            if act == "LOAD": lbl_text = "Load Bitstream / .v"
            elif act == "LOAD_XDC": lbl_text = "Load .XDC"
            elif act == "CLK_PULSE": lbl_text = "CLK Step (P)"
            elif act == "TOGGLE_AUTO_CLK": lbl_text = f"Auto CLK: {'ON' if self.auto_clock else 'OFF'}"
            elif act == "RESET": lbl_text = "Reset"

            lbl = self.font_small.render(lbl_text, True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + (rect.width - lbl.get_width())//2, rect.y + (rect.height - lbl.get_height())//2))

        # Status text
        status_surf = self.font_small.render(f"File: {self.loaded_filename} | {self.status_msg}", True, (200, 220, 255))
        self.screen.blit(status_surf, (50, 650))

    def _draw_leds(self):
        start_x = 90
        spacing = 50
        y_led = 490

        for i in range(16):
            led_idx = 15 - i
            led_name = f"LED{led_idx}"
            x = start_x + i * spacing

            val = self.engine.get_output(led_name)
            color = COLOR_LED_ON if val == 1 else COLOR_LED_OFF

            # Draw LED diode circle & glow
            if val == 1:
                pygame.draw.circle(self.screen, (255, 120, 120), (x + 16, y_led + 8), 12)
            pygame.draw.circle(self.screen, color, (x + 16, y_led + 8), 8)
            pygame.draw.circle(self.screen, (200, 200, 200), (x + 16, y_led + 8), 8, width=1)

            # Label (LD15..LD0)
            lbl = self.font_small.render(f"L{led_idx}", True, COLOR_TEXT)
            self.screen.blit(lbl, (x + 6, y_led - 18))

    def _draw_switches(self):
        for i in range(16):
            sw_idx = 15 - i
            sw_name = f"SW{sw_idx}"
            rect = self.sw_rects[sw_name]
            val = self.engine.inputs.get(sw_name, 0)

            # Draw Switch Body
            pygame.draw.rect(self.screen, (20, 20, 20), rect, border_radius=4)

            # Switch Knob Position
            knob_y = rect.y + 4 if val == 1 else rect.y + rect.height - 20
            knob_color = COLOR_SW_ON if val == 1 else COLOR_SW_OFF
            pygame.draw.rect(self.screen, knob_color, (rect.x + 4, knob_y, rect.width - 8, 16), border_radius=3)

            # Label
            lbl = self.font_small.render(f"SW{sw_idx}", True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + 1, rect.y + rect.height + 4))

    def _draw_buttons(self):
        lbl_header = self.font_medium.render("PUSH BUTTONS", True, COLOR_TEXT)
        self.screen.blit(lbl_header, (735, 360))

        for btn_name, rect in self.btn_rects.items():
            val = self.engine.inputs.get(btn_name, 0)
            color = (0, 200, 255) if val == 1 else (90, 95, 105)

            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (220, 220, 220), rect, width=2, border_radius=8)

            lbl = self.font_small.render(btn_name.replace("BTN", ""), True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + (rect.width - lbl.get_width())//2, rect.y + (rect.height - lbl.get_height())//2))

    def _draw_7segment_display(self):
        """Renders the 4-digit 7-Segment display box on the PCB."""
        box_rect = pygame.Rect(120, 220, 240, 120)
        pygame.draw.rect(self.screen, (10, 10, 10), box_rect, border_radius=6)
        pygame.draw.rect(self.screen, (80, 80, 80), box_rect, width=2, border_radius=6)

        lbl = self.font_medium.render("7-SEGMENT DISPLAY", True, COLOR_TEXT)
        self.screen.blit(lbl, (155, 195))

        # Active Low Anodes AN3, AN2, AN1, AN0
        # Active Low Cathodes CA, CB, CC, CD, CE, CF, CG, DP
        for digit in range(4):
            an_name = f"AN{3 - digit}"
            an_active = (self.engine.get_output(an_name) == 0)

            x_off = box_rect.x + 20 + digit * 52
            y_off = box_rect.y + 20

            self._draw_single_digit(x_off, y_off, an_active)

    def _draw_single_digit(self, x: int, y: int, active: bool):
        """Draws a single 7-segment digit (A-G, DP)."""
        # Segment map: key -> active low output check
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

        w, h, t = 24, 45, 5

        # Horizontal segments A, G, D
        pygame.draw.rect(self.screen, col('A'), (x + t, y, w, t))
        pygame.draw.rect(self.screen, col('G'), (x + t, y + h//2, w, t))
        pygame.draw.rect(self.screen, col('D'), (x + t, y + h, w, t))

        # Vertical segments F, B (top left/right), E, C (bottom left/right)
        pygame.draw.rect(self.screen, col('F'), (x, y + t, t, h//2 - t))
        pygame.draw.rect(self.screen, col('B'), (x + w + t, y + t, t, h//2 - t))
        pygame.draw.rect(self.screen, col('E'), (x, y + h//2 + t, t, h//2 - t))
        pygame.draw.rect(self.screen, col('C'), (x + w + t, y + h//2 + t, t, h//2 - t))

        # Decimal point
        pygame.draw.circle(self.screen, col('DP'), (x + w + t + 8, y + h + 2), 3)

    def handle_click(self, pos: Tuple[int, int]):
        """Handles mouse clicks on switches, buttons, and top controls."""
        # 1. Check Toggle Switches
        for sw_name, rect in self.sw_rects.items():
            if rect.collidepoint(pos):
                curr = self.engine.inputs.get(sw_name, 0)
                self.engine.set_input(sw_name, 1 - curr)
                self.engine.update_signals()
                return

        # 2. Check Action Buttons
        for act, rect in self.action_rects.items():
            if rect.collidepoint(pos):
                if act == "CLK_PULSE":
                    self.pulse_clock()
                elif act == "TOGGLE_AUTO_CLK":
                    self.auto_clock = not self.auto_clock
                elif act == "RESET":
                    self.engine.reset()
                    self.engine.update_signals()
                    self.status_msg = "Engine Reset to Default."
                elif act == "LOAD" or act == "LOAD_XDC":
                    self.status_msg = f"Use command line or drag-and-drop to load {act} file."
                return

    def pulse_clock(self):
        """Pulses CLK high then low to trigger sequential DFFs."""
        self.engine.set_input("CLK", 1)
        self.engine.update_signals()
        self.engine.set_input("CLK", 0)
        self.engine.update_signals()
        self.clock_ticks += 1

    def handle_file_drop(self, filepath: str):
        """Processes files dragged & dropped into the window."""
        if self.loader.load_file(filepath):
            self.loaded_filename = os.path.basename(filepath)
            self.status_msg = f"Successfully loaded {self.loaded_filename}"
            self.engine.update_signals()
        else:
            self.status_msg = f"Failed to parse file: {os.path.basename(filepath)}"

    def run(self):
        """Main Pygame Event & Render Loop."""
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                        # Check pushbutton press
                        for btn_name, rect in self.btn_rects.items():
                            if rect.collidepoint(event.pos):
                                self.engine.set_input(btn_name, 1)
                                self.engine.update_signals()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        # Release pushbuttons
                        for btn_name in self.btn_rects:
                            if self.engine.inputs.get(btn_name) == 1:
                                self.engine.set_input(btn_name, 0)
                                self.engine.update_signals()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p or event.key == pygame.K_SPACE:
                        self.pulse_clock()
                elif event.type == pygame.DROPFILE:
                    self.handle_file_drop(event.file)

            if self.auto_clock:
                self.pulse_clock()

            self.draw()
            clock.tick(60)

        pygame.quit()
