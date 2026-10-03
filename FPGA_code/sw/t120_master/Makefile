PROJ_NAME = t120_master

STANDALONE = ./software
BSP_PATH = ./bsp/efinix/EfxSapphireSoc

SRCS = src/main.c \
       ${STANDALONE}/common/start_minimal.S

CFLAGS += -Iinclude \
          -I${BSP_PATH}/include \
          -I${BSP_PATH}/app \
          -I${STANDALONE}/include \
          -I${STANDALONE}/driver

include ${BSP_PATH}/include/soc.mk
include ${STANDALONE}/common/riscv64-unknown-elf.mk
include ${STANDALONE}/common/standalone.mk

LDSCRIPT = ${BSP_PATH}/linker/default.ld
