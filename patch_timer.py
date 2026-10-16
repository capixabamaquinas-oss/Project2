from pathlib import Path
p=Path(r"C:\OllamaLimit\Sei lá\Projeto TTC\Babel Pura TTC\experiments\X2-X3_repeat_dispersion_20261016\runner.py")
s=p.read_text(encoding="utf-8")
old='        restored=f["decode_h1_integer"](int.from_bytes(parsed,"big")); actual=hashlib.sha256(restored).hexdigest()\n        elapsed=(time.perf_counter()-t)*1000; mem=peak_ws(); expected=m["cases"][case]["data_sha256"]'
new='        restored=f["decode_h1_integer"](int.from_bytes(parsed,"big"))\n        elapsed=(time.perf_counter()-t)*1000; mem=peak_ws(); actual=hashlib.sha256(restored).hexdigest(); expected=m["cases"][case]["data_sha256"]'
if old not in s: raise SystemExit("roundtrip timer patch context missing")
p.write_text(s.replace(old,new,1),encoding="utf-8",newline="")
print("patched full-path hash outside timer; runner_sha256",__import__("hashlib").sha256(p.read_bytes()).hexdigest())
