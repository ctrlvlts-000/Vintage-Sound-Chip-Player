.include thump.cir
.control
tran 1m 4
foreach t 0.2 0.5 1 1.5 2 3
 meas tran v find v(hp_in) at=$t
 meas tran d find v(diff) at=$t
end
.endc
.end
