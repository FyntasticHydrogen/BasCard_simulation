"""
XDC (Xilinx Design Constraints) Parser for Basys 3 FPGA Simulator.
Parses lines like:
  set_property PACKAGE_PIN V17 [get_ports {sw[0]}]
  set_property IOSTANDARD LVCMOS33 [get_ports {sw[0]}]
"""

import re
from typing import Dict, Optional

# Standard Basys 3 Board Pin Definitions
BASYS3_PIN_MAP = {
    # Switches
    "V17": "SW0",  "V16": "SW1",  "W16": "SW2",  "W17": "SW3",
    "W15": "SW4",  "V15": "SW5",  "W14": "SW6",  "W13": "SW7",
    "V2":  "SW8",  "T3":  "SW9",  "T2":  "SW10", "R3":  "SW11",
    "W2":  "SW12", "U1":  "SW13", "T1":  "SW14", "R2":  "SW15",

    # LEDs
    "U16": "LED0",  "E19": "LED1",  "U19": "LED2",  "V19": "LED3",
    "W18": "LED4",  "U15": "LED5",  "U14": "LED6",  "V14": "LED7",
    "V13": "LED8",  "V3":  "LED9",  "W3":  "LED10", "U3":  "LED11",
    "P3":  "LED12", "N3":  "LED13", "P1":  "LED14", "L1":  "LED15",

    # Buttons
    "U18": "BTNC",  "T18": "BTNU",  "W19": "BTNL",  "T17": "BTNR",  "U17": "BTND",

    # Clock
    "W5":  "CLK",

    # 7-Segment Anodes
    "W4":  "AN0",  "V4":  "AN1",  "U4":  "AN2",  "U2":  "AN3",

    # 7-Segment Cathodes
    "W7":  "CA",   "W6":  "CB",   "V8":  "CC",   "U8":  "CD",
    "V5":  "CE",   "U5":  "CF",   "V7":  "CG",   "M6":  "DP"
}


class XDCParser:
    def __init__(self):
        # Maps user top-level port name (e.g. 'sw[0]' or 'led[3]') to FPGA package pin (e.g. 'V17')
        self.port_to_pin: Dict[str, str] = {}
        # Maps FPGA package pin to user top-level port name
        self.pin_to_port: Dict[str, str] = {}
        # Maps user top-level port name to hardware component name (e.g. 'SW0', 'LED3')
        self.port_to_hardware: Dict[str, str] = {}
        # Maps hardware component name to user top-level port name
        self.hardware_to_port: Dict[str, str] = {}

        # Pre-populate default Basys 3 standard port naming conventions
        self._init_default_mappings()

    def _init_default_mappings(self):
        """Pre-populates standard Basys3 port names (sw[0]..sw[15], led[0]..led[15], etc.)."""
        for i in range(16):
            self.port_to_hardware[f"sw[{i}]"] = f"SW{i}"
            self.port_to_hardware[f"sw{i}"] = f"SW{i}"
            self.port_to_hardware[f"SW[{i}]"] = f"SW{i}"
            self.port_to_hardware[f"SW{i}"] = f"SW{i}"

            self.port_to_hardware[f"led[{i}]"] = f"LED{i}"
            self.port_to_hardware[f"led{i}"] = f"LED{i}"
            self.port_to_hardware[f"LED[{i}]"] = f"LED{i}"
            self.port_to_hardware[f"LED{i}"] = f"LED{i}"

        for btn in ["btnC", "btnU", "btnD", "btnL", "btnR", "BTNC", "BTNU", "BTND", "BTNL", "BTNR"]:
            self.port_to_hardware[btn] = btn.upper()

        self.port_to_hardware["clk"] = "CLK"
        self.port_to_hardware["CLK"] = "CLK"

        for i in range(4):
            self.port_to_hardware[f"an[{i}]"] = f"AN{i}"
            self.port_to_hardware[f"an{i}"] = f"AN{i}"

        seg_names = ["CA", "CB", "CC", "CD", "CE", "CF", "CG", "DP"]
        for idx, seg in enumerate(seg_names):
            self.port_to_hardware[f"seg[{idx}]"] = seg
            self.port_to_hardware[f"seg{idx}"] = seg
            self.port_to_hardware[seg.lower()] = seg

    def parse_file(self, filepath: str) -> None:
        """Reads and parses an XDC file."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.parse_string(content)

    def parse_string(self, content: str) -> None:
        """Parses XDC text content."""
        pattern = re.compile(
            r'set_property\s+PACKAGE_PIN\s+([A-Z0-9]+)\s+\[\s*get_ports\s+\{?([A-Za-z0-9_\[\]]+)\}?\s*\]',
            re.IGNORECASE
        )
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = pattern.search(line)
            if match:
                pin = match.group(1).upper()
                port = match.group(2)
                self.port_to_pin[port] = pin
                self.pin_to_port[pin] = port

                if pin in BASYS3_PIN_MAP:
                    hw_name = BASYS3_PIN_MAP[pin]
                    self.port_to_hardware[port] = hw_name
                    self.hardware_to_port[hw_name] = port

    def get_hardware_for_port(self, port_name: str) -> Optional[str]:
        """Returns the hardware element (e.g. 'SW0', 'LED1') for a given HDL port name."""
        if port_name in self.port_to_hardware:
            return self.port_to_hardware[port_name]
        cleaned = port_name.upper().replace("[", "").replace("]", "")
        if cleaned in BASYS3_PIN_MAP.values():
            return cleaned
        return None
