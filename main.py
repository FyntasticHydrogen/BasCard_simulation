"""
Main Entry point for Basys 3 FPGA Simulator.
Usage:
  python main.py
  python main.py <path_to_bitstream_or_verilog> [<path_to_xdc>]
"""

import sys
import os
from basys3_simulator.gui import Basys3GUI

def main():
    gui = Basys3GUI()

    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        if os.path.exists(target_file):
            gui.handle_file_drop(target_file)

    if len(sys.argv) > 2:
        xdc_file = sys.argv[2]
        if os.path.exists(xdc_file):
            gui.handle_file_drop(xdc_file)

    gui.run()

if __name__ == "__main__":
    main()
