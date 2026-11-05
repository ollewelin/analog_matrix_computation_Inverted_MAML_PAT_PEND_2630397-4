#ifndef LWIP_LWIPOPTS_H
#define LWIP_LWIPOPTS_H

#define NO_SYS                     1
#define LWIP_SOCKET                0
#define LWIP_NETCONN               0
#define LWIP_NETIF_API             0

#define LWIP_IPV4                  1
#define LWIP_IPV6                  0

#define LWIP_ARP                   1
#define ARP_TABLE_SIZE             4
#define ARP_QUEUEING               0

#define LWIP_IP                    1
#define IP_FORWARD                 0
#define IP_REASSEMBLY              0
#define IP_FRAG                    0

#define LWIP_ICMP                  1
#define ICMP_TTL                   255

#define LWIP_RAW                   0
#define LWIP_DHCP                  0
#define LWIP_AUTOIP                0
#define LWIP_IGMP                  0
#define LWIP_DNS                   0
#define LWIP_UDP                   0

#define PPP_SUPPORT                0

/* TCP Configuration */
#define LWIP_TCP                   1
#define TCP_TTL                    255
#define LWIP_ALTCP                 0
#define TCP_QUEUE_OOSEQ            0
#define TCP_MSS                    1460
#define TCP_WND                    (2 * TCP_MSS)
#define TCP_SND_BUF                (2 * TCP_MSS)
#define TCP_SND_QUEUELEN           16
#define TCP_SNDLOWAT               (TCP_SND_BUF / 2)
#define TCP_SNDQUEUELOWAT          (TCP_SND_QUEUELEN / 2)
#define TCP_LISTEN_BACKLOG         0

/* Memory options tuned for 128 KB on-chip BRAM */
#define MEM_ALIGNMENT              4U
#define MEM_SIZE                   (8 * 1024)

#define MEMP_NUM_PBUF              8
#define MEMP_NUM_RAW_PCB           0
#define MEMP_NUM_UDP_PCB           0
#define MEMP_NUM_TCP_PCB           2
#define MEMP_NUM_TCP_PCB_LISTEN    2
#define MEMP_NUM_TCP_SEG           16
#define MEMP_NUM_SYS_TIMEOUT       8
#define MEMP_NUM_NETBUF            0
#define MEMP_NUM_NETCONN           0
#define MEMP_NUM_TCPIP_MSG_API     0
#define MEMP_NUM_TCPIP_MSG_INPKT   0

/* Pbuf options */
#define PBUF_POOL_SIZE             8
#define PBUF_POOL_BUFSIZE          512

#define SYS_LIGHTWEIGHT_PROT       0
#define LWIP_STATS                 0

/* Checksum options */
#define CHECKSUM_GEN_IP            1
#define CHECKSUM_GEN_UDP           0
#define CHECKSUM_GEN_TCP           1
#define CHECKSUM_GEN_ICMP          1
#define CHECKSUM_CHECK_IP          1
#define CHECKSUM_CHECK_UDP         0
#define CHECKSUM_CHECK_TCP         1
#define CHECKSUM_CHECK_ICMP        1

#define LWIP_DISABLE_TCP_SANITY_CHECKS 1

#endif /* LWIP_LWIPOPTS_H */
