* simple OPA2350-like opamp: GBW 38MHz, rail-to-rail output (clamped 0.05V from rails), en 5nV/rtHz via 1.5k resistor at + input
.subckt OPA inp inn out vp vn
Rn inp inp2 1.5k
Rin inp2 inn 10Meg
G1 0 n1 inp2 inn 1m
R1 n1 0 1e8
C1 n1 0 4.19e-12
* gain = 1e5, pole at 1e8*4.19e-12 -> f=38Hz -> GBW 3.8MHz*... adjust below
E2 n2 0 n1 0 1
Bout out 0 V = min(max(v(n2), v(vn)+0.05), v(vp)-0.05)
.ends
