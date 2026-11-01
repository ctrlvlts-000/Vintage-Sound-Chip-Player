.include thump.cir
.control
tran 100u 4
meas tran hp max v(hot_out)
meas tran hn min v(hot_out)
meas tran cp max v(cold_out)
meas tran cn min v(cold_out)
meas tran dp max v(diff)
meas tran dn min v(diff)
meas tran hpp max v(hp_in)
meas tran hpn min v(hp_in)
.endc
.end
