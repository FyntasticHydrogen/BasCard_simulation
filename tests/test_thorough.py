"""
Comprehensive unit, integration, and edge-case tests for Basys 3 FPGA Simulator.
"""

import os
import pygame
from basys3_simulator.engine import SimulationEngine, Gate, DFlipFlop
from basys3_simulator.xdc_parser import XDCParser, BASYS3_PIN_MAP
from basys3_simulator.bitstream_loader import BitstreamLoader
from basys3_simulator.gui import Basys3GUI


def test_all_gates():
    """Tests all logic gate types in the simulation engine."""
    engine = SimulationEngine()

    # BUF
    engine.add_gate("BUF", ["out_buf"], ["in1"])
    # NOT
    engine.add_gate("NOT", ["out_not"], ["in1"])
    # AND
    engine.add_gate("AND", ["out_and"], ["in1", "in2"])
    # OR
    engine.add_gate("OR", ["out_or"], ["in1", "in2"])
    # NAND
    engine.add_gate("NAND", ["out_nand"], ["in1", "in2"])
    # NOR
    engine.add_gate("NOR", ["out_nor"], ["in1", "in2"])
    # XOR
    engine.add_gate("XOR", ["out_xor"], ["in1", "in2"])
    # XNOR
    engine.add_gate("XNOR", ["out_xnor"], ["in1", "in2"])
    # LUT (INIT = 0x8 for 2-input AND logic)
    engine.add_gate("LUT", ["out_lut"], ["in1", "in2"], param=8)

    # Inputs: (0, 0)
    engine.set_input("in1", 0)
    engine.set_input("in2", 0)
    engine.update_signals()

    assert engine.signals["out_buf"] == 0
    assert engine.signals["out_not"] == 1
    assert engine.signals["out_and"] == 0
    assert engine.signals["out_or"] == 0
    assert engine.signals["out_nand"] == 1
    assert engine.signals["out_nor"] == 1
    assert engine.signals["out_xor"] == 0
    assert engine.signals["out_xnor"] == 1
    assert engine.signals["out_lut"] == 0

    # Inputs: (1, 1)
    engine.set_input("in1", 1)
    engine.set_input("in2", 1)
    engine.update_signals()

    assert engine.signals["out_buf"] == 1
    assert engine.signals["out_not"] == 0
    assert engine.signals["out_and"] == 1
    assert engine.signals["out_or"] == 1
    assert engine.signals["out_nand"] == 0
    assert engine.signals["out_nor"] == 0
    assert engine.signals["out_xor"] == 0
    assert engine.signals["out_xnor"] == 1
    assert engine.signals["out_lut"] == 1

    # Inputs: (1, 0)
    engine.set_input("in1", 1)
    engine.set_input("in2", 0)
    engine.update_signals()

    assert engine.signals["out_xor"] == 1
    assert engine.signals["out_xnor"] == 0

    print("All logic gates tested successfully!")


def test_dff_and_reset():
    """Tests D-Flip-Flop edge triggering and reset functionality."""
    engine = SimulationEngine()
    engine.add_dff(d_in="D", clk_in="CLK", q_out="Q", rst_in="RST")

    # Set D = 1, RST = 0, CLK = 0
    engine.set_input("D", 1)
    engine.set_input("RST", 0)
    engine.set_input("CLK", 0)
    engine.update_signals()
    assert engine.signals.get("Q", 0) == 0

    # Posedge CLK: 0 -> 1
    engine.set_input("CLK", 1)
    engine.update_signals()
    assert engine.signals["Q"] == 1

    # D changes while CLK is steady high -> Q should stay 1
    engine.set_input("D", 0)
    engine.update_signals()
    assert engine.signals["Q"] == 1

    # Reset on next clock pulse
    engine.set_input("RST", 1)
    engine.set_input("CLK", 0)
    engine.update_signals()
    engine.set_input("CLK", 1)
    engine.update_signals()
    assert engine.signals["Q"] == 0

    print("DFlipFlop tested successfully!")


def test_xdc_completeness():
    """Verifies standard Basys 3 XDC pin mappings for switches, LEDs, buttons, and 7-segment display."""
    parser = XDCParser()

    xdc_content = """
    set_property PACKAGE_PIN V17 [get_ports {sw[0]}]
    set_property PACKAGE_PIN R2  [get_ports {sw[15]}]
    set_property PACKAGE_PIN U16 [get_ports {led[0]}]
    set_property PACKAGE_PIN L1  [get_ports {led[15]}]
    set_property PACKAGE_PIN U18 [get_ports btnC]
    set_property PACKAGE_PIN W5  [get_ports clk]
    set_property PACKAGE_PIN W4  [get_ports {an[0]}]
    set_property PACKAGE_PIN W7  [get_ports {seg[0]}]
    """
    parser.parse_string(xdc_content)

    assert parser.get_hardware_for_port("sw[0]") == "SW0"
    assert parser.get_hardware_for_port("sw[15]") == "SW15"
    assert parser.get_hardware_for_port("led[0]") == "LED0"
    assert parser.get_hardware_for_port("led[15]") == "LED15"
    assert parser.get_hardware_for_port("btnC") == "BTNC"
    assert parser.get_hardware_for_port("clk") == "CLK"
    assert parser.get_hardware_for_port("an[0]") == "AN0"
    assert parser.get_hardware_for_port("seg[0]") == "CA"

    print("XDC completeness tested successfully!")


def test_verilog_parsing_and_always():
    """Tests Verilog parsing with assign statements, primitives, and always blocks."""
    engine = SimulationEngine()
    parser = XDCParser()
    loader = BitstreamLoader(engine, parser)

    verilog_src = """
    module top(
        input wire clk,
        input wire rst,
        input wire [15:0] sw,
        output wire [15:0] led,
        output wire [3:0] an,
        output wire [6:0] seg
    );
        assign led[0] = sw[0] & sw[1];
        assign led[1] = ~sw[2];
        assign led[2] = sw[3] | sw[4];

        and g1(led[3], sw[5], sw[6]);

        reg count;
        always @(posedge clk) begin
            count <= sw[7];
        end
    endmodule
    """
    tmp_path = "test_verilog_full.v"
    with open(tmp_path, "w") as f:
        f.write(verilog_src)

    assert loader.load_file(tmp_path) == True

    # Test sw[0] & sw[1] -> led[0]
    engine.set_input("SW0", 1)
    engine.set_input("SW1", 1)
    engine.update_signals()
    assert engine.signals.get("led[0]") == 1

    # Test ~sw[2] -> led[1]
    engine.set_input("SW2", 0)
    engine.update_signals()
    assert engine.signals.get("led[1]") == 1

    # Test gate primitive g1: sw[5] & sw[6] -> led[3]
    engine.set_input("SW5", 1)
    engine.set_input("SW6", 1)
    engine.update_signals()
    assert engine.signals.get("led[3]") == 1

    # Test DFF always block: sw[7] -> count on posedge clk
    engine.set_input("SW7", 1)
    engine.set_input("CLK", 0)
    engine.update_signals()
    assert engine.signals.get("count", 0) == 0

    engine.set_input("CLK", 1)
    engine.update_signals()
    assert engine.signals.get("count") == 1

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    print("Verilog full parsing tested successfully!")


def test_bitstream_header():
    """Tests binary bitstream header parsing."""
    engine = SimulationEngine()
    parser = XDCParser()
    loader = BitstreamLoader(engine, parser)

    design_name = "7a35t_top.ncd"
    part_name = "7a35tcpg236-1"

    # Standard Xilinx Bitstream format structure
    fake_bitstream = (
        b"\x00\x09\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00\x00\x01" +
        b"a" + len(design_name).to_bytes(2, "big") + design_name.encode("latin-1") +
        b"b" + len(part_name).to_bytes(2, "big") + part_name.encode("latin-1") +
        b"\xaa\x99\x55\x66"
    )
    header = loader.parse_xilinx_header(fake_bitstream)
    assert header.get("design_name") == "7a35t_top.ncd"
    assert header.get("part_name") == "7a35tcpg236-1"
    assert header.get("sync_word") == "FOUND (0xAA995566)"

    # Test loading bitstream file
    tmp_bit = "test_design.bit"
    with open(tmp_bit, "wb") as f:
        f.write(fake_bitstream)

    assert loader.load_file(tmp_bit) == True

    if os.path.exists(tmp_bit):
        os.remove(tmp_bit)

    print("Bitstream header parsing tested successfully!")


def test_gui_full_events():
    """Tests GUI event handling, button actions, switch clicks, 7-segment rendering, and dropfile."""
    os.environ["HEADLESS"] = "1"
    os.environ["SDL_VIDEODRIVER"] = "dummy"

    gui = Basys3GUI()
    gui.draw()

    # 1. Click every switch (SW0..SW15)
    for sw_name in [f"SW{i}" for i in range(16)]:
        rect = gui.sw_rects[sw_name]
        gui.handle_click((rect.x + 5, rect.y + 5))
        assert gui.engine.inputs[sw_name] == 1
        # Toggle back
        gui.handle_click((rect.x + 5, rect.y + 5))
        assert gui.engine.inputs[sw_name] == 0

    # 2. Click Action buttons: CLK_PULSE, TOGGLE_AUTO_CLK, RESET
    clk_rect = gui.action_rects["CLK_PULSE"]
    gui.handle_click((clk_rect.x + 5, clk_rect.y + 5))
    assert gui.clock_ticks == 1

    auto_clk_rect = gui.action_rects["TOGGLE_AUTO_CLK"]
    gui.handle_click((auto_clk_rect.x + 5, auto_clk_rect.y + 5))
    assert gui.auto_clock == True
    gui.handle_click((auto_clk_rect.x + 5, auto_clk_rect.y + 5))
    assert gui.auto_clock == False

    reset_rect = gui.action_rects["RESET"]
    gui.handle_click((reset_rect.x + 5, reset_rect.y + 5))

    # 3. Test non-existent dropfile handling
    gui.handle_file_drop("non_existent_file.v")
    assert "Failed to parse file" in gui.status_msg

    print("GUI full event testing passed!")


if __name__ == "__main__":
    test_all_gates()
    test_dff_and_reset()
    test_xdc_completeness()
    test_verilog_parsing_and_always()
    test_bitstream_header()
    test_gui_full_events()
    print("ALL THOROUGH TESTS PASSED SUCCESSFULLY!")
