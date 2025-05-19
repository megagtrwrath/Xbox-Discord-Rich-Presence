#include <xtl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include "network.h"
#include "xbeParse.h"
//-
// This is a simple XBE, no UI, no fancy bells and whistles.
// It loads an ini file, with a path you chose.
// Parses the TitleID, and relays it to Discord.
//-
// ------------------- Discord relay -------------------
void send_discord_relay(const char* title_id_hex, const char* relay_ip, int port) {
    char message[128];
    sprintf(message, "{\"id\":\"%s\"}", title_id_hex);

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) return;

    sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = inet_addr(relay_ip);

    sendto(sock, message, strlen(message), 0, (sockaddr*)&addr, sizeof(addr));
    closesocket(sock);
}

// ------------------- INI reader -------------------
bool read_ini_value(const char* filename, const char* key, char* out_value, int max_len) {
    FILE* file = fopen(filename, "r");
    if (!file) return false;

    char line[256];
    while (fgets(line, sizeof(line), file)) {
        if (strncmp(line, key, strlen(key)) == 0 && line[strlen(key)] == '=') {
            strncpy(out_value, line + strlen(key) + 1, max_len - 1);
            out_value[strcspn(out_value, "\r\n")] = '\0';
            fclose(file);
            return true;
        }
    }

    fclose(file);
    return false;
}

// ------------------- Title ID parser -------------------
bool get_title_id(const char* path, DWORD* out_title_id) {

    if (parseXBE(path, NULL, out_title_id)) {
        return true;
    }

    return false;
}


// ------------------- Device mounting -------------------
typedef struct _STRING {
    USHORT Length;
    USHORT MaximumLength;
    PSTR Buffer;
} UNICODE_STRING, *PUNICODE_STRING, ANSI_STRING, *PANSI_STRING;

extern "C" {
    XBOXAPI LONG WINAPI IoCreateSymbolicLink(IN PUNICODE_STRING SymbolicLinkName, IN PUNICODE_STRING DeviceName);
    XBOXAPI LONG WINAPI IoDeleteSymbolicLink(IN PUNICODE_STRING SymbolicLinkName);
}

#define DeviceC "\\Device\\Harddisk0\\Partition2"
#define DeviceE "\\Device\\Harddisk0\\Partition1"
#define DeviceF "\\Device\\Harddisk0\\Partition6"
#define DeviceG "\\Device\\Harddisk0\\Partition7"
#define DeviceX "\\Device\\Harddisk0\\Partition3"
#define DeviceY "\\Device\\Harddisk0\\Partition4"
#define DeviceZ "\\Device\\Harddisk0\\Partition5"

#define DriveC "\\??\\C:"
#define DriveE "\\??\\E:"
#define DriveF "\\??\\F:"
#define DriveG "\\??\\G:"
#define DriveX "\\??\\X:"
#define DriveY "\\??\\Y:"
#define DriveZ "\\??\\Z:"

LONG MountDevice(LPSTR sSymbolicLinkName, char* sDeviceName) {
    UNICODE_STRING deviceName = { (USHORT)strlen(sDeviceName), (USHORT)(strlen(sDeviceName) + 1), sDeviceName };
    UNICODE_STRING symbolicLinkName = { (USHORT)strlen(sSymbolicLinkName), (USHORT)(strlen(sSymbolicLinkName) + 1), sSymbolicLinkName };
    return IoCreateSymbolicLink(&symbolicLinkName, &deviceName);
}

LONG UnMountDevice(LPSTR sSymbolicLinkName) {
    UNICODE_STRING symbolicLinkName = { (USHORT)strlen(sSymbolicLinkName), (USHORT)(strlen(sSymbolicLinkName) + 1), sSymbolicLinkName };
    return IoDeleteSymbolicLink(&symbolicLinkName);
}

void mountAllDrives() {
    UnMountDevice(DriveX); UnMountDevice(DriveY); UnMountDevice(DriveZ);
    UnMountDevice(DriveC); UnMountDevice(DriveE); UnMountDevice(DriveF); UnMountDevice(DriveG);

    MountDevice(DriveX, DeviceX);
    MountDevice(DriveY, DeviceY);
    MountDevice(DriveZ, DeviceZ);
    MountDevice(DriveC, DeviceC);
    MountDevice(DriveE, DeviceE);
    MountDevice(DriveF, DeviceF);
    MountDevice(DriveG, DeviceG);
}

// ------------------- XBE launcher -------------------
struct pathconv_s {
    char* DriveLetter;
    char* FullPath;
} pathconv_table[] = {
    { "C:", "\\Device\\Harddisk0\\Partition2" },
    { "E:", "\\Device\\Harddisk0\\Partition1" },
    { "F:", "\\Device\\Harddisk0\\Partition6" },
    { "G:", "\\Device\\Harddisk0\\Partition7" },
    { "X:", "\\Device\\Harddisk0\\Partition3" },
    { "Y:", "\\Device\\Harddisk0\\Partition4" },
    { "Z:", "\\Device\\Harddisk0\\Partition5" },
    { NULL, NULL }
};

HRESULT LaunchXBE(char* XBEFile) {
    HRESULT r;
    char *umFilename, *mFilename, *mDrivePath, *mDriveLetter, *mFullPath, *mDevicePath, *tempname;

    umFilename = (char*)malloc(strlen(XBEFile) + 1);
    lstrcpy(umFilename, XBEFile);

    tempname = strrchr(umFilename, '\\');
    mFilename = tempname ? tempname + 1 : umFilename;

    mDrivePath = umFilename;
    tempname = strrchr(mDrivePath, '\\');
    if (tempname) tempname[0] = 0;

    int tm = 0;
    while (mDrivePath[tm] != ':' && mDrivePath[tm] != 0) tm++;
    mDriveLetter = (char*)malloc(tm + 3);
    lstrcpyn(mDriveLetter, mDrivePath, tm + 2);
    mDriveLetter[tm + 2] = 0;
    mDrivePath += tm + 1;

    for (int i = 0; pathconv_table[i].DriveLetter != NULL; i++) {
        if (!lstrcmpi(pathconv_table[i].DriveLetter, mDriveLetter)) {
            mDevicePath = pathconv_table[i].FullPath;
            break;
        }
    }

    mFullPath = (char*)malloc(strlen(mDevicePath) + strlen(mDrivePath) + 1);
    sprintf(mFullPath, "%s%s", mDevicePath, mDrivePath);
    if (mFullPath[strlen(mFullPath) - 1] == '\\') mFullPath[strlen(mFullPath) - 1] = 0;

    ANSI_STRING DeviceName = { (USHORT)strlen(mFullPath), (USHORT)(strlen(mFullPath) + 1), mFullPath };
    ANSI_STRING LinkName = { (USHORT)strlen("\\??\\D:"), (USHORT)(strlen("\\??\\D:") + 1), (PSTR)"\\??\\D:" };

    IoDeleteSymbolicLink(&LinkName);
    IoCreateSymbolicLink(&LinkName, &DeviceName);

    mFullPath = (char*)malloc(strlen(mFilename) + 4);
    sprintf(mFullPath, "D:\\%s", mFilename);

    r = XLaunchNewImage(mFullPath, NULL);
    return r;
}

// ------------------- Entry Point -------------------
int main() {
    network::init();
    mountAllDrives();

    char xbe_path[256] = { 0 };
	// Generic data as placeholders from MobCats original client test.
    char relay_ip[64] = "192.168.0.123";
    char relay_port_str[16] = "6969";

    if (!read_ini_value("D:\\shortcut.ini", "Path", xbe_path, sizeof(xbe_path))) {
        XLaunchNewImage("C:\\xboxdash.xbe", NULL);
        return -1;
    }

    read_ini_value("D:\\shortcut.ini", "RelayIP", relay_ip, sizeof(relay_ip));
    read_ini_value("D:\\shortcut.ini", "RelayPort", relay_port_str, sizeof(relay_port_str));
    int relay_port = atoi(relay_port_str);

    DWORD title_id = 0;
    if (get_title_id(xbe_path, &title_id)) {
        char hex[9];
        sprintf(hex, "%08X", title_id);
        send_discord_relay(hex, relay_ip, relay_port);
    }

    LaunchXBE(xbe_path);
    return 0;
}




