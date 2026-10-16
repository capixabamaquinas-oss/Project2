import argparse, ctypes, hashlib, json, sys, time
from ctypes import wintypes
from pathlib import Path

class PMC(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
def memory():
 c=PMC(); c.cb=ctypes.sizeof(PMC); psapi=ctypes.WinDLL('psapi',use_last_error=True); kernel32=ctypes.WinDLL('kernel32',use_last_error=True); kernel32.GetCurrentProcess.restype=wintypes.HANDLE; get_info=psapi.GetProcessMemoryInfo; get_info.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]; get_info.restype=wintypes.BOOL
 if not get_info(kernel32.GetCurrentProcess(),ctypes.byref(c),c.cb): raise ctypes.WinError(ctypes.get_last_error())
 return {'working_set_bytes':int(c.WorkingSetSize),'peak_working_set_bytes':int(c.PeakWorkingSetSize),'commit_bytes':int(c.PagefileUsage),'peak_commit_bytes':int(c.PeakPagefileUsage)}
p=argparse.ArgumentParser(); p.add_argument('--package-root',required=True); p.add_argument('--input',required=True); p.add_argument('--mode',choices=['direct','preflight'],required=True); p.add_argument('--limit',type=int,default=4096); a=p.parse_args()
sys.dont_write_bytecode=True; sys.path.insert(0,a.package_root)
from babel_pura import address
raw=Path(a.input).read_bytes(); text=raw.decode('ascii'); before=memory(); calls={'parser':0,'format_decode':0}
original=address.decode_format
def counted(*args,**kwargs):
 calls['format_decode']+=1; return original(*args,**kwargs)
address.decode_format=counted
started=time.perf_counter(); outcome='accepted'; detail=''
try:
 if a.mode=='preflight' and len(text)>a.limit:
  outcome='preflight_rejected_before_parser'
 else:
  calls['parser']+=1
  address.decode_address(text)
except Exception as e:
 outcome=type(e).__name__; detail=str(e)[:160]
elapsed=time.perf_counter()-started; after=memory()
print(json.dumps({'mode':a.mode,'input_bytes':len(raw),'limit_chars':a.limit if a.mode=='preflight' else None,'input_sha256':__import__('hashlib').sha256(raw).hexdigest(),'outcome':outcome,'detail':detail,'parser_calls':calls['parser'],'format_decode_calls':calls['format_decode'],'elapsed_seconds':elapsed,'baseline_working_set_bytes':before['working_set_bytes'],'peak_working_set_bytes':after['peak_working_set_bytes'],'peak_working_set_delta_bytes':max(0,after['peak_working_set_bytes']-before['working_set_bytes']),'peak_commit_bytes':after['peak_commit_bytes'],'peak_commit_delta_bytes':max(0,after['peak_commit_bytes']-before['commit_bytes']),'metric':'Windows GetProcessMemoryInfo; input string loaded before baseline; peak includes startup/imports'},sort_keys=True))

