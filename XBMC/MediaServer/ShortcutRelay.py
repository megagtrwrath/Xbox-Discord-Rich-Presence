# ______ ___  _____ _____ _   _ _   _  _____ ___________ 
# |  ___/ _ \|_   _|_   _| | | | | | ||  _  |_   _|  _  \
# | |_ / /_\ \ | |   | | | |_| | | | || | | | | | | | | |
# |  _||  _  | | |   | | |  _  | | | || | | | | | | | | |
# | |  | | | |_| |_  | | | | | \ \_/ /\ \_/ /_| |_| |/ / 
# \_|  \_| |_/\___/  \_/ \_| |_/\___/  \___/ \___/|___/  
# sakuraPresence 0.5 - Simple Discord Rich Presence script for XBMC4Xbox / XBMC4Gamers. For use with Mobcat/MrMilenko's "xbdStats" server or my own fork (sakuraPresence). Now with 100% more UDP auto-detection!

import xbmc, xbmcgui
import os
import socket
import json
import struct
import hashlib

# Server port and default path
SERVER_PORT = 1102
DEFAULT_PATH = ''  # Optional: set to something like 'F:/Games/Retail' for faster browsing

BLOCKLIST = {"4D5307E6", "FFFFFEFF", "00000000", "0", "FFFF051F", "FFFF0002"} # Does nothing (yet)
# [FFFF0002 - Default NXDK titleID] | 

# Auto-discovery via UDP broadcast
def discover_server(timeout=5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', SERVER_PORT))
    sock.settimeout(timeout)
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            if data == b'XBDSTATS_ONLINE':
                xbmc.executebuiltin('XBMC.Notification("sakuraPresence", "Server found!", 4000, icon-cortana.png)')
                return addr[0]
    except socket.timeout:
        return None
    finally:
        sock.close()

# Ask the user to select the .XBE file
def select_xbe():
    dialog = xbmcgui.Dialog()
    xbe_path = dialog.browse(1, 'Select Game (Discord)', 'files', '.xbe', True, False, DEFAULT_PATH)
    return xbe_path if xbe_path and os.path.isfile(xbe_path) else None

# Scan .XBE for title ID (Xbox)
def read_titleid(xbe_path):
    try:
        with open(xbe_path, 'rb') as f:
            f.seek(0)
            if f.read(4) != b'XBEH':
                return None
            f.seek(0x104)
            base_addr = struct.unpack('<I', f.read(4))[0]
            f.seek(0x118)
            cert_addr = struct.unpack('<I', f.read(4))[0]
            cert_offset = cert_addr - base_addr
            f.seek(cert_offset + 0x8)
            titleid = struct.unpack('<I', f.read(4))[0]
            return "%08X" % titleid
    except Exception as e:
        xbmc.log("XBE TitleID Error: %s" % str(e), level=xbmc.LOGERROR)
        return None

# Swap endian (uint32) (Xbox 360)
def swap32(x):
    return ((x & 0xFF) << 24) | ((x & 0xFF00) << 8) | ((x >> 8) & 0xFF00) | ((x >> 24) & 0xFF)

# Scan .XEX for title ID (Xbox 360)
def read_titleid_xex(xex_path):
    try:
        with open(xex_path, 'rb') as f:
            br = f
            br.seek(0)
            if br.read(4) != b'XEX2':
                return None

            def get_uint(offset):
                br.seek(offset)
                data = br.read(4)
                if len(data) != 4:
                    raise Exception("Invalid read at offset %X" % offset)
                return swap32(struct.unpack('<I', data)[0])

            code_offset = get_uint(0x08)
            cert_offset = get_uint(0x10)
            info_count  = get_uint(0x14)

            if cert_offset > code_offset or info_count * 8 + 0x18 > code_offset:
                return None

            exec_info_offset = 0
            for i in range(info_count):
                base = 0x18 + (i * 8)
                entry_id = get_uint(base)
                if entry_id == 0x00040006:
                    exec_info_offset = get_uint(base + 4)
                    break

            if exec_info_offset == 0:
                return None

            titleid = get_uint(exec_info_offset + 0x0C)
            return "%08X" % titleid
    except Exception as e:
        xbmc.log("XEX TitleID Error: %s" % str(e), level=xbmc.LOGERROR)
        return None

# Send title ID to server
def send_to_server(data, server_ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet = json.dumps(data)
        sock.sendto(packet.encode('utf-8'), (server_ip, SERVER_PORT))
        sock.close()
        return True
    except Exception as e:
        xbmc.log("Send Error: %s" % str(e), level=xbmc.LOGERROR)
        return False

# Launch the game (Xbox)
def launch_game(xbe_path):
    xbmc.executebuiltin('XBMC.RunXBE(%s)' % xbe_path)
# Launch the game (Xbox 360)
def launch_game_xex(xex_path):
    xbmc.executebuiltin('XBMC.RunXEX(%s)' % xex_path)

def get_selected_game_path():
    try:
        path = xbmc.getInfoLabel('ListItem.Path')
        filename = xbmc.getInfoLabel('ListItem.FilenameAndPath')

        full_path = filename or path

        if full_path and (full_path.lower().endswith('.xbe') or full_path.lower().endswith('.xex')):
            if os.path.isfile(full_path):
                return full_path
    except Exception as e:
        xbmc.log("Error reading selected listitem via getInfoLabel: %s" % str(e), xbmc.LOGERROR)
    return None

def main():
    server_ip = discover_server()
    if not server_ip:
        xbmc.executebuiltin('XBMC.Notification("Xbox Discord Rich Presence", "No xbdStats / sakuraPresence server found!", 4000)')
        return

    xbe_path = get_selected_game_path()

    if not xbe_path:
        xbe_path = select_xbe()
    if not xbe_path:
        return

    folder_name = os.path.basename(os.path.dirname(xbe_path))
    titleid = None
    is_xex = xbe_path.lower().endswith('.xex')

    if is_xex:
        titleid = read_titleid_xex(xbe_path)
    else:
        titleid = read_titleid(xbe_path)

    if not titleid or titleid in BLOCKLIST:
       payload = {'id': titleid} # Hacky workaround because MD5 isn't supported here (yet)
    else:
        payload = {'id': titleid}

    # Sends 'xbox360' as console if sending XEX, otherwise send 'game' (changing to 'xbox' soon!)
    payload['xbox360' if is_xex else 'game'] = True

    if send_to_server(payload, server_ip):
        if is_xex:
            launch_game_xex(xbe_path)
        else:
            launch_game(xbe_path)
    else:
        xbmc.executebuiltin('XBMC.Notification("Xbox Discord Rich Presence", "Failed to send title ID to server!", 3000)')

if __name__ == '__main__':
    main()
