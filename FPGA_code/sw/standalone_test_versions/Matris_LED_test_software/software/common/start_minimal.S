    .section .init
    .globl _start
    .type _start,@function

_start:
    /* Set stack pointer to top of 128KB BRAM */
    lui  sp, 0xF9020
    addi sp, sp, -16

    /* Jump directly to main */
    j    main

    .globl _init
_init:
    ret
