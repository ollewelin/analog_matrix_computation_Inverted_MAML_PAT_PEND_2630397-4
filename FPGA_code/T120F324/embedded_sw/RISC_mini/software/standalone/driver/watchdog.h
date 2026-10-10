///////////////////////////////////////////////////////////////////////////////////
//  Copyright (c) 2025 SaxonSoc contributors
//  SPDX license identifier: MIT
//  Full license header bsp/efinix/EfxSapphireSoc/include/LICENSE.MD
//////////////////////////////////////////////////////////////////////////////////

#pragma once

#include "type.h"
#include "io.h"

#define WATCHDOG_HEARTBEAT   0x0
#define WATCHDOG_ENABLE      0x4
#define WATCHDOG_DISABLE     0x8
#define WATCHDOG_PRESCALER  0x40
#define WATCHDOG_COUNTER_LIMIT 0x80
#define WATCHDOG_COUNTER_VALUE 0xC0

#define WATCHDOG_HEARTBEAT_CHALLENGE 0xAD68E70D
#define WATCHDOG_UNLOCK_CHALLENGE 0x3C21B925
#define WATCHDOG_LOCK_CHALLENGE 0x3C21B924


writeReg_u32(watchdog_setPrescaler , WATCHDOG_PRESCALER)

void watchdog_setCounterLimit(u32 reg, u32 counterId, u32 value){
    write_u32(value, reg + WATCHDOG_COUNTER_LIMIT + counterId * 4);
}

u32 watchdog_getCounterValue(u32 reg, u32 counterId, u32 value){
    return read_u32(reg + WATCHDOG_COUNTER_VALUE + counterId * 4);
}

void watchdog_heartbeat(u32 reg){
    write_u32(WATCHDOG_HEARTBEAT_CHALLENGE, reg + WATCHDOG_HEARTBEAT);
}

void watchdog_unlock(u32 reg){
    write_u32(WATCHDOG_UNLOCK_CHALLENGE, reg + WATCHDOG_HEARTBEAT);
}

void watchdog_lock(u32 reg){
    write_u32(WATCHDOG_LOCK_CHALLENGE, reg + WATCHDOG_HEARTBEAT);
}

void watchdog_enable(u32 reg, u32 mask){
    write_u32(mask, reg + WATCHDOG_ENABLE);
}

void watchdog_disable(u32 reg, u32 mask){
    write_u32(mask, reg + WATCHDOG_DISABLE);
}
