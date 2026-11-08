#ifndef MDIO_APB_MASTER_H
#define MDIO_APB_MASTER_H

#include <stdint.h>

#define MDIO_APB_BASE       0xf8101000
#define MDIO_APB_CTRL       0x00
#define MDIO_APB_STATUS     0x04
#define MDIO_APB_START      (1u << 0)
#define MDIO_APB_READ       (1u << 1)
#define MDIO_APB_BUSY       (1u << 0)
#define MDIO_APB_DONE       (1u << 1)

#define PHY_REG_BMCR        0x00
#define PHY_REG_BMSR        0x01
#define PHY_REG_PHYID1      0x02
#define PHY_REG_PHYID2      0x03
#define PHY_REG_ANAR        0x04
#define PHY_REG_ANLPAR      0x05
#define PHY_REG_GBCR        0x09
#define PHY_REG_GBSR        0x0A

static inline void mdio_apb_write(uint32_t offset, uint32_t value)
{
    volatile uint32_t *reg = (volatile uint32_t *)(MDIO_APB_BASE + offset);
    *reg = value;
}

static inline uint32_t mdio_apb_read(uint32_t offset)
{
    volatile uint32_t *reg = (volatile uint32_t *)(MDIO_APB_BASE + offset);
    return *reg;
}

static inline void mdio_init(void)
{
    mdio_apb_write(MDIO_APB_STATUS, MDIO_APB_DONE);
}

static inline int mdio_wait_done(void)
{
    for (uint32_t timeout = 0; timeout < 500000; timeout++) {
        if (mdio_apb_read(MDIO_APB_STATUS) & MDIO_APB_DONE)
            return 1;
    }
    return 0;
}

static inline uint16_t mdio_read(uint8_t phy_addr, uint8_t reg_addr)
{
    uint32_t command = MDIO_APB_START | MDIO_APB_READ |
        (((uint32_t)phy_addr & 0x1fu) << 5) |
        (((uint32_t)reg_addr & 0x1fu) << 10);
    mdio_apb_write(MDIO_APB_STATUS, MDIO_APB_DONE);
    mdio_apb_write(MDIO_APB_CTRL, command);
    if (!mdio_wait_done())
        return 0xffff;
    return (uint16_t)(mdio_apb_read(MDIO_APB_STATUS) >> 16);
}

static inline int mdio_write(uint8_t phy_addr, uint8_t reg_addr, uint16_t data)
{
    uint32_t command = MDIO_APB_START |
        (((uint32_t)phy_addr & 0x1fu) << 5) |
        (((uint32_t)reg_addr & 0x1fu) << 10) |
        ((uint32_t)data << 16);
    mdio_apb_write(MDIO_APB_STATUS, MDIO_APB_DONE);
    mdio_apb_write(MDIO_APB_CTRL, command);
    return mdio_wait_done();
}

#endif
