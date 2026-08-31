"""
Simulation Engine for Basys 3 FPGA Simulator.
Supports combinational logic (AND, OR, NOT, XOR, NAND, NOR, XNOR, MUX, LUT),
sequential logic (D Flip-Flops triggered on clock posedge), and custom netlists.
"""

from typing import Dict, List, Set, Callable, Any, Optional

class Gate:
    def __init__(self, gate_type: str, outputs: List[str], inputs: List[str], extra_param: Any = None):
        self.type = gate_type.upper()
        self.outputs = outputs
        self.inputs = inputs
        self.param = extra_param

class DFlipFlop:
    def __init__(self, d_in: str, clk_in: str, q_out: str, rst_in: Optional[str] = None):
        self.d = d_in
        self.clk = clk_in
        self.q = q_out
        self.rst = rst_in
        self.state = 0
        self.last_clk = 0

class SimulationEngine:
    def __init__(self):
        # Current state of all signals (wires/ports) -> 0 or 1
        self.signals: Dict[str, int] = {}
        # Hardware inputs (SW0-SW15, BTNC, BTNU, BTND, BTNL, BTNR, CLK)
        self.inputs: Dict[str, int] = {f"SW{i}": 0 for i in range(16)}
        for btn in ["BTNC", "BTNU", "BTND", "BTNL", "BTNR"]:
            self.inputs[btn] = 0
        self.inputs["CLK"] = 0

        # Hardware outputs (LED0-LED15, AN0-AN3, CA-CG, DP)
        self.outputs: Dict[str, int] = {f"LED{i}": 0 for i in range(16)}
        for an in range(4):
            self.outputs[f"AN{an}"] = 1  # Active Low default OFF
        for seg in ["CA", "CB", "CC", "CD", "CE", "CF", "CG", "DP"]:
            self.outputs[seg] = 1        # Active Low default OFF

        # Port mapping to hardware (e.g. 'sw[0]' -> 'SW0')
        self.port_map: Dict[str, str] = {}

        # Logic gates and DFFs
        self.gates: List[Gate] = []
        self.dffs: List[DFlipFlop] = []

        # Custom python evaluation callback (for complex Verilog or LUT execution)
        self.eval_callback: Optional[Callable[[Dict[str, int]], Dict[str, int]]] = None

    def reset(self):
        """Resets all signals and outputs."""
        self.signals = {k: 0 for k in self.inputs}
        for hw, val in self.inputs.items():
            self.signals[hw] = val
        self.outputs = {f"LED{i}": 0 for i in range(16)}
        for an in range(4):
            self.outputs[f"AN{an}"] = 1
        for seg in ["CA", "CB", "CC", "CD", "CE", "CF", "CG", "DP"]:
            self.outputs[seg] = 1
        for dff in self.dffs:
            dff.state = 0
            dff.last_clk = 0

    def set_input(self, hw_name: str, value: int):
        """Sets hardware input state (e.g. SW0 = 1)."""
        value = 1 if value else 0
        self.inputs[hw_name] = value
        self.signals[hw_name] = value

        # Also update connected ports if mapping exists
        for port, hw in self.port_map.items():
            if hw == hw_name:
                self.signals[port] = value

    def get_output(self, hw_name: str) -> int:
        """Gets hardware output state."""
        return self.outputs.get(hw_name, 0)

    def add_gate(self, gate_type: str, outputs: List[str], inputs: List[str], param: Any = None):
        self.gates.append(Gate(gate_type, outputs, inputs, param))

    def add_dff(self, d_in: str, clk_in: str, q_out: str, rst_in: Optional[str] = None):
        self.dffs.append(DFlipFlop(d_in, clk_in, q_out, rst_in))

    def update_signals(self):
        """Propagates signal values through gates and registers."""
        # 1. Map HW inputs to port signals
        for port, hw in self.port_map.items():
            if hw in self.inputs:
                self.signals[port] = self.inputs[hw]

        # Direct connection default if no port map
        for hw_name, val in self.inputs.items():
            if hw_name not in self.signals:
                self.signals[hw_name] = val

        # 2. Custom callback evaluation if registered
        if self.eval_callback:
            custom_out = self.eval_callback(self.signals)
            if custom_out:
                self.signals.update(custom_out)

        # 3. Evaluate DFFs on posedge CLK
        for dff in self.dffs:
            clk_val = self.signals.get(dff.clk, self.inputs.get("CLK", 0))
            if dff.last_clk == 0 and clk_val == 1:  # Posedge
                if dff.rst and self.signals.get(dff.rst, 0) == 1:
                    dff.state = 0
                else:
                    dff.state = self.signals.get(dff.d, 0)
            dff.last_clk = clk_val
            self.signals[dff.q] = dff.state

        # 4. Evaluate Combinational Gates (iterative relaxation to settle loops)
        max_passes = 10
        for _ in range(max_passes):
            changed = False
            for gate in self.gates:
                in_vals = [self.signals.get(inp, 0) for inp in gate.inputs]
                out_val = 0

                if gate.type == "BUF" or gate.type == "ASSIGN":
                    out_val = in_vals[0] if in_vals else 0
                elif gate.type == "NOT":
                    out_val = 1 - in_vals[0] if in_vals else 1
                elif gate.type == "AND":
                    out_val = 1 if all(v == 1 for v in in_vals) else 0
                elif gate.type == "OR":
                    out_val = 1 if any(v == 1 for v in in_vals) else 0
                elif gate.type == "NAND":
                    out_val = 0 if all(v == 1 for v in in_vals) else 1
                elif gate.type == "NOR":
                    out_val = 0 if any(v == 1 for v in in_vals) else 1
                elif gate.type == "XOR":
                    res = 0
                    for v in in_vals:
                        res ^= v
                    out_val = res
                elif gate.type == "XNOR":
                    res = 0
                    for v in in_vals:
                        res ^= v
                    out_val = 1 - res
                elif gate.type == "LUT":
                    # gate.param is integer mask/init string
                    bit_idx = 0
                    for idx, val in enumerate(in_vals):
                        if val:
                            bit_idx |= (1 << idx)
                    init_mask = int(gate.param) if gate.param is not None else 0
                    out_val = (init_mask >> bit_idx) & 1

                out_name = gate.outputs[0]
                if self.signals.get(out_name) != out_val:
                    self.signals[out_name] = out_val
                    changed = True
            if not changed:
                break

        # 5. Map outputs back to hardware elements
        for port, hw in self.port_map.items():
            if hw in self.outputs:
                self.outputs[hw] = self.signals.get(port, 0)

        # Fallback direct mappings if not explicitly mapped
        for hw_name in list(self.outputs.keys()):
            if hw_name in self.signals:
                self.outputs[hw_name] = self.signals[hw_name]
