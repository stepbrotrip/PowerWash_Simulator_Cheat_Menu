import ctypes
from ctypes import wintypes
from consts import *

kernel32 = ctypes.windll.kernel32


def GetProcId(processName: str):
	procId = None
	hSnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)

	if hSnap != INVALID_HANDLE_VALUE:
		procEntry = PROCESSENTRY32()
		procEntry.dwSize = ctypes.sizeof(PROCESSENTRY32)

		if kernel32.Process32First(hSnap, ctypes.byref(procEntry)):
			while True:
				name = procEntry.szExeFile.decode("utf-8").rstrip("\x00")
				if name.lower() == processName.lower():
					procId = procEntry.th32ProcessID
					break
				if not kernel32.Process32Next(hSnap, ctypes.byref(procEntry)):
					break

	kernel32.CloseHandle(hSnap)
	return procId


def GetModuleBaseAddress(pid, moduleName: str):
	baseAddress = None
	hSnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)

	if hSnap != INVALID_HANDLE_VALUE:
		modEntry = MODULEENTRY32()
		modEntry.dwSize = ctypes.sizeof(MODULEENTRY32)

		if kernel32.Module32First(hSnap, ctypes.byref(modEntry)):
			while True:
				name = modEntry.szModule.decode("utf-8").rstrip("\x00")
				if name.lower() == moduleName.lower():
					baseAddress = ctypes.addressof(modEntry.modBaseAddr.contents)
					break
				if not kernel32.Module32Next(hSnap, ctypes.byref(modEntry)):
					break

	kernel32.CloseHandle(hSnap)
	return baseAddress


def findDMAddy(hProc, base, offsets, arch=64):
	size = 8 if arch == 64 else 4
	address = ctypes.c_uint64(base)

	for offset in offsets:
		buf = ctypes.c_uint64()
		if not kernel32.ReadProcessMemory(hProc, address, ctypes.byref(buf), size, None):
			return None
		address = ctypes.c_uint64(buf.value + offset)

	return address.value


def patchBytes(handle, src, destination, size):
	src = bytes.fromhex(src)
	size = ctypes.c_size_t(size)
	destination = ctypes.c_void_p(destination)
	oldProtect = wintypes.DWORD()

	kernel32.VirtualProtectEx(handle, destination, size, PAGE_EXECUTE_READWRITE, ctypes.byref(oldProtect))
	kernel32.WriteProcessMemory(handle, destination, src, size, None)
	kernel32.VirtualProtectEx(handle, destination, size, oldProtect, ctypes.byref(oldProtect))


def nopBytes(handle, destination, size):
    old_buf = (ctypes.c_ubyte * size)()
    kernel32.ReadProcessMemory(handle, ctypes.c_void_p(destination), old_buf, size, None)
    patchBytes(handle, "90" * size, destination, size)
    return bytes(old_buf)  # return the original bytes
