from pathlib import Path
p=Path(r"C:\OllamaLimit\Sei lá\Projeto TTC\Babel Pura TTC\experiments\X2-X3_repeat_dispersion_20261016\runner.py")
s=p.read_text(encoding="utf-8")
changes=[
('    t=time.perf_counter()\n    if op=="encode":','    data=src.read_bytes() if op=="roundtrip" else None\n    t=time.perf_counter()\n    if op=="encode":'),
('    elif op=="roundtrip":\n        data=src.read_bytes(); value=f["encode_h1_integer"](data); ib=f["integer_minimal_bytes"](value)','    elif op=="roundtrip":\n        value=f["encode_h1_integer"](data); ib=f["integer_minimal_bytes"](value)'),
('    t=time.perf_counter()\n    if metric=="baseline":\n        data=(FIX/"x3_4m.bin").read_bytes(); value=f["encode_h1_integer"](data); minimal=f["integer_minimal_bytes"](value); text=minimal.hex()','    if metric=="baseline":\n        data=(FIX/"x3_4m.bin").read_bytes(); t=time.perf_counter(); value=f["encode_h1_integer"](data); minimal=f["integer_minimal_bytes"](value); text=minimal.hex()'),
('        raw=p.read_bytes(); value=binascii.crc32(raw)&0xffffffff; elapsed=(time.perf_counter()-t)*1000; mem=peak_ws()','        raw=p.read_bytes(); t=time.perf_counter(); value=binascii.crc32(raw)&0xffffffff; elapsed=(time.perf_counter()-t)*1000; mem=peak_ws()'),
]
for old,new in changes:
    if old not in s:
        raise SystemExit("patch context missing: "+old[:70])
    s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8",newline="")
print("patches_applied",len(changes),"runner_sha256",__import__("hashlib").sha256(p.read_bytes()).hexdigest())
