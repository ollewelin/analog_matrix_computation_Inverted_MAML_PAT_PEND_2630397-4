// =============================================================================
// t120_bridge_clkgen.sv : T20_CLK9 generator + edge-event strobes
// =============================================================================
// Everything on the T120<->T20 bridge (H-bus and S-bus) is launched/sampled
// relative to the two strobes produced here, so all bridge logic stays in the
// sys_clk domain and has ZERO relative jitter.
//
//   fall_ev : sys_clk cycle in which clk9 falls at the END of the cycle.
//             All TX lanes are launched on this edge (T20 samples on the next
//             rising edge, i.e. half a CLK9 period later).
//   rise_ev : sys_clk cycle in which clk9 rises at the END of the cycle.
//             RX lanes (launched by T20 on its rising edge) are sampled here.
//
// CLK9 period = `period` sys_clk cycles (min 4). High phase = period/2.
//   50 MHz sys_clk:  period=5 -> 10 MHz ... period=40 -> 1.25 MHz.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_bridge_clkgen (
    input  wire        clk,
    input  wire        rstn,
    input  wire        enable,
    input  wire [11:0] period,
    output logic       clk9,
    output wire        rise_ev,
    output wire        fall_ev
);
    logic [11:0] cnt;
    logic [11:0] per_q;
    logic        run;

    wire [11:0] per_req = (period < 12'd4) ? 12'd4 : period;
    wire [11:0] half    = {1'b0, per_q[11:1]};

    assign rise_ev = enable && run && (cnt == per_q - 12'd1);
    assign fall_ev = enable && run && (cnt == half  - 12'd1);

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            run   <= 1'b0;
            cnt   <= 12'd0;
            clk9  <= 1'b0;
            per_q <= 12'd25;
        end else begin
            run <= enable;
            if (!enable) begin
                cnt   <= 12'd0;
                clk9  <= 1'b0;
                per_q <= per_req;
            end else if (rise_ev) begin
                cnt   <= 12'd0;
                clk9  <= 1'b1;
                per_q <= per_req;
            end else begin
                cnt <= cnt + 12'd1;
                if (fall_ev) clk9 <= 1'b0;
            end
        end
    end
endmodule
`default_nettype wire
