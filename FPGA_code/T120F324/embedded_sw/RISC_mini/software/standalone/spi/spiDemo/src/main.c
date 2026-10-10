///////////////////////////////////////////////////////////////////////////////////
//  Copyright (c) 2025 SaxonSoc contributors
//  SPDX license identifier: MIT
//  Full license header bsp/efinix/EfxSapphireSoc/include/LICENSE.MD
///////////////////////////////////////////////////////////////////////////////////

/******************************************************************************
*
* @file main.c: spiDemo
*
* @brief This demo provides example code for reading the device ID and JEDEC ID of the SPI flash 
*        device on the development board. The application displays the results on a UART terminal. 
*        It continues to print to the terminal until you suspend or stop the application.
*
* @note
*   The default base address map of the SPI flash master is 0xF801_4000.
*   The default SCK frequency is half of the SoC system clock frequency.
*   The default base address of the UART is 0xF801_0000 with a default baud rate of 115200.
*
******************************************************************************/
#include <stdint.h>
#include "bsp.h"
#include "userDef.h"
#include "spi.h"
#include "spiFlash.h"



#define LEN 256   // Length to write/read from/to SPI Flash
#define SPI_CS 0 // Chip Select



/*******************************************************************************
*
* @brief This function initialize the spi configuration setting based on the following
*        parameters. 
*
* @param
* - cpol: Clock polarity (0 or 1).
* - cpha: Clock phase (0 or 1).
* - mode: SPI mode 
*      0: Full-duplex dual line
*      1: Half-duplex dual line
*          (Available only when data width is configured as 8 or 16)
*      2: Half-duplex quad line
*          (Available only when data width is configured as 8 or 16)
*
* - clkDivider: Clock divider value. SPI frequency = FCLK/((clockDivider+1)*2)
*               FCLK is the system clock (io_systemClk) to the SoC. If
*               you enable the peripheral clock, then FCLK is driven by
*               the peripheral clock (io_peripheralClk) instead.
*
* - ssSetup: Slave select setup time. Clock cycle between activated chip-select and first
*            rising-edge of SCLK. Clock cycle refers to FCLK.
*
* - ssHold: Slave select hold time. Clock cycle between last falling-edge and deactivated
*           chip-select is activated. Clock cycle refers to FCLK.
*           
* - ssDisable: Slave select disable time.
*
******************************************************************************/
void spiInit(){
    //SPI init
    Spi_Config spiA;
    spiA.cpol       = 1;
    spiA.cpha       = 1;
    spiA.mode       = 0; 
    spiA.clkDivider = 19;
    spiA.ssSetup    = 5;
    spiA.ssHold     = 5;
    spiA.ssDisable  = 5;
    spi_applyConfig(SPI, &spiA);
}



/**************************************l****************************************
*
* @brief This function is Writes LEN bytes of incrementing data to NOR Flash starting at the specified address.
*
******************************************************************************/
void spiWriteData_toFlash(u32 reg ,u32 cs, u32 addr){
    spiGlobalUnlock(reg,cs);
    spiSectorErase(reg,cs,addr);
    spiWriteEnable(reg,cs);
    spi_select(reg, 0);
    spi_write(reg, PAGE_PROGRAM_OP);
    spi_write(reg, (addr>>16) & 0xFF);
    spi_write(reg, (addr>>8) & 0xFF);
    spi_write(reg, addr & 0xFF);
    // Write dummy data
    for(int i=0; i<LEN; i++)
    {
        spi_write(reg, i & 0xFF );
        bsp_printf("Write address %x := %x \r\n", addr+i, i & 0xFF );
    }

    spi_diselect(reg, cs);
    // Wait for page writing done
    if (spiWaitBusy(reg,cs) == 1) bsp_printf("Timeout!\r\n");
    spiGlobalLock(reg,cs);
}



/**************************************l****************************************
*
* @brief This main function initializes the SPI interface, selects the SPI device,
*        writes to SPI flash starting from a specific address and for a specified LENgth.
*
******************************************************************************/
void main() {

    bsp_init();
    bsp_printf("***Starting SPI Demo*** \r\n");
    spiInit();
    bsp_printf("Device ID : %x \r\n", spiFlash_manufacturer_id(SPI,SPI_CS));
    bsp_printf("Writing data to flash .. \r\n");
    spiWriteData_toFlash(SPI,SPI_CS,FLASH_START_ADDR);

    bsp_printf("Reading from flash .. \r\n");
    for(int i=FLASH_START_ADDR;i< (FLASH_START_ADDR+LEN) ;i++)
    {
        bsp_printf("Read address %x := %x \r\n", i, spiReadData_fromFlash(SPI,SPI_CS,i));
    }

    bsp_printf("***Successfully Ran Demo*** \r\n");

}
