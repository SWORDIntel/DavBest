#pragma once

// Instruction Set for SPECTRE-VM

enum Opcodes {
    // Memory Operations
    PUSH,
    POP,
    LOAD_CONST,
    LOAD_MEM,
    STORE_MEM,

    // Arithmetic/Logic Operations
    ADD,
    SUB,
    XOR,
    CMP,

    // Control Flow Operations
    JMP,
    JZ,
    JNZ,
    CALL,
    RET,

    // System Interaction Operations
    SYSCALL,
    GET_API,

    // Custom Payload Operations
    FIND_KEY,
    DECRYPT_DB
};

// VM Resources

// Registers
enum Registers {
    R0, R1, R2, R3, R4, R5, R6, R7,
    IP, // Instruction Pointer
    SP, // Stack Pointer
    FP, // Frame Pointer
    ZF  // Zero Flag
};

// Memory
#define VM_MEMORY_SIZE (1024 * 1024 * 4) // 4MB
