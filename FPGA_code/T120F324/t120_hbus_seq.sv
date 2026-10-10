// =============================================================================
// t120_hbus_seq.sv : H-bus (Hadamard) hardware sequencer, T120 side
// =============================================================================
// REQUIREMENT: the Hadamard path is 100% hardware-synchronous from T120 to T20.
// No processor code, no CRC, no handshake wait is ever in the timing path.
// The CPU only (1) loads the table, (2) writes count/period, (3) pulses START.
// After START every step is emitted at an exact multiple of CLK9 cycles.
//
// Wires (all launched on the CLK9 falling edge, sampled by T20 on the rising edge):
//   h_sync : 1 CLK9 cycle high, together with the first (MSB) bit of a step
//   h_data : W bits per step, one bit per CLK9 cycle, MSB first
//   ack_in : 1-bit ACK from T20 (pulse), sampled on the CLK9 rising event
//
// Step timeline (c = CLK9 cycle inside a step, step period = `period` cycles):
//   c=0 table address, c=1 table data latched, c=2 SYNC + bit W-1,
//   c=3..W+1 bits W-2..0, remaining cycles idle (0).
//   T20 loads its vector register on the rising edge that samples bit 0; the
//   vector is applied from the following CLK9 cycle (fixed offset, see spec).
//
// ACK is only a 1-bit timing proof. T120 measures the latency (in CLK9 cycles)
// from the SYNC cycle to the first ACK pulse of the step and keeps last/min/max:
// min == max proves zero jitter. A missing / out-of-window ACK increments
// ack_miss. Neither ever stalls or alters the stream.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_hbus_seq #(
    parameter integer W  = 16,   // Hadamard word width in bits (<= 32)
    parameter integer DL = 8     // log2(table depth)
)(
    input  wire        clk,
    input  wire        rstn,
    input  wire        fall_ev,
    input  wire        rise_ev,

    // Table (synchronous read RAM outside)
    output logic [DL-1:0] rd_addr,
    input  wire  [31:0]   rd_data,

    // Control
    input  wire        start,
    input  wire        stop,
    input  wire        clr,
    input  wire        loop_en,
    input  wire        ack_en,
    input  wire [15:0] count,
    input  wire [15:0] period,
    input  wire [7:0]  ack_min,
    input  wire [7:0]  ack_max,

    // Bus pins (registered)
    output logic       h_sync,
    output logic       h_data,
    input  wire        ack_in,

    // Status
    output logic       running,
    output logic       done,
    output logic       ack_miss_sticky,
    output logic [15:0] step,
    output logic [31:0] ack_ok,
    output logic [31:0] ack_miss,
    output logic [15:0] lat_last,
    output logic [15:0] lat_min,
    output logic [15:0] lat_max,
    output logic       step_strobe
);
    localparam [15:0] MIN_PERIOD = W + 3;
    localparam [16:0] DEPTH = (17'd1 << DL);

    wire [15:0] period_eff = (period < MIN_PERIOD) ? MIN_PERIOD : period;
    wire [15:0] count_eff  = ({1'b0, count} > DEPTH) ? DEPTH[15:0] : count;

    logic        start_pend, stop_pend;
    logic [15:0] c;
    logic [W-1:0] shreg;
    logic [15:0] cyc;
    logic [15:0] sync_cyc;
    logic        ack_pend, ack_seen;
    logic        ack_prev;

    wire ack_evt = ack_in & ~ack_prev;
    wire [15:0] lat_now = cyc - sync_cyc;

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            rd_addr <= '0; h_sync <= 1'b0; h_data <= 1'b0;
            running <= 1'b0; done <= 1'b0; ack_miss_sticky <= 1'b0;
            step <= 16'd0; ack_ok <= 32'd0; ack_miss <= 32'd0;
            lat_last <= 16'd0; lat_min <= 16'hFFFF; lat_max <= 16'd0;
            step_strobe <= 1'b0;
            start_pend <= 1'b0; stop_pend <= 1'b0;
            c <= 16'd0; shreg <= '0; cyc <= 16'd0; sync_cyc <= 16'd0;
            ack_pend <= 1'b0; ack_seen <= 1'b0; ack_prev <= 1'b0;
        end else begin
            step_strobe <= 1'b0;
            if (start && !running) begin start_pend <= 1'b1; done <= 1'b0; end
            if (stop)  stop_pend <= 1'b1;

            if (clr) begin
                ack_ok <= 32'd0; ack_miss <= 32'd0; ack_miss_sticky <= 1'b0;
                lat_last <= 16'd0; lat_min <= 16'hFFFF; lat_max <= 16'd0;
            end

            // ---------------- ACK sampling (CLK9 rising event) ----------------
            if (rise_ev) begin
                ack_prev <= ack_in;
                if (ack_evt && ack_pend && !ack_seen) begin
                    ack_seen <= 1'b1;
                    lat_last <= lat_now;
                    if (lat_now < lat_min) lat_min <= lat_now;
                    if (lat_now > lat_max) lat_max <= lat_now;
                    if (lat_now >= {8'd0, ack_min} && lat_now <= {8'd0, ack_max}) begin
                        ack_ok <= ack_ok + 32'd1;
                    end else begin
                        ack_miss <= ack_miss + 32'd1;
                        ack_miss_sticky <= 1'b1;
                    end
                end
            end

            // ---------------- Step engine (CLK9 falling event) ----------------
            if (fall_ev) begin
                cyc    <= cyc + 16'd1;
                h_sync <= 1'b0;
                h_data <= 1'b0;

                if (ack_pend && !ack_seen && lat_now > {8'd0, ack_max}) begin
                    ack_pend <= 1'b0;
                    ack_miss <= ack_miss + 32'd1;
                    ack_miss_sticky <= 1'b1;
                end

                if (stop_pend) begin
                    stop_pend <= 1'b0; start_pend <= 1'b0;
                    running <= 1'b0; ack_pend <= 1'b0;
                end else if (running) begin
                    if (c == 16'd0) begin
                        rd_addr <= step[DL-1:0];
                    end else if (c == 16'd1) begin
                        shreg <= rd_data[W-1:0];
                    end else if (c == 16'd2) begin
                        h_sync   <= 1'b1;
                        h_data   <= shreg[W-1];
                        shreg    <= {shreg[W-2:0], 1'b0};
                        sync_cyc <= cyc;
                        ack_pend <= ack_en;
                        ack_seen <= 1'b0;
                        step_strobe <= 1'b1;
                    end else if (c <= W + 1) begin
                        h_data <= shreg[W-1];
                        shreg  <= {shreg[W-2:0], 1'b0};
                    end

                    if (c >= period_eff - 16'd1) begin
                        c <= 16'd0;
                        if (step + 16'd1 >= count_eff) begin
                            if (loop_en) step <= 16'd0;
                            else begin running <= 1'b0; done <= 1'b1; end
                        end else begin
                            step <= step + 16'd1;
                        end
                    end else begin
                        c <= c + 16'd1;
                    end
                end else if (start_pend) begin
                    start_pend <= 1'b0;
                    if (count_eff != 16'd0) begin
                        running <= 1'b1;
                        c       <= 16'd0;
                        step    <= 16'd0;
                        done    <= 1'b0;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
