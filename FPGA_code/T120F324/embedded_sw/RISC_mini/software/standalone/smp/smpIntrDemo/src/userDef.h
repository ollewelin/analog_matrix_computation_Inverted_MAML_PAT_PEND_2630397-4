////////////////////////////////////////////////////////////////////////////////
// Copyright (C) 2013-2025 Efinix Inc. All rights reserved.
// Full license header bsp/efinix/EfxSapphireSoc/include/LICENSE.MD
////////////////////////////////////////////////////////////////////////////////

#pragma once

#define STACK_PER_HART 4096

#ifdef BSP_PLIC_CPU_3
#define HART_COUNT 4

#elif BSP_PLIC_CPU_2
#define HART_COUNT 3

#elif BSP_PLIC_CPU_1
#define HART_COUNT 2

#else
#define HART_COUNT 1

#endif

#define SYSTEM_PLIC_TIMER_INTERRUPTS_0  SYSTEM_PLIC_SYSTEM_USER_TIMER_0_INTERRUPTS_0
#define TIMER_0                     	SYSTEM_USER_TIMER_0_CTRL
#define SYSTEM_PLIC_TIMER_INTERRUPTS_1  SYSTEM_PLIC_SYSTEM_USER_TIMER_1_INTERRUPTS_0
#define TIMER_1                     	SYSTEM_USER_TIMER_1_CTRL
#define TIMER_0_PRESCALER_CTRL        	(TIMER_0 + 0x00)
#define TIMER_0_CTRL                    (TIMER_0 + 0x40)
#define TIMER_1_PRESCALER_CTRL        	(TIMER_1 + 0x00)
#define TIMER_1_CTRL                    (TIMER_1 + 0x40)
#define TIMER_CONFIG_WITH_PRESCALER     0x2
#define TIMER_CONFIG_WITHOUT_PRESCALER  0x1
#define TIMER_CONFIG_SELF_RESTART       0x10000
#define TIMER_TICK_DELAY            	(BSP_CLINT_HZ)


