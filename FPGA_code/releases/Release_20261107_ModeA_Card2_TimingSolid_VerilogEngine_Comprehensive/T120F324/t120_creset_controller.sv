// =============================================================================
// t120_creset_controller.sv : T20 CRESET_N control (patch wire, T120 pin LED1)
// =============================================================================
// level register : 1 = T20 released (default after T120 configuration), 0 = held in reset.
// pulse          : drives CRESET_N low for pulse_us microseconds (>= 10 ms
//                  required by T20), then returns to the level register value.
// Software writes and the S-bus watchdog (auto_pulse) can start a pulse.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_creset_controller (
    input  wire        clk,
    input  wire        rstn,
    input  wire        us_tick,

    input  wire        level_we,
    input  wire        level_val,
    input  wire        pulse_start,
    input  wire [23:0] pulse_us,

    output logic       creset_n,
    output logic       busy
);
    logic        level;
    logic [23:0] cnt;

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            level    <= 1'b1;
            creset_n <= 1'b1;
            busy     <= 1'b0;
            cnt      <= 24'd0;
        end else begin
            if (level_we) level <= level_val;

            if (busy) begin
                if (us_tick) begin
                    if (cnt <= 24'd1) begin
                        busy     <= 1'b0;
                        creset_n <= level;
                    end else begin
                        cnt <= cnt - 24'd1;
                    end
                end
            end else begin
                creset_n <= level_we ? level_val : level;
                if (pulse_start) begin
                    busy     <= 1'b1;
                    creset_n <= 1'b0;
                    cnt      <= pulse_us;
                end
            end
        end
    end
endmodule
`default_nettype wire
