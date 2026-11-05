#pragma once
#include "soc.h"

#ifdef SYSTEM_GPIO_0_IO_CTRL
    #define GPIO0   SYSTEM_GPIO_0_IO_CTRL
#endif

#define DEBUG_PRINTF_EN     1
#define TSEMAC_BASE         0xF8102000
#define TSEMAC_DMASG_BASE   0xF8102000
#define TSE_DMASG_RX_CH     0
#define TSE_DMASG_TX_CH     1

#define TX_ENA_MASK    		0xFFFFFFFE
#define RX_ENA_MASK    		0xFFFFFFFD
#define XON_GEN_MASK 		0xFFFFFFFB
#define PROMIS_EN_MASK   	0xFFFFFFEF
#define PAD_EN_MASK   		0xFFFFFFDF
#define CRC_FWD_MASK   		0xFFFFFFBF
#define PAUSE_IGNORE_MASK   0xFFFFFEFF
#define TX_ADDR_INS_MASK   	0xFFFFFBFF
#define LOOP_ENA_MASK   	0xFFFF7FFF
#define ETH_SPEED_MASK   	0xFFF8FFFF
#define XOFF_GEN_MASK 		0xFFBFFFFF
#define CNT_RST_MASK 		0x7FFFFFFF

#define DST_MAC_H 	        0xffff
#define DST_MAC_L 	        0xffffffff
#define SRC_MAC_H 	        0xeae8
#define SRC_MAC_L 	        0x5e0060c8

#define PHY_ADDR            0x0

#ifdef SIM
    #define LOOP_UDELAY 100
#else
    #define LOOP_UDELAY 100000
#endif
