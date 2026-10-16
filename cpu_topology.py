import ctypes,struct,os,platform,winreg
k=ctypes.WinDLL("kernel32",use_last_error=True)
f=k.GetLogicalProcessorInformationEx
f.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
f.restype=ctypes.c_int
n=ctypes.c_uint32(0)
ok=f(0,None,ctypes.byref(n))
err=ctypes.get_last_error()
if ok or err!=122: raise OSError(err,"GetLogicalProcessorInformationEx size query")
b=ctypes.create_string_buffer(n.value)
if not f(0,b,ctypes.byref(n)): raise ctypes.WinError(ctypes.get_last_error())
off=0; cores=0; records=[]
while off<n.value:
 rel,size=struct.unpack_from("<II",b.raw,off)
 if size<8: raise RuntimeError(("invalid record size",off,size))
 if rel==0: cores+=1
 records.append((rel,size)); off+=size
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
 name,_=winreg.QueryValueEx(key,"ProcessorNameString")
print("system="+platform.platform())
print("cpu="+name)
print("physical_cores="+str(cores))
print("logical_processors="+str(os.cpu_count()))
print("processor_records="+str(len(records)))
