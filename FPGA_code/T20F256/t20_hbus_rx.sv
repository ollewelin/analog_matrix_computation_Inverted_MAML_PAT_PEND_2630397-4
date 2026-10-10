// =============================================================================
// t20_hbus_rx.sv : H-bus (Hadamard) receiver, T20 side. 100 % hardware, CLK9 domain.
// =============================================================================
// REQUIREMENT: no processor, no CRC, no handshake in this path. A W-bit shift
// register clocked by T20_CLK9 captures the word that T120 launches on the CLK9
// falling edge (sampled here on the rising edge, half a period of margin).
//
// Word timeline (see docs/t120_t20_bridge_spec.md), R(n) = CLK9 rising edge n:
//   R(S)       : h_sync=1, first (MSB) bit
//   R(S+W-1)   : last (LSB) bit sampled, vec register loaded
//   R(S+W)     : pad registers update (APPLY instant, all 30 outputs on the same edge)
//   R(S+W+1)   : h_ack pulse (one CLK9 cycle) launched
// h_sync restarts the capture at any time, so a partial word never desynchronises.
//
// Pad mapping (row k = vec[k-1]): M3 rows 1..8 = vec[7:0], M8 rows 1..7 = vec[14:8].
// Each row has an independent P and N pad:   en=0 -> P=0,N=0 (no perturbation)
//                                            en=1, bit=1 -> P=1,N=0 (+)
//                                            en=1, bit=0 -> P=0,N=1 (-)
// en_mask and the static override are configuration (set over the S-bus, never
// part of the timing path).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t20_hbus_rx #(
    parameter integer W = 16
)(
    input  wire         clk9,
    input  wire         rstn,

    input  wire         h_sync,
    input  wire         h_data,

    input  wire [15:0]  en_mask,
    input  wire         static_on,
    input  wire [15:0]  static_vec,

    output logic [15:0] pad_p,
    output logic [15:0] pad_n,
    output logic        ack,

    output logic [15:0] word_cnt,
    output logic [15:0] sync_err_cnt
);
    logic [W-1:0] sh;
    logic [W-1:0] vec;
    logic [7:0]   cnt;
    logic         busy;
    logic         done_q, ack_pipe;

    wire [15:0] vec16    = {{(16-W){1'b0}}, vec};
    wire [15:0] eff_vec  = static_on ? static_vec : vec16;

    always_ff @(posedge clk9 or negedge rstn) begin
        if (!rstn) begin
            sh <= '0; vec <= '0; cnt <= 8'd0; busy <= 1'b0;
            done_q <= 1'b0; ack_pipe <= 1'b0; ack <= 1'b0;
            pad_p <= 16'd0; pad_n <= 16'd0;
            word_cnt <= 16'd0; sync_err_cnt <= 16'd0;
        end else begin
            done_q <= 1'b0;

            if (h_sync) begin
                if (busy) sync_err_cnt <= sync_err_cnt + 16'd1;
                sh   <= {{(W-1){1'b0}}, h_data};
                cnt  <= 8'd1;
                busy <= 1'b1;
            end else if (busy) begin
                sh <= {sh[W-2:0], h_data};
                if (cnt == W - 1) begin
                    vec      <= {sh[W-2:0], h_data};
                    done_q   <= 1'b1;
                    busy     <= 1'b0;
                    word_cnt <= word_cnt + 16'd1;
                end else begin
                    cnt <= cnt + 8'd1;
                end
            end

            // APPLY: pads follow the vector register one edge after it is loaded
            pad_p <= eff_vec & en_mask;
            pad_n <= ~eff_vec & en_mask;

            ack_pipe <= done_q;
            ack      <= ack_pipe;
        end
    end
endmodule
`default_nettype wire
