module top_level (
    (* syn_peri_port = 0 *) input  logic CLK_50MHZ,
    (* syn_peri_port = 0 *) output logic T20_LED1,
    (* syn_peri_port = 0 *) output logic T20_LED2,
    (* syn_peri_port = 0 *) output logic T20_LED3,
    (* syn_peri_port = 0 *) output logic T20_LED4,
    (* syn_peri_port = 0 *) output logic T20_LED5,
    (* syn_peri_port = 0 *) output logic T20_LED6,
    (* syn_peri_port = 0 *) output logic T20_LED7,
    (* syn_peri_port = 0 *) output logic T20_LED8
);

    // One counter step is 39.0625 ms at 50 MHz.
    localparam integer BASE_TICK_COUNT = 1_953_125;

    integer base_counter = 0;
    logic [7:0] led_counter = 8'b0;

    assign T20_LED1 = led_counter[0];
    assign T20_LED2 = led_counter[1];
    assign T20_LED3 = led_counter[2];
    assign T20_LED4 = led_counter[3];
    assign T20_LED5 = led_counter[4];
    assign T20_LED6 = led_counter[5];
    assign T20_LED7 = led_counter[6];
    assign T20_LED8 = led_counter[7];

    always @(posedge CLK_50MHZ) begin
        if (base_counter == BASE_TICK_COUNT - 1) begin
            base_counter <= 0;
            led_counter <= led_counter + 1'b1;
        end else begin
            base_counter <= base_counter + 1;
        end
    end

endmodule
