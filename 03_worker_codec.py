import argparse, ctypes, hashlib, json, sys, time
from ctypes import wintypes
from pathlib import Path

class PMC(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
    ]

def memory():
    counters = PMC(); counters.cb = ctypes.sizeof(PMC)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    get_info = psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    ok = get_info(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    if not ok: raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set_bytes': int(counters.WorkingSetSize), 'peak_working_set_bytes': int(counters.PeakWorkingSetSize), 'commit_bytes': int(counters.PagefileUsage), 'peak_commit_bytes': int(counters.PeakPagefileUsage)}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser()
p.add_argument('--package-root',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--method',required=True,choices=['monolithic','segmented_reverse','segmented_two_pass']); p.add_argument('--chunk-size',type=int,default=65536)
a=p.parse_args()
sys.dont_write_bytecode=True
sys.path.insert(0,a.package_root)
from babel_pura import codec
source=Path(a.source); output=Path(a.output)
source_hash=sha(source); before=memory(); t0=time.perf_counter()
if a.method=='monolithic': codec.encode_monolithic_file(source,output)
elif a.method=='segmented_reverse': codec.encode_segmented_reverse(source,output,a.chunk_size)
else: codec.encode_segmented_two_pass(source,output,a.chunk_size)
elapsed=time.perf_counter()-t0
after=memory()
print(json.dumps({'method':a.method,'chunk_size':None if a.method=='monolithic' else a.chunk_size,'input_bytes':source.stat().st_size,'input_sha256':source_hash,'output_bytes':output.stat().st_size,'output_sha256':sha(output),'elapsed_seconds':elapsed,'baseline_working_set_bytes':before['working_set_bytes'],'peak_working_set_bytes':after['peak_working_set_bytes'],'peak_working_set_delta_bytes':max(0,after['peak_working_set_bytes']-before['working_set_bytes']),'peak_commit_bytes':after['peak_commit_bytes'],'peak_commit_delta_bytes':max(0,after['peak_commit_bytes']-before['commit_bytes']),'metric':'Windows GetProcessMemoryInfo; peak includes process startup and imports'},sort_keys=True))

