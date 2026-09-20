module top_level (
    (* syn_peri_port = 0 *) input  logic T120_GCLK,
    (* syn_peri_port = 0 *) output logic T120_LED1,
    (* syn_peri_port = 0 *) output logic T120_LED2
);

    localparam integer LED1_TOGGLE_COUNT = 25_000_000;
    localparam integer LED2_TOGGLE_COUNT = 12_500_000;

    logic [24:0] led1_counter = '0;
    logic [23:0] led2_counter = '0;

    initial begin
        T120_LED1 = 1'b0;
        T120_LED2 = 1'b0;
    end

    always @(posedge T120_GCLK) begin
        if (led1_counter == LED1_TOGGLE_COUNT - 1) begin
            led1_counter <= '0;
            T120_LED1 <= ~T120_LED1;
        end else begin
            led1_counter <= led1_counter + 1'b1;
        end

        if (led2_counter == LED2_TOGGLE_COUNT - 1) begin
            led2_counter <= '0;
            T120_LED2 <= ~T120_LED2;
        end else begin
            led2_counter <= led2_counter + 1'b1;
        end
    end

endmodule
