///////////////////////////////////////////////////////////////////////////////////
//  Copyright (c) 2025 SaxonSoc contributors
//  SPDX license identifier: MIT
//  Full license header bsp/efinix/EfxSapphireSoc/include/LICENSE.MD
//////////////////////////////////////////////////////////////////////////////////

/******************************************************************************
*
* @file main.c: i2cMasterInterruptDemo
*
* @brief This demo is functionally similar to i2cMasterDemo but includes interrupt support
*        to prevent the program from getting stuck if the slave device fails to respond.
*        It demonstrates the use of a timeout interrupt to handle stalled I2C communication.
*        The program operates as an I2C master, performing both single- and multi-byte reads
*        from a slave device, which can be emulated using I2CSlaveDemo.
*        It assumes it is the sole master on the bus and performs data transfers in a blocking manner.
*
******************************************************************************/
#include <stdint.h>
#include "bsp.h"
#include "i2c.h"
#include "riscv.h"
#include "clint.h"
#include "plic.h"
#include "userDef.h"

#define I2C_MASTER_ADDR 0x67    // Slave device address
#define WORD_REG_ADDR  0       // Set 0 if master only expect to send 1-byte of register address, else set 1.
#define I2C_FREQUENCY   100000  // Set your I2C Frequency here
#ifdef SYSTEM_I2C_0_IO_CTRL

void crash();
void trap_entry();
void externalInterrupt();

/******************************************************************************
*
* @brief This function initiates the configuration of I2C by setting it to 100kHz.
*
* @param i2c.samplingClockDivider => Sampling rate = (FCLK/(samplingClockDivider + 1).
* 							   	  => Controls the rate at which the I2C controller samples SCL and SDA.
*
* @param i2c.timeout => Inactive timeout clock cycle. The controller will drop the transfer when the value of the timeout is reached or exceeded.
* 				  => Setting the timeout value to zero will disable the timeout feature.
*
* @param i2c.tsuDat  => Data setup time. The number of clock cycles should SDA hold its state before the rising edge of SCL.
* @param i2c.tLow    => The number of clock cycles of SCL in LOW state.
* @param i2c.tHigh   => The number of clock cycles of SCL in HIGH state.
* @param i2c.tBuf 	 => The number of clock cycles delay before master can initiate a START bit after a STOP bit is issued.
* @return None.
*
******************************************************************************/
void init(){
    //I2C init
    I2c_Config i2c;
    i2c.samplingClockDivider    = 3;
    i2c.timeout                 = I2C_CTRL_HZ/10;               // timeout = 0.1s
    i2c.tsuDat                  = I2C_CTRL_HZ/I2C_FREQUENCY/3;  // tsuDat = 3.33us
    i2c.tLow                    = I2C_CTRL_HZ/I2C_FREQUENCY/2;  // tLow   = 5us
    i2c.tHigh                   = I2C_CTRL_HZ/I2C_FREQUENCY/2;  // tHigh  = 5us
    i2c.tBuf                    = I2C_CTRL_HZ/I2C_FREQUENCY;    // tBuf   = 10us

    i2c_applyConfig(I2C_CTRL, &i2c);                            // Apply the configs from i2c structure into the I2C controller.
	i2c_enableInterrupt(I2C_CTRL, I2C_INTERRUPT_DROP);

    //configure PLIC
    plic_set_threshold(BSP_PLIC, BSP_PLIC_CPU_0, 0);

    //enable PLIC I2C interrupts
    plic_set_enable(BSP_PLIC, BSP_PLIC_CPU_0, I2C_CTRL_PLIC_INTERRUPT, 1);
    plic_set_priority(BSP_PLIC, I2C_CTRL_PLIC_INTERRUPT, 1);

    //configure RISC-V interrupt CSR
    //Set the machine trap vector (trap.S)
    csr_write(mtvec, trap_entry);
    //Enable machine external interrupts
    csr_write(mie, MIE_MEIE);
    //Enable interrupts
    csr_write(mstatus, csr_read(mstatus) | MSTATUS_MPP | MSTATUS_MIE);
}

/******************************************************************************
*
* @brief This function handles exceptions and interrupts in the system.
*
* @note It is called by the trap_entry function on both exceptions and interrupts
* 		events. If the cause of the trap is an interrupt, it checks the cause of
* 		the interrupt and calls corresponding interrupt handler functions. If
* 		the cause is an exception or an unhandled interrupt, it calls a
*		crash function to handle the error.
*
******************************************************************************/
void trap(){
    int32_t mcause = csr_read(mcause);
    int32_t interrupt = mcause < 0;
    int32_t cause     = mcause & 0xF;

    if(interrupt){
        switch(cause){
        case CAUSE_MACHINE_EXTERNAL: externalInterrupt(); break;
        default: crash(); break;
        }
    }
    else
    {
      crash();
    }
}

/******************************************************************************
*
* @brief This function handles I2C interrupts and clear interrupt flag.
*
******************************************************************************/
void i2c_intc(){
	if (i2c_getInterruptFlag(I2C_CTRL) & I2C_INTERRUPT_DROP)
		bsp_printf("I2C Transfer is dropped due to timeout!\r\n");
	else
		bsp_printf("I2C Interrupt is triggered!\r\n");

	i2c_clearInterruptFlag(I2C_CTRL, I2C_INTERRUPT_DROP);
	while(1);

}
/******************************************************************************
*
* @brief This function handles I2C interrupts by claiming pending interrupts
* 		 and processing them through i2c_intc().
*
******************************************************************************/
void externalInterrupt(){
    uint32_t claim;
    //While there is pending interrupts
    while(claim = plic_claim(BSP_PLIC, BSP_PLIC_CPU_0)){
        switch(claim){
        case I2C_CTRL_PLIC_INTERRUPT: i2c_intc(); break;
        default:crash(); break;
        }
        //unmask the claimed interrupt
        plic_release(BSP_PLIC, BSP_PLIC_CPU_0, claim);
    }
}

/******************************************************************************
*
* @brief This function handles the system crash scenario by printing a crash message
* 		 and entering an infinite loop.
*
******************************************************************************/
void crash(){
    bsp_printf("\r\n*** CRASH ***\r\n");
    while(1);
}



/******************************************************************************
*
* @brief This main function demonstrates the functionality of I2C Master. It performs
*        single byte and multi-byte write-read operations with error checks.
*        The I2C Master communicates with an I2C Slave (or another compatible I2C
*        device) to perform the tests.
*
******************************************************************************/
void main() {
    bsp_init();
    init(); // Initiatize
    bsp_printf("I2C Master Interrupt Demo! \r\n Please ensure you've either connect to a compatible I2C Slave or running the i2cSlaveDemo with I2C ports connected.\r\n");
    bsp_printf("TEST STARTED ! \r\n");
    u8 dacValue[20];
    u8 readData[20];
    // Set default value for dacValue variable.
    for (int i = 0; i < 20; i++){
        dacValue[i] = i;
    }
    u8 slaveAddr = (I2C_MASTER_ADDR << 1) & 0xFF; // The slave address is shifted left by 1 bit to allocate the bit for rw bit
    while(1){ // Forever loop
        uint32_t ready;

#if ( WORD_REG_ADDR == 1) // 2-Byte Register Address
        //single byte write and read
        i2c_writeData_w_ack(I2C_CTRL, slaveAddr, 0x00, dacValue, 0x01); // Write a byte of dacValue array to address 0x00 with 2-byte of register address
        i2c_readData_w_ack(I2C_CTRL, slaveAddr, 0x00, readData , 0x01); // Read a byte of data from address 0x00 with 2-byte of register address
        // Make sure the data write and read are tally.
        if (dacValue[0] != readData[0]){
            bsp_printf("I2C single data write and read test failed. \r\n");
            while(1){};
        }

        //Multiple bytes write and read
        i2c_writeData_w_ack(I2C_CTRL, slaveAddr, 0x00, dacValue, 20); // Write 20 bytes of dacValue array to address 0x00 with 2-byte of register address
        i2c_readData_w_ack(I2C_CTRL, slaveAddr, 0x00, readData , 20); // Read 20 bytes of data from address 0x00 with 2-byte of register address
        // Make sure the data write and read are tally.
        for (int i = 0; i < 20; i++){
            if (dacValue[i] != readData[i]){
                bsp_printf("I2C multi data write and read test failed at data #%i \r\n", i);
                while(1){};
            }
        }
#else // 1-Byte Register Address
        //single byte write and read
        i2c_writeData_b_ack(I2C_CTRL, slaveAddr, 0x00, dacValue, 0x01); // Write a byte of dacValue array to address 0x00 with 1-byte of register address
        i2c_readData_b_ack(I2C_CTRL, slaveAddr, 0x00, readData , 0x01); // Read a byte of data from address 0x00 with 1-byte of register address
        // Make sure the data write and read are tally.
        if (dacValue[0] != readData[0]){
            bsp_printf("I2C single data write and read test failed. \r\n");
            while(1){};
        }

        //Multiple bytes write and read
        i2c_writeData_b_ack(I2C_CTRL, slaveAddr, 0x00, dacValue, 20); // Write 20 bytes of dacValue array to address 0x00 with 1-byte of register address
        i2c_readData_b_ack(I2C_CTRL, slaveAddr, 0x00, readData , 20); // Read 20 bytes of data from address 0x00 with 1-byte of register address
        // Make sure the data write and read are tally.
        for (int i = 0; i < 20; i++){
            if (dacValue[i] != readData[i]){
                bsp_printf("I2C multi data write and read test failed at data #%i \r\n", i);
                while(1){};
            }
        }
#endif
        bsp_printf("I2C Master Interrupt Demo completed. \r\n");
        bsp_printf("TEST PASSED! \r\n");
        while(1){};
    }
}
#else
/******************************************************************************
*
* @brief This main function is executed when I2C functionality is disabled.
*        It initializes the BSP and prints a message indicating that
*        I2C 0 is disabled, and the user should enable it to run the app.
*
******************************************************************************/
void main() {
    bsp_init();
    bsp_printf("i2c 0 is disabled, please enable it to run this app. \r\n");
}
#endif





