# ______ ___  _____ _____ _   _ _   _  _____ ___________ 
# |  ___/ _ \|_   _|_   _| | | | | | ||  _  |_   _|  _  \
# | |_ / /_\ \ | |   | | | |_| | | | || | | | | | | | | |
# |  _||  _  | | |   | | |  _  | | | || | | | | | | | | |
# | |  | | | |_| |_  | | | | | \ \_/ /\ \_/ /_| |_| |/ / 
# \_|  \_| |_/\___/  \_/ \_| |_/\___/  \___/ \___/|___/  
# ShortcutRelayPy - Simple Discord Rich Presence script for XBMC4Xbox / XBMC4Gamers (and possibly XBMC360). For use with Mobcat/MrMilenko's "xbdStats" server.

import xbmc, xbmcgui
import os
import socket
import json
import struct

# Server IP & Port settings
SERVER_IP = '192.168.1.100' # Change this to your PC/server running xbdStats
SERVER_PORT = 1102 # Only change this if you've changed the port that xbdStats uses on your PC/server.
DEFAULT_PATH = '' # Change this to the primary path where your games are located for faster access. (ie; 'F:/Games/Retail'). Defaults to showing all drives when left blank.

# Ask the user to select the .XBE file for the game they'd like to run.
def select_xbe():
    dialog = xbmcgui.Dialog()
    xbe_path = dialog.browse(1, 'Select Game (Discord)', 'files', '.xbe', True, False, DEFAULT_PATH)
    return xbe_path if xbe_path and os.path.isfile(xbe_path) else None

# Scan the .XBE for the title ID (Xbox)
def read_titleid(xbe_path):
    try:
        with open(xbe_path, 'rb') as f:
            # Verify XBE magic number ("XBEH")
            f.seek(0)
            if f.read(4) != b'XBEH':
                return None

            # Read base address (offset 0x104)
            f.seek(0x104)
            base_addr = struct.unpack('<I', f.read(4))[0]

            # Read certificate address (offset 0x118)
            f.seek(0x118)
            cert_addr = struct.unpack('<I', f.read(4))[0]

            # Calculate certificate file offset
            cert_offset = cert_addr - base_addr

            # Seek to certificate and read Title ID (offset 0x8 in certificate)
            f.seek(cert_offset + 0x8)
            titleid = struct.unpack('<I', f.read(4))[0]

            # Return as 8-digit uppercase hex string
            return "%08X" % titleid

    except Exception as e:
        xbmc.log("XBE TitleID Error: %s" % str(e), level=xbmc.LOGERROR)
        return None

# Swap endian (uint32) (Xbox 360)
def swap32(x):
    return ((x & 0xFF) << 24) | ((x & 0xFF00) << 8) | ((x >> 8) & 0xFF00) | ((x >> 24) & 0xFF)

# Scan the .XEX for the title ID (Xbox 360)
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

# Send the title ID to the xbdStats server
def send_to_server(data):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet = json.dumps(data)
        sock.sendto(packet.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        sock.close()
        return True
    except Exception as e:
        return False

# Launch the game (XBE) after sending the title ID
def launch_game(xbe_path):
    xbmc.executebuiltin('XBMC.RunXBE(%s)' % xbe_path)

# Launch the game (XEX) after sending the title ID
def launch_game_xex(xex_path):
    xbmc.executebuiltin('XBMC.RunXEX(%s)' % xex_path)

def main():
    xbe_path = select_xbe()
    if not xbe_path:
        return

    folder_name = os.path.basename(os.path.dirname(xbe_path))
    titleid = None

    if xbe_path.lower().endswith('.xex'):
        titleid = read_titleid_xex(xex_path)
    else:
        titleid = read_titleid(xbe_path)

    payload = {
        'id': titleid if titleid else folder_name
    }

    if send_to_server(payload):
        launch_game(xbe_path)
    else:
        xbmc.executebuiltin('XBMC.Notification("Shortcut Relay", "Failed to send title ID to server!", 3000)')

if __name__ == '__main__':
    main()
