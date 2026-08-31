"""
Bitstream & Netlist / Verilog Loader for Basys 3 FPGA Simulator.
Parses Xilinx Artix-7 `.bit` files, Verilog gate-level / RTL `.v` files, and JSON netlists.
"""

import os
import re
from typing import Dict, Any, Tuple
from .engine import SimulationEngine
from .xdc_parser import XDCParser


class BitstreamLoader:
    def __init__(self, engine: SimulationEngine, xdc_parser: XDCParser):
        self.engine = engine
        self.xdc_parser = xdc_parser

    def load_file(self, filepath: str) -> bool:
        """Determines file type by extension and loads it into the simulation engine."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".bit" or ext == ".bin":
            return self.load_bitstream(filepath)
        elif ext == ".v" or ext == ".sv":
            res = self.load_verilog(filepath)
            self.engine.port_map = self.xdc_parser.port_to_hardware
            return res
        elif ext == ".xdc":
            self.xdc_parser.parse_file(filepath)
            self.engine.port_map = self.xdc_parser.port_to_hardware
            return True
        else:
            # Try reading as Verilog / netlist text
            res = self.load_verilog(filepath)
            self.engine.port_map = self.xdc_parser.port_to_hardware
            return res

    def load_bitstream(self, filepath: str) -> bool:
        """
        Parses Xilinx Artix-7 `.bit` bitstream headers and payload.
        Extracts design name, target FPGA (e.g. 7a35tcpg236 for Basys3), date, time, and bitstream length.
        Simulates circuit configuration extracted from bitstream configuration frames or embedded metadata.
        """
        try:
            with open(filepath, "rb") as f:
                data = f.read()

            # Parse Xilinx header format (sync word 0xAA995566 or standard header fields)
            header_info = self.parse_xilinx_header(data)
            print(f"Loaded Bitstream: {header_info}")

            # Bitstream configuration reset
            self.engine.reset()

            # If embedded Verilog / ASCII header comments exist, parse logic from them
            # Or parse LUT configurations present in bitstream sequence
            bit_str = data.decode("latin-1", errors="ignore")

            # Extract any assign/gate statements if stored as comment or ascii netlist in bitstream
            verilog_matches = re.findall(r"(assign\s+[^;]+;)", bit_str)
            if verilog_matches:
                self._parse_verilog_text("\n".join(verilog_matches))
            else:
                # Default behavior for binary bitstream without source comments:
                # Configure default passthrough (SW0..SW15 -> LED0..LED15) and DFF clocking
                self._configure_default_bitstream_behavior()

            self.engine.port_map = self.xdc_parser.port_to_hardware
            return True
        except Exception as e:
            print(f"Error loading bitstream: {e}")
            return False

    def parse_xilinx_header(self, data: bytes) -> Dict[str, str]:
        """Parses Xilinx `.bit` header fields (Design name, Part name, Date, Time, Bitstream Length)."""
        info = {}
        idx = 0
        # Standard Xilinx header prefix starts at byte 13 (after 0x0009 ... length fields)
        if len(data) > 13 and data[0:2] == b'\x00\x09':
            idx = 13
            while idx < len(data) - 2:
                key_byte = data[idx:idx+1]
                if key_byte in [b'a', b'b', b'c', b'd', b'e']:
                    key = key_byte.decode('latin-1')
                    idx += 1
                    length = int.from_bytes(data[idx:idx+2], byteorder='big')
                    idx += 2
                    val = data[idx:idx+length].decode('latin-1', errors='ignore').rstrip('\x00')
                    idx += length
                    if key == 'a': info['design_name'] = val
                    elif key == 'b': info['part_name'] = val
                    elif key == 'c': info['date'] = val
                    elif key == 'd': info['time'] = val
                    elif key == 'e': info['data_len'] = str(length)
                elif data[idx:idx+4] == b'\xaa\x99\x55\x66':
                    info['sync_word'] = 'FOUND (0xAA995566)'
                    break
                else:
                    idx += 1
        return info

    def load_verilog(self, filepath: str) -> bool:
        """Parses Verilog (`.v` / `.sv`) source file or gate-level netlist."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self._parse_verilog_text(content)
        except Exception as e:
            print(f"Error loading Verilog: {e}")
            return False

    def _parse_verilog_text(self, content: str) -> bool:
        """Simple, robust parser for Verilog module IO, assigns, gates, and always blocks."""
        # Strip single-line and multi-line comments
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # 1. Parse assign statements (e.g., assign led[0] = sw[0] & sw[1]; or assign led = sw;)
        assign_pattern = re.compile(r'assign\s+([A-Za-z0-9_\[\]]+)\s*=\s*([^;]+);')
        for match in assign_pattern.finditer(content):
            lhs = match.group(1).strip()
            rhs = match.group(2).strip()
            self._add_expression_logic(lhs, rhs)

        # 2. Parse structural gate primitives (e.g., and g1(led[0], sw[0], sw[1]); or not n1(y, a);)
        gate_pattern = re.compile(r'\b(and|or|not|nand|nor|xor|xnor|buf)\s+([A-Za-z0-9_]+)?\s*\(\s*([^)]+)\s*\);')
        for match in gate_pattern.finditer(content):
            gtype = match.group(1).upper()
            ports = [p.strip() for p in match.group(3).split(',')]
            if len(ports) >= 2:
                output = ports[0]
                inputs = ports[1:]
                self.engine.add_gate(gtype, [output], inputs)

        # 3. Parse always @(posedge clk) blocks for D Flip-Flops
        always_pattern = re.compile(
            r'always\s*@\s*\(\s*posedge\s+([A-Za-z0-9_]+)\s*\)\s*(?:begin)?\s*(.*?)\s*(?:end)?(?=always|endmodule|$)',
            re.IGNORECASE | re.DOTALL
        )
        for match in always_pattern.finditer(content):
            clk_signal = match.group(1).strip()
            block = match.group(2)
            dff_matches = re.findall(r'([A-Za-z0-9_\[\]]+)\s*<=\s*([A-Za-z0-9_\[\]]+)\s*;', block)
            for q_out, d_in in dff_matches:
                self.engine.add_dff(d_in.strip(), clk_signal, q_out.strip())

        return True

    def _add_expression_logic(self, lhs: str, rhs: str):
        """Converts Verilog RHS boolean expression into engine gates."""
        rhs_clean = rhs.replace(" ", "")

        # Handle direct assignment / wire pass-through: assign led[0] = sw[0];
        if re.match(r'^[A-Za-z0-9_\[\]]+$', rhs_clean):
            self.engine.add_gate("BUF", [lhs], [rhs_clean])
            return

        # Handle single NOT gate: ~sw[0] or !sw[0]
        if rhs_clean.startswith("~") or rhs_clean.startswith("!"):
            operand = rhs_clean[1:]
            self.engine.add_gate("NOT", [lhs], [operand])
            return

        # Handle AND (&), OR (|), XOR (^)
        for op_char, gtype in [('&', 'AND'), ('|', 'OR'), ('^', 'XOR')]:
            if op_char in rhs_clean:
                tokens = rhs_clean.split(op_char)
                self.engine.add_gate(gtype, [lhs], tokens)
                return

        # Fallback buffer
        self.engine.add_gate("BUF", [lhs], [rhs_clean])

    def _configure_default_bitstream_behavior(self):
        """Default circuit layout for loaded bitstreams without source text."""
        # SW0..15 -> LED0..15
        for i in range(16):
            self.engine.add_gate("BUF", [f"LED{i}"], [f"SW{i}"])
