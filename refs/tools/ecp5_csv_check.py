import csv,json,sys,collections,re
rows=[r for r in csv.reader(open(sys.argv[1])) if r and r[0] and not r[0].startswith("#")]
hdr=rows[0]; rows=[dict(zip(hdr,r)) for r in rows[1:]]
bg=[r for r in rows if r.get("CABGA256","-") not in ("-","")]
balls=collections.defaultdict(list)
for r in bg: balls[r["CABGA256"]].append(r)
print("rows with a CABGA256 ball:",len(bg),"distinct balls:",len(balls))
io={b:v[0] for b,v in balls.items() if re.match(r"P[LRTB]\d+[A-D]$",v[0]["Pin/Ball Function"])}
nonio={b:v for b,v in balls.items() if b not in io}
print("IO balls:",len(io)," non-IO balls:",len(nonio))
d=json.load(open(sys.argv[2])); pk=d["packages"]["CABGA256"]
meta={(m["col"],m["row"],m["pio"]):m for m in d["pio_metadata"]}
tb={b:meta[(v["col"],v["row"],v["pio"])] for b,v in pk.items()}
print("trellis IO balls:",len(tb)," same set:",set(tb)==set(io))
print("bank mismatches:",[(b,io[b]["Bank"],tb[b]["bank"]) for b in io if b in tb and str(tb[b]["bank"])!=io[b]["Bank"]][:10])
mis=[]
for b in io:
    lf=io[b]["Dual Function"]; t=tb.get(b,{}).get("function","")
    for key in ("PCLKT","PCLKC","GPLL"):
        if (key in lf)!=(key in t): mis.append((b,lf,t))
print("clock-function mismatches:",mis[:10])
for b in ("K1","K16","M1","R8","T8","T7","M7","N7","B1","B2"): print("  ",b,io[b]["Pin/Ball Function"],"bank",io[b]["Bank"],"dual:",io[b]["Dual Function"])
fc=collections.Counter(re.sub(r"\d+$","",v[0]["Pin/Ball Function"]) for v in nonio.values())
print("non-IO function counts:",dict(fc))
for b,v in sorted(nonio.items()):
    f=v[0]["Pin/Ball Function"]
    if not re.match(r"(VCC|GND|VSS)",f) or len(v)>1: print("   ",b,[x["Pin/Ball Function"] for x in v],v[0]["Bank"])
json.dump({"io":{b:[r["Pin/Ball Function"],r["Bank"],r["Dual Function"]] for b,r in io.items()},
           "nonio":{b:[x["Pin/Ball Function"] for x in v] for b,v in nonio.items()}},open("ecp5_bg256.json","w"),indent=0)
