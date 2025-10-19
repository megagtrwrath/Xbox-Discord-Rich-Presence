# Linux Daemon

In this section, there is a Daemon that you can use on linux distros that use SystemD.

NOTE: This has only been tested on Arch and may require some changes to the install process for your Distro!
If you need to make any alterations, please let me know! - Mega

# Setup
1. Download the ```xbdStats-go-linux``` client (And the associated ini and json files) from [here](https://github.com/OfficialTeamUIX/Xbox-Discord-Rich-Presence/tree/main/xbdStats-go/Release)
2. Mark the xbdStats-go-linux client able to execute by running ```chmod -x /your/download/directory/xbdStats-go-linux```
3. Configure the xbdStats.ini to match your needs. (This allows you to enable 360 support, and other features)
4. Copy the now able to run ```xbdStats-go-linux``` client, the ```xbdStats.ini``` and the ```xbox360.json``` files to /usr/share/xbdstats (You can change this if you want, but will require editing the daemon!)
5. Copy the ```xbdstats-daemon.service``` to where your Distro stores it's user services. for Arch, this is ```/etc/systemd/user/```
6. Now run systemctl --user enable --now xbdstats-daemon.service

# Congratulations!
The Daemon should now be running.
All you need to do is have Discord also running, and turn on a game in an Rich Presence enabled dashboard!
