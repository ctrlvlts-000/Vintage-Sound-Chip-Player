* VBUS ripple -> VA_IN (LDO input) ; and +5V_YM -> YM_AVCC
VB vb 0 DC 5 AC 1
* FB2 BLM18PG221SN1: ~0.05 ohm DCR, ~0.5uH low-freq inductance (rough)
Rfb vb a 0.05
Lfb a raw 0.5u
* L1 LQH32CN100K53L: 10uH, DCR ~0.3 ohm
Rl1 raw b 0.3
L1 b va 10u
* C4 22uF X5R 0805 10V at 5V bias -> ~9uF effective, ESR 5m
C4 va c4n 9u
Rc4 c4n 0 5m
* C5 47uF 16V elec 5x5.4: ESR ~0.6 ohm (assumed, general-purpose)
C5 va c5n 47u
Rc5 c5n 0 0.03
* LDO quiescent+load ~ 30 mA as resistor
Rld va 0 1k
* A.VCC filter
VY y 0 DC 5 AC 1
R21 y av 10
C15 av c15n 220u
Rc15 c15n 0 0.3
C16 av 0 100n
Ryma av 0 1k
.control
op
print v(va) v(av)
ac dec 100 10 1Meg
let g=vdb(va)
meas ac peak max g
meas ac fpk when g=peak
foreach f 100 1000 10000 20000 100000 1000000
 meas ac x find g at=$f
end
let ga=vdb(av)
foreach f 100 1000 10000
 meas ac y find ga at=$f
end
.endc
.end
