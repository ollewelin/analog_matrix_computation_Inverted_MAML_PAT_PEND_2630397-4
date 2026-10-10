#include "soc.h"
#include "bsp.h"

#if defined(SYSTEM_PLIC_SYSTEM_CORES_1_EXTERNAL_INTERRUPT) &&\
	defined(SYSTEM_USER_TIMER_0_CTRL) &&\
	defined(SYSTEM_USER_TIMER_1_CTRL)

#include "userDef.h"
#include "riscv.h"
#include "start.h"
#include "plic.h"
#include "timer.h"
#include "prescaler.h"

u8 hartStack[STACK_PER_HART*HART_COUNT] __attribute__((aligned(16)));

void 		trap();
void 		crash();
void 		trap_entry();
void		externalInterrupt();
void 		isrRoutine();
extern void smpInit();

volatile u32 hartCounter = 0;
volatile u32 uart_occupied = 0;

__inline__ __attribute__((always_inline)) s32 atomicAdd(s32 *a, u32 increment) {
    s32 old;
    __asm__ volatile(
          "amoadd.w %[old], %[increment], (%[atomic])"
        : [old] "=r"(old)
        : [increment] "r"(increment), [atomic] "r"(a)
        : "memory"
    );
    return old;
}

void timer_init(){
    //set timer 1 trigger every 2.2s
    prescaler_setValue(TIMER_0_PRESCALER_CTRL, 9999);
    timer_setLimit(TIMER_0_CTRL, 22000);
    timer_setConfig(TIMER_0_CTRL, TIMER_CONFIG_WITH_PRESCALER | TIMER_CONFIG_SELF_RESTART);

    // set timer 1 to trigger every 4.7s
    prescaler_setValue(TIMER_1_PRESCALER_CTRL, 9999);
    timer_setLimit(TIMER_1_CTRL, 47000);
    timer_setConfig(TIMER_1_CTRL, TIMER_CONFIG_WITH_PRESCALER | TIMER_CONFIG_SELF_RESTART);
}

void plic_init(){
	//set all cores to accept all interupts of priority above 0
	plic_set_threshold(BSP_PLIC, BSP_PLIC_CPU_0, 0);
	plic_set_threshold(BSP_PLIC, BSP_PLIC_CPU_1, 0);

#ifdef BSP_PLIC_CPU_2
	plic_set_threshold(BSP_PLIC, BSP_PLIC_CPU_2, 0);
#endif

#ifdef BSP_PLIC_CPU_3
	plic_set_threshold(BSP_PLIC, BSP_PLIC_CPU_3, 0);
#endif

	//set core 0 and core 1 to entertain interrupt from user timers
	plic_set_enable(BSP_PLIC, BSP_PLIC_CPU_0, SYSTEM_PLIC_TIMER_INTERRUPTS_0, 1);
	plic_set_priority(BSP_PLIC, SYSTEM_PLIC_TIMER_INTERRUPTS_0, 1);
	plic_set_enable(BSP_PLIC, BSP_PLIC_CPU_1, SYSTEM_PLIC_TIMER_INTERRUPTS_1, 1);
	plic_set_priority(BSP_PLIC, SYSTEM_PLIC_TIMER_INTERRUPTS_1, 1);
}

void timer0Isr(){
	while(uart_occupied == 1);
	uart_occupied = 1;
    bsp_printf("c0 isr .. \r\n");
    uart_occupied = 0;
}

void timer1Isr(){
	while(uart_occupied == 1);
	uart_occupied = 1;
    bsp_printf("c1 isr .. \r\n");
    uart_occupied = 0;
}

void crash(){
    bsp_printf("\r\n*** CRASH ***\r\n");
    while(1);
}


void isrInit(){
	//enable interrupts
    //Set the machine trap vector (../common/trap.S)
    csr_write(mtvec, trap_entry);
    //Enable external interrupts
    csr_set(mie, MIE_MEIE);
    csr_write(mstatus, MSTATUS_MPP | MSTATUS_MIE | MSTATUS_FS);
}

void trap(){
    int32_t mcause = csr_read(mcause);
    // Interrupt if true, exception if false
    int32_t interrupt = mcause < 0;
    int32_t cause     = mcause & 0xF;
    if(interrupt){
        switch(cause){
        case CAUSE_MACHINE_EXTERNAL: isrRoutine(); break;
        default: crash(); break;
        }
    } else {
        crash();
    }
}

void isrRoutine(){
    uint32_t claim;
    // While there is pending interrupts
    if (csr_read(mhartid) == 0x0){
    	while(claim = plic_claim(BSP_PLIC, BSP_PLIC_CPU_0)){
    		switch(claim){
    		case SYSTEM_PLIC_TIMER_INTERRUPTS_0:  timer0Isr(); break;
    		default: crash(); break;
    		}
    		// Unmask the claimed interrupt
    		plic_release(BSP_PLIC, BSP_PLIC_CPU_0, claim);
    	}
    }
    else if (csr_read(mhartid) == 0x1){
    	while(claim = plic_claim(BSP_PLIC, BSP_PLIC_CPU_1)){
    		switch(claim){
    		case SYSTEM_PLIC_TIMER_INTERRUPTS_1:  timer1Isr(); break;
    		default: crash(); break;
    		}
    		// Unmask the claimed interrupt
    		plic_release(BSP_PLIC, BSP_PLIC_CPU_1, claim);
    	}
    }
}

void mainSmp(){
	//this routine run by all cores
	u32 hartId = csr_read(mhartid);
	//each core register the interrupt trap
	isrInit();
	atomicAdd((s32*)&hartCounter, 1);

	while(hartCounter != HART_COUNT);
	 if(hartId == 0) {
		 bsp_printf("smp init done .. \r\n");

		 while(1);
	 }
	 else if(hartId == 1){
		 while(1);
	 }
	 else if(hartId == 2){
		 while(1);
	 }
	 else if(hartId == 3){
		 while(1);
	 }

}

void main(){
	//this routine run by core 0
	bsp_init();
	timer_init();
	plic_init();
	//timer_init();
	bsp_printf("***Starting SMP Interrupt Demo*** \r\n");
	smp_unlock(smpInit);
	mainSmp();
}

#else

#define STACK_PER_HART 4096
#define HART_COUNT 4
u8 hartStack[STACK_PER_HART*HART_COUNT];

void trap(){

}

void mainSmp(){

}

void main(){
	bsp_printf("Unable to perform smpIntrDemo. Please enable the following modules in SapphireSoc:\r\n");
	bsp_printf("- At least 2 CPU cores \r\n");
	bsp_printf("- User Timer 0 with 32-bit counter width and 16-bit prescaler width \r\n");
	bsp_printf("- User Timer 1 with 32-bit counter width and 16-bit prescaler width \r\n");
	while(1);
}

#endif
