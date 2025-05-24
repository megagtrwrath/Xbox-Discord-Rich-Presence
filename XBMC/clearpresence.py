# ______ ___  _____ _____ _   _ _   _  _____ ___________ 
# |  ___/ _ \|_   _|_   _| | | | | | ||  _  |_   _|  _  \
# | |_ / /_\ \ | |   | | | |_| | | | || | | | | | | | | |
# |  _||  _  | | |   | | |  _  | | | || | | | | | | | | |
# | |  | | | |_| |_  | | | | | \ \_/ /\ \_/ /_| |_| |/ / 
# \_|  \_| |_/\___/  \_/ \_| |_/\___/  \___/ \___/|___/  
# ClearPresence - Discord Rich Presence clearing script for XBMC4Xbox / XBMC4Gamers (and possibly XBMC360). For use with Mobcat/MrMilenko's "xbdStats" server + ShortcutRelayPy. To use on startup, add xbmc.executebuiltin("XBMC.RunScript(Q:/scripts/ShortcutRelayPy/clearpresence.py)") to "autoexec.py" in your XBMC "scripts" folder (usually Q:/scripts) ] 

import socket
import json

# Server IP & Port
SERVER_IP = '192.168.1.100'  # Change this to your PC/server running xbdStats
SERVER_PORT = 1102  # Only change this if you've changed the port that xbdStats uses on your PC/server.

TITLE_ID = '' # Only modify if you intend to change the titleID to your Dashboard's Title ID!

# Sends a blank title ID to the xbdStats server
def send_to_server(title_id):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = json.dumps({'id': title_id})
        sock.sendto(payload.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        sock.close()
    except Exception as e:
        pass  # Silently fail

send_to_server(TITLE_ID)
