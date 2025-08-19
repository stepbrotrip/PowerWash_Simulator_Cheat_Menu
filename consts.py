import ctypes
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
INVALID_HANDLE_VALUE = -1
PAGE_EXECUTE_READWRITE = 0x40
PROCESS_ALL_ACCESS = (0x000F0000 | 0x00100000 | 0xFFFF)

class PROCESSENTRY32(ctypes.Structure):
	_fields_ = [
		("dwSize", wintypes.DWORD),
		("cntUsage", wintypes.DWORD),
		("th32ProcessID", wintypes.DWORD),
		("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
		("th32ModuleID", wintypes.DWORD),
		("cntThreads", wintypes.DWORD),
		("th32ParentProcessID", wintypes.DWORD),
		("pcPriClassBase", wintypes.LONG),
		("dwFlags", wintypes.DWORD),
		("szExeFile", ctypes.c_char * 260),
	]
    

class MODULEENTRY32(ctypes.Structure):
	_fields_ = [
		("dwSize", wintypes.DWORD),
		("th32ModuleID", wintypes.DWORD),
		("th32ProcessID", wintypes.DWORD),
		("GlblcntUsage", wintypes.DWORD),
		("ProccntUsage", wintypes.DWORD),
		("modBaseAddr", ctypes.POINTER(wintypes.BYTE)),
		("modBaseSize", wintypes.DWORD),
		("hModule", wintypes.HMODULE),
		("szModule", ctypes.c_char * 256),
		("szExePath", ctypes.c_char * 260),
	]
