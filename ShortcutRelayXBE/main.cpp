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
void send_discord_relay_websocket(const char *title_id_hex, const char *relay_ip, int port)
{
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
        return;

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(port);
    server.sin_addr.s_addr = inet_addr(relay_ip);

    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == SOCKET_ERROR)
    {
        closesocket(sock);
        return;
    }

    char host_header[64];
    _snprintf(host_header, sizeof(host_header), "Host: %s:%d\r\n", relay_ip, port);

    const char *base_request =
        "GET / HTTP/1.1\r\n"
        "%s"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n";

    char upgrade_request[512];
    _snprintf(upgrade_request, sizeof(upgrade_request), base_request, host_header);

    send(sock, upgrade_request, strlen(upgrade_request), 0);

    char buffer[1024];
    int recv_len = recv(sock, buffer, sizeof(buffer) - 1, 0);
    if (recv_len <= 0)
    {
        closesocket(sock);
        return;
    }
    buffer[recv_len] = '\0';

    if (strstr(buffer, "101 Switching Protocols") == NULL)
    {
        closesocket(sock);
        return;
    }

    char message[128];
    _snprintf(message, sizeof(message), "{\"id\":\"%s\"}", title_id_hex);
    int len = strlen(message);

    char frame[256];
    int frame_len = 0;
    frame[frame_len++] = 0x81;

    unsigned char mask_key[4] = {0x12, 0x34, 0x56, 0x78};

    if (len <= 125)
    {
        frame[frame_len++] = 0x80 | len;
    }
    else
    {
        frame[frame_len++] = 0x80 | 126;
        frame[frame_len++] = (len >> 8) & 0xFF;
        frame[frame_len++] = len & 0xFF;
    }

    memcpy(&frame[frame_len], mask_key, 4);
    frame_len += 4;

    for (int i = 0; i < len; i++)
    {
        frame[frame_len++] = message[i] ^ mask_key[i % 4];
    }

    send(sock, frame, frame_len, 0);


    shutdown(sock, SD_SEND);
    closesocket(sock);
}

void send_discord_relay_udp(const char *title_id_hex, const char *relay_ip, int port)
{
    char message[128];
    _snprintf(message, sizeof(message), "{\"id\":\"%s\"}", title_id_hex);

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET)
        return;

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = inet_addr(relay_ip);

    sendto(sock, message, strlen(message), 0, (struct sockaddr *)&addr, sizeof(addr));
    closesocket(sock);
}

void send_discord_relay_tcp(const char *title_id_hex, const char *relay_ip, int port)
{
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
        return;

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(port);
    server.sin_addr.s_addr = inet_addr(relay_ip);

    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == SOCKET_ERROR)
    {
        closesocket(sock);
        return;
    }

    char message[128];
    _snprintf(message, sizeof(message), "{\"id\":\"%s\"}", title_id_hex);
    send(sock, message, strlen(message), 0);
    shutdown(sock, SD_SEND);
    closesocket(sock);
}

// ------------------- INI reader -------------------
bool read_ini_value(const char *filename, const char *key, char *out_value, int max_len)
{
    FILE *file = fopen(filename, "r");
    if (!file)
        return false;

    char line[256];
    while (fgets(line, sizeof(line), file))
    {
        if (strncmp(line, key, strlen(key)) == 0 && line[strlen(key)] == '=')
        {
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
bool get_title_id(const char *path, DWORD *out_title_id)
{

    if (parseXBE(path, NULL, out_title_id))
    {
        return true;
    }

    return false;
}

// ------------------- Device mounting -------------------
typedef struct _STRING
{
    USHORT Length;
    USHORT MaximumLength;
    PSTR Buffer;
} UNICODE_STRING, *PUNICODE_STRING, ANSI_STRING, *PANSI_STRING;

extern "C"
{
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
//Cerbios Dual HDD Partitions
#define DeviceC2 "\\Device\\Harddisk1\\Partition2"
#define DeviceE2 "\\Device\\Harddisk1\\Partition1"
#define DeviceF2 "\\Device\\Harddisk1\\Partition6"
#define DeviceG2 "\\Device\\Harddisk1\\Partition7"
//Don't know why these would be needed, but here we are!
#define DeviceX2 "\\Device\\Harddisk1\\Partition3"
#define DeviceY2 "\\Device\\Harddisk1\\Partition4"
#define DeviceZ2 "\\Device\\Harddisk1\\Partition5"

#define DriveC "\\??\\C:"
#define DriveE "\\??\\E:"
#define DriveF "\\??\\F:"
#define DriveG "\\??\\G:"
#define DriveX "\\??\\X:"
#define DriveY "\\??\\Y:"
#define DriveZ "\\??\\Z:"
//Cerb Continued
#define DriveC2 "\\??\\C2:"
#define DriveE2 "\\??\\E2:"
#define DriveF2 "\\??\\F2:"
#define DriveG2 "\\??\\G2:"
#define DriveX2 "\\??\\X2:"
#define DriveY2 "\\??\\Y2:"
#define DriveZ2 "\\??\\Z2:"

LONG MountDevice(LPSTR sSymbolicLinkName, char *sDeviceName)
{
    UNICODE_STRING deviceName = {(USHORT)strlen(sDeviceName), (USHORT)(strlen(sDeviceName) + 1), sDeviceName};
    UNICODE_STRING symbolicLinkName = {(USHORT)strlen(sSymbolicLinkName), (USHORT)(strlen(sSymbolicLinkName) + 1), sSymbolicLinkName};
    return IoCreateSymbolicLink(&symbolicLinkName, &deviceName);
}

LONG UnMountDevice(LPSTR sSymbolicLinkName)
{
    UNICODE_STRING symbolicLinkName = {(USHORT)strlen(sSymbolicLinkName), (USHORT)(strlen(sSymbolicLinkName) + 1), sSymbolicLinkName};
    return IoDeleteSymbolicLink(&symbolicLinkName);
}

void mountAllDrives()
{
    UnMountDevice(DriveX);
    UnMountDevice(DriveY);
    UnMountDevice(DriveZ);
    UnMountDevice(DriveC);
    UnMountDevice(DriveE);
    UnMountDevice(DriveF);
    UnMountDevice(DriveG);
	// Cerb continued
	UnMountDevice(DriveX2);
    UnMountDevice(DriveY2);
    UnMountDevice(DriveZ2);
    UnMountDevice(DriveC2);
    UnMountDevice(DriveE2);
    UnMountDevice(DriveF2);
    UnMountDevice(DriveG2);

    MountDevice(DriveX, DeviceX);
    MountDevice(DriveY, DeviceY);
    MountDevice(DriveZ, DeviceZ);
    MountDevice(DriveC, DeviceC);
    MountDevice(DriveE, DeviceE);
    MountDevice(DriveF, DeviceF);
    MountDevice(DriveG, DeviceG);
	//Cerb continued
	MountDevice(DriveX2, DeviceX2);
    MountDevice(DriveY2, DeviceY2);
    MountDevice(DriveZ2, DeviceZ2);
    MountDevice(DriveC2, DeviceC2);
    MountDevice(DriveE2, DeviceE2);
    MountDevice(DriveF2, DeviceF2);
    MountDevice(DriveG2, DeviceG2);
}

// ------------------- XBE launcher -------------------
struct pathconv_s
{
    char *DriveLetter;
    char *FullPath;
} pathconv_table[] = {
    {"C:", "\\Device\\Harddisk0\\Partition2"},
    {"E:", "\\Device\\Harddisk0\\Partition1"},
    {"F:", "\\Device\\Harddisk0\\Partition6"},
    {"G:", "\\Device\\Harddisk0\\Partition7"},
    {"X:", "\\Device\\Harddisk0\\Partition3"},
    {"Y:", "\\Device\\Harddisk0\\Partition4"},
    {"Z:", "\\Device\\Harddisk0\\Partition5"},
	//Cerb continued
    {"C2:", "\\Device\\Harddisk1\\Partition2"},
    {"E2:", "\\Device\\Harddisk1\\Partition1"},
    {"F2:", "\\Device\\Harddisk1\\Partition6"},
    {"G2:", "\\Device\\Harddisk1\\Partition7"},
    {"X2:", "\\Device\\Harddisk1\\Partition3"},
    {"Y2:", "\\Device\\Harddisk1\\Partition4"},
    {"Z2:", "\\Device\\Harddisk1\\Partition5"},
    {NULL, NULL}};

HRESULT LaunchXBE(char *XBEFile)
{
    HRESULT r;
    char *umFilename, *mFilename, *mDrivePath, *mDriveLetter, *mFullPath, *mDevicePath, *tempname;

    umFilename = (char *)malloc(strlen(XBEFile) + 1);
    lstrcpy(umFilename, XBEFile);

    tempname = strrchr(umFilename, '\\');
    mFilename = tempname ? tempname + 1 : umFilename;

    mDrivePath = umFilename;
    tempname = strrchr(mDrivePath, '\\');
    if (tempname)
        tempname[0] = 0;

    int tm = 0;
    while (mDrivePath[tm] != ':' && mDrivePath[tm] != 0)
        tm++;
    mDriveLetter = (char *)malloc(tm + 3);
    lstrcpyn(mDriveLetter, mDrivePath, tm + 2);
    mDriveLetter[tm + 2] = 0;
    mDrivePath += tm + 1;

    for (int i = 0; pathconv_table[i].DriveLetter != NULL; i++)
    {
        if (!lstrcmpi(pathconv_table[i].DriveLetter, mDriveLetter))
        {
            mDevicePath = pathconv_table[i].FullPath;
            break;
        }
    }

    mFullPath = (char *)malloc(strlen(mDevicePath) + strlen(mDrivePath) + 1);
    sprintf(mFullPath, "%s%s", mDevicePath, mDrivePath);
    if (mFullPath[strlen(mFullPath) - 1] == '\\')
        mFullPath[strlen(mFullPath) - 1] = 0;

    ANSI_STRING DeviceName = {(USHORT)strlen(mFullPath), (USHORT)(strlen(mFullPath) + 1), mFullPath};
    ANSI_STRING LinkName = {(USHORT)strlen("\\??\\D:"), (USHORT)(strlen("\\??\\D:") + 1), (PSTR) "\\??\\D:"};

    IoDeleteSymbolicLink(&LinkName);
    IoCreateSymbolicLink(&LinkName, &DeviceName);

    mFullPath = (char *)malloc(strlen(mFilename) + 4);
    sprintf(mFullPath, "D:\\%s", mFilename);

    r = XLaunchNewImage(mFullPath, NULL);
    return r;
}

// ------------------- Entry Point -------------------
int main()
{
    network::init();
    mountAllDrives();

    char xbe_path[256] = {0};
    // Generic data as placeholders from MobCats original client test.
    char relay_ip[64] = "192.168.0.123";
    char relay_port_str[16] = "6969";

    if (!read_ini_value("D:\\shortcut.ini", "Path", xbe_path, sizeof(xbe_path)))
    {
        XLaunchNewImage("C:\\xboxdash.xbe", NULL);
        return -1;
    }

    read_ini_value("D:\\shortcut.ini", "RelayIP", relay_ip, sizeof(relay_ip));
    read_ini_value("D:\\shortcut.ini", "RelayPort", relay_port_str, sizeof(relay_port_str));
    int relay_port = atoi(relay_port_str);

    DWORD title_id = 0;
    if (get_title_id(xbe_path, &title_id))
    {
        char hex[9];
        sprintf(hex, "%08X", title_id);
        switch (relay_port)
        {
        case 1101:
            send_discord_relay_websocket(hex, relay_ip, relay_port);
            break;
        case 1102:
            send_discord_relay_udp(hex, relay_ip, relay_port);
            break;
        case 1103:
            send_discord_relay_tcp(hex, relay_ip, relay_port);
            break;
        default:
            // Fallback or ignore
            break;
        }
    }

    LaunchXBE(xbe_path);
    return 0;
}