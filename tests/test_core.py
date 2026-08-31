import os
from basys3_simulator.xdc_parser import XDCParser
from basys3_simulator.engine import SimulationEngine
from basys3_simulator.bitstream_loader import BitstreamLoader

def test_xdc_parser():
    parser = XDCParser()
    sample_xdc = """
    ## Switches
    set_property PACKAGE_PIN V17 [get_ports {sw[0]}]
    set_property PACKAGE_PIN V16 [get_ports {sw[1]}]
    ## LEDs
    set_property PACKAGE_PIN U16 [get_ports {led[0]}]
    set_property PACKAGE_PIN E19 [get_ports {led[1]}]
    """
    parser.parse_string(sample_xdc)
    assert parser.get_hardware_for_port("sw[0]") == "SW0"
    assert parser.get_hardware_for_port("sw[1]") == "SW1"
    assert parser.get_hardware_for_port("led[0]") == "LED0"
    assert parser.get_hardware_for_port("led[1]") == "LED1"
    print("XDC Parser test passed!")

def test_simulation_engine():
    engine = SimulationEngine()
    # Add AND gate: LED0 = SW0 AND SW1
    engine.add_gate("AND", ["LED0"], ["SW0", "SW1"])

    engine.set_input("SW0", 1)
    engine.set_input("SW1", 0)
    engine.update_signals()
    assert engine.get_output("LED0") == 0

    engine.set_input("SW1", 1)
    engine.update_signals()
    assert engine.get_output("LED0") == 1
    print("Simulation Engine test passed!")

def test_verilog_loader():
    engine = SimulationEngine()
    parser = XDCParser()
    loader = BitstreamLoader(engine, parser)

    verilog_code = """
    module top(
        input sw0,
        input sw1,
        output led0
    );
        assign led0 = sw0 ^ sw1;
    endmodule
    """
    with open("temp_test.v", "w") as f:
        f.write(verilog_code)

    loader.load_file("temp_test.v")
    engine.set_input("sw0", 1)
    engine.set_input("sw1", 1)
    engine.update_signals()
    assert engine.signals.get("led0") == 0

    engine.set_input("sw1", 0)
    engine.update_signals()
    assert engine.signals.get("led0") == 1

    if os.path.exists("temp_test.v"):
        os.remove("temp_test.v")
    print("Verilog Loader test passed!")

if __name__ == "__main__":
    test_xdc_parser()
    test_simulation_engine()
    test_verilog_loader()
    print("ALL CORE TESTS PASSED!")
