.include audio.cir
.control
foreach a 0.3 0.5 0.7 0.8 0.9 1.0 1.2
 alter @VMOL[sin] = [ 2.0 $a 1k ]
 tran 2u 30m 20m
 meas tran hmax max v(hot)
 meas tran hmin min v(hot)
 meas tran dpp pp v(diff)
 fourier 1k v(diff)
end
.endc
.end
