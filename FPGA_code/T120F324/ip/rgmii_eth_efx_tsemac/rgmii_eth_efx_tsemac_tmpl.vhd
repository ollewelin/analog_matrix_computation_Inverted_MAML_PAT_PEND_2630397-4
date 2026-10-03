--------------------------------------------------------------------------------
-- Copyright (C) 2013-2025 Efinix Inc. All rights reserved.              
--
-- This   document  contains  proprietary information  which   is        
-- protected by  copyright. All rights  are reserved.  This notice       
-- refers to original work by Efinix, Inc. which may be derivitive       
-- of other work distributed under license of the authors.  In the       
-- case of derivative work, nothing in this notice overrides the         
-- original author's license agreement.  Where applicable, the           
-- original license agreement is included in it's original               
-- unmodified form immediately below this header.                        
--                                                                       
-- WARRANTY DISCLAIMER.                                                  
--     THE  DESIGN, CODE, OR INFORMATION ARE PROVIDED “AS IS” AND        
--     EFINIX MAKES NO WARRANTIES, EXPRESS OR IMPLIED WITH               
--     RESPECT THERETO, AND EXPRESSLY DISCLAIMS ANY IMPLIED WARRANTIES,  
--     INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTIES OF          
--     MERCHANTABILITY, NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR    
--     PURPOSE.  SOME STATES DO NOT ALLOW EXCLUSIONS OF AN IMPLIED       
--     WARRANTY, SO THIS DISCLAIMER MAY NOT APPLY TO LICENSEE.           
--                                                                       
-- LIMITATION OF LIABILITY.                                              
--     NOTWITHSTANDING ANYTHING TO THE CONTRARY, EXCEPT FOR BODILY       
--     INJURY, EFINIX SHALL NOT BE LIABLE WITH RESPECT TO ANY SUBJECT    
--     MATTER OF THIS AGREEMENT UNDER TORT, CONTRACT, STRICT LIABILITY   
--     OR ANY OTHER LEGAL OR EQUITABLE THEORY (I) FOR ANY INDIRECT,      
--     SPECIAL, INCIDENTAL, EXEMPLARY OR CONSEQUENTIAL DAMAGES OF ANY    
--     CHARACTER INCLUDING, WITHOUT LIMITATION, DAMAGES FOR LOSS OF      
--     GOODWILL, DATA OR PROFIT, WORK STOPPAGE, OR COMPUTER FAILURE OR   
--     MALFUNCTION, OR IN ANY EVENT (II) FOR ANY AMOUNT IN EXCESS, IN    
--     THE AGGREGATE, OF THE FEE PAID BY LICENSEE TO EFINIX HEREUNDER    
--     (OR, IF THE FEE HAS BEEN WAIVED, $100), EVEN IF EFINIX SHALL HAVE 
--     BEEN INFORMED OF THE POSSIBILITY OF SUCH DAMAGES.  SOME STATES DO 
--     NOT ALLOW THE EXCLUSION OR LIMITATION OF INCIDENTAL OR            
--     CONSEQUENTIAL DAMAGES, SO THIS LIMITATION AND EXCLUSION MAY NOT   
--     APPLY TO LICENSEE.                                                
--
--------------------------------------------------------------------------------
------------- Begin Cut here for COMPONENT Declaration ------
component rgmii_eth_efx_tsemac is
port (
    mac_reset : in std_logic;
    proto_reset : in std_logic;
    s_axi_araddr : in std_logic_vector(9 downto 0);
    s_axi_rresp : out std_logic_vector(1 downto 0);
    rx_mac_aclk : out std_logic;
    tx_mac_aclk : in std_logic;
    eth_speed : out std_logic_vector(2 downto 0);
    MdoEn : out std_logic;
    rx_axis_clk : in std_logic;
    rx_axis_mac_tuser : out std_logic;
    Mdc : out std_logic;
    rx_axis_mac_tlast : out std_logic;
    Mdi : in std_logic;
    rx_axis_mac_tvalid : out std_logic;
    s_axi_rvalid : out std_logic;
    s_axi_arready : out std_logic;
    rx_axis_mac_tready : in std_logic;
    s_axi_rdata : out std_logic_vector(31 downto 0);
    tx_axis_clk : in std_logic;
    tx_axis_mac_tvalid : in std_logic;
    s_axi_bvalid : out std_logic;
    s_axi_wready : out std_logic;
    s_axi_rready : in std_logic;
    tx_axis_mac_tlast : in std_logic;
    Mdo : out std_logic;
    tx_axis_mac_tuser : in std_logic;
    s_axi_wdata : in std_logic_vector(31 downto 0);
    tx_axis_mac_tready : out std_logic;
    rgmii_txd_HI : out std_logic_vector(3 downto 0);
    rgmii_txd_LO : out std_logic_vector(3 downto 0);
    rgmii_tx_ctl_HI : out std_logic;
    rgmii_tx_ctl_LO : out std_logic;
    rgmii_txc_HI : out std_logic;
    rgmii_txc_LO : out std_logic;
    rgmii_rxd_HI : in std_logic_vector(3 downto 0);
    rgmii_rxd_LO : in std_logic_vector(3 downto 0);
    rgmii_rx_ctl_HI : in std_logic;
    rgmii_rx_ctl_LO : in std_logic;
    rgmii_rxc : in std_logic;
    s_axi_aclk : in std_logic;
    s_axi_bready : in std_logic;
    s_axi_awaddr : in std_logic_vector(9 downto 0);
    s_axi_arvalid : in std_logic;
    s_axi_awvalid : in std_logic;
    s_axi_awready : out std_logic;
    s_axi_wvalid : in std_logic;
    rx_axis_mac_tdata : out std_logic_vector(7 downto 0);
    tx_axis_mac_tdata : in std_logic_vector(7 downto 0);
    tx_axis_mac_tstrb : in std_logic_vector(0 to 0);
    rx_axis_mac_tstrb : out std_logic_vector(0 to 0);
    s_axi_bresp : out std_logic_vector(1 downto 0)
);
end component rgmii_eth_efx_tsemac;

---------------------- End COMPONENT Declaration ------------
------------- Begin Cut here for INSTANTIATION Template -----
u_rgmii_eth_efx_tsemac : rgmii_eth_efx_tsemac
port map (
    mac_reset => mac_reset,
    proto_reset => proto_reset,
    s_axi_araddr => s_axi_araddr,
    s_axi_rresp => s_axi_rresp,
    rx_mac_aclk => rx_mac_aclk,
    tx_mac_aclk => tx_mac_aclk,
    eth_speed => eth_speed,
    MdoEn => MdoEn,
    rx_axis_clk => rx_axis_clk,
    rx_axis_mac_tuser => rx_axis_mac_tuser,
    Mdc => Mdc,
    rx_axis_mac_tlast => rx_axis_mac_tlast,
    Mdi => Mdi,
    rx_axis_mac_tvalid => rx_axis_mac_tvalid,
    s_axi_rvalid => s_axi_rvalid,
    s_axi_arready => s_axi_arready,
    rx_axis_mac_tready => rx_axis_mac_tready,
    s_axi_rdata => s_axi_rdata,
    tx_axis_clk => tx_axis_clk,
    tx_axis_mac_tvalid => tx_axis_mac_tvalid,
    s_axi_bvalid => s_axi_bvalid,
    s_axi_wready => s_axi_wready,
    s_axi_rready => s_axi_rready,
    tx_axis_mac_tlast => tx_axis_mac_tlast,
    Mdo => Mdo,
    tx_axis_mac_tuser => tx_axis_mac_tuser,
    s_axi_wdata => s_axi_wdata,
    tx_axis_mac_tready => tx_axis_mac_tready,
    rgmii_txd_HI => rgmii_txd_HI,
    rgmii_txd_LO => rgmii_txd_LO,
    rgmii_tx_ctl_HI => rgmii_tx_ctl_HI,
    rgmii_tx_ctl_LO => rgmii_tx_ctl_LO,
    rgmii_txc_HI => rgmii_txc_HI,
    rgmii_txc_LO => rgmii_txc_LO,
    rgmii_rxd_HI => rgmii_rxd_HI,
    rgmii_rxd_LO => rgmii_rxd_LO,
    rgmii_rx_ctl_HI => rgmii_rx_ctl_HI,
    rgmii_rx_ctl_LO => rgmii_rx_ctl_LO,
    rgmii_rxc => rgmii_rxc,
    s_axi_aclk => s_axi_aclk,
    s_axi_bready => s_axi_bready,
    s_axi_awaddr => s_axi_awaddr,
    s_axi_arvalid => s_axi_arvalid,
    s_axi_awvalid => s_axi_awvalid,
    s_axi_awready => s_axi_awready,
    s_axi_wvalid => s_axi_wvalid,
    rx_axis_mac_tdata => rx_axis_mac_tdata,
    tx_axis_mac_tdata => tx_axis_mac_tdata,
    tx_axis_mac_tstrb => tx_axis_mac_tstrb,
    rx_axis_mac_tstrb => rx_axis_mac_tstrb,
    s_axi_bresp => s_axi_bresp
);

------------------------ End INSTANTIATION Template ---------
