
module top(
    input wire clk,
    input wire [15:0] sw,
    output reg count
);
    always @(posedge clk) begin
        count <= sw[7];
    end
endmodule
