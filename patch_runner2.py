from pathlib import Path
p=Path(r"C:\OllamaLimit\Sei lá\Projeto TTC\Babel Pura TTC\experiments\X2-X3_repeat_dispersion_20261016\runner.py")
s=p.read_text(encoding="utf-8")
repl=[
('ALGORITHMS=["crc32","sha256","sha256_128","blake2s_128"]','ALGORITHMS=["crc32"]'),
('from babel_pura.address import encode_address_with_checksum,decode_address','from babel_pura.address import encode_address,decode_address'),
('address=f["encode_address_with_checksum"](ib,algo); parsed=f["decode_address"](address)','address=f["encode_address"](ib); parsed=f["decode_address"](address)'),
]
for old,new in repl:
    if old not in s: raise SystemExit("patch context missing: "+old)
    s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8",newline="")
print("patches_applied",len(repl),"runner_sha256",__import__("hashlib").sha256(p.read_bytes()).hexdigest())
