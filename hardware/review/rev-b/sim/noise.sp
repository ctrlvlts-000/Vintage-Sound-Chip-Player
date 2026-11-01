.include audio.cir
.control
noise v(hot_out,cold_out) VMOL dec 50 20 20k
setplot noise2
print onoise_total
setplot noise1
noise v(hp_out) VMOL dec 50 20 20k
setplot noise4
print onoise_total
.endc
.end
