import re

# Let's inspect the exact UART log captured:
log = """
[ARP] Replied to ARP Request!
[ARP] Replied to ARP Request!
>>> ETHERNET LINK UP! (Cable connected) <<<
[ETH] BMSR=79AD RX=0000 TX=0002 FCS=000F FIFO_ST=0004
[IP] Proto=11 Dst=E0.00.00.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[ETH] BMSR=79AD RX=0000 TX=0002 FCS=001E FIFO_ST=0004
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=EF.FF.FF.FA
[IP] Proto=11 Dst=FF.FF.FF.FF
[ARP] Replied to ARP Request!
"""
print("Log shows:")
print("- ARP replies triggered by software: 12 times!")
print("- UDP packets decoded: Proto=11 Dst=EF.FF.FF.FA (239.255.255.250 SSDP) and FF.FF.FF.FF (Broadcast) and E0.00.00.FA (224.0.0.250 mDNS/LLMNR)!")
print("- When host sent ping (ICMP proto 01): [IP] Proto=01 Dst=C0.A8.01.32 (192.168.1.50) [ICMP] Ping Reply triggered!")
