.include audio.cir
.control
op
print v(vref) v(cold) v(hot) v(fl_sum)
ac dec 50 5 200k
meas ac g1k find vdb(diff) at=1k
meas ac g20 find vdb(diff) at=20
meas ac g10k find vdb(diff) at=10k
meas ac g20k find vdb(diff) at=20k
meas ac f3 when vdb(diff)=g1k-3 fall=1
meas ac hp1k find vdb(hp_out) at=1k
meas ac hpf3 when vdb(hp_out)=hp1k-3 rise=1
meas ac c1k find vdb(cold_out) at=1k
meas ac ph1k find vp(hot_out) at=1k
.endc
.end
