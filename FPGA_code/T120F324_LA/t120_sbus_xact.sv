// =============================================================================
// t120_sbus_xact.sv : S-bus command / ACK transaction FSM with timeout
// =============================================================================
// start -> send frame -> (unless no_ack) wait for a valid RX frame or timeout.
// Timeout is counted in microseconds (us_tick) from the end of the TX frame.
// A response frame with bad CRC (rx_err) also ends the transaction (software retries).
// abort returns to idle immediately.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_sbus_xact (
    input  wire        clk,
    input  wire        rstn,
    input  wire        us_tick,

    input  wire        start,
    input  wire        no_ack,
    input  wire [31:0] timeout_us,

    output logic       tx_start,
    input  wire        tx_done,
    input  wire        rx_ok,
    input  wire        rx_err,
    input  wire        abort,

    output logic       busy,
    output logic       done_p,
    output logic       timeout_p
);
    localparam [1:0] X_IDLE = 2'd0, X_TX = 2'd1, X_WAIT = 2'd2;

    logic [1:0]  st;
    logic [31:0] cnt;

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            st <= X_IDLE; cnt <= 32'd0; tx_start <= 1'b0;
            busy <= 1'b0; done_p <= 1'b0; timeout_p <= 1'b0;
        end else begin
            tx_start  <= 1'b0;
            done_p    <= 1'b0;
            timeout_p <= 1'b0;

            if (abort) begin
                st <= X_IDLE; busy <= 1'b0;
            end else case (st)
                X_IDLE: if (start) begin
                    tx_start <= 1'b1;
                    busy     <= 1'b1;
                    st       <= X_TX;
                end

                X_TX: if (tx_done) begin
                    if (no_ack) begin
                        st <= X_IDLE; busy <= 1'b0; done_p <= 1'b1;
                    end else begin
                        st  <= X_WAIT;
                        cnt <= timeout_us;
                    end
                end

                default: begin // X_WAIT
                    if (rx_ok || rx_err) begin
                        st <= X_IDLE; busy <= 1'b0; done_p <= 1'b1;
                    end else if (us_tick) begin
                        if (cnt <= 32'd1) begin
                            st <= X_IDLE; busy <= 1'b0; timeout_p <= 1'b1;
                        end else begin
                            cnt <= cnt - 32'd1;
                        end
                    end
                end
            endcase
        end
    end
endmodule
`default_nettype wire
