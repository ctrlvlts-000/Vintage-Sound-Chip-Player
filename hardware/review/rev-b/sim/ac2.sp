.include audio.cir
.control
ac dec 50 5 200k
let d=vdb(diff)-vdb(diff)[0]
foreach f 20 100 1000 2000 3390 5000 10000 15000 20000
 meas ac x find d at=$f
end
meas ac f3 when d=-3
meas ac hpref find vdb(hp_out) at=1k
let h=vdb(hp_out)
meas ac hlo when h=-6.2 rise=1
.endc
.end
