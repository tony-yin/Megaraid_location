#! /usr/bin/python
'''
@Author Tony Yin

This script is used to get physical location of logic disk.
So the result maybe the location of one or more hardware disks.
Data format of result is list which contains one or more
hardware disk location. Every disk location data format
contains controller, enclosure id and slot number which
is like [controller]:[enclosure id]:[slot number], such as
[0:1:2, 0:1:2, ...]
'''

import sys
import subprocess
import re

MEGACLI = "/opt/MegaRAID/MegaCli/MegaCli64"

def get_all_disks():
    disks = do_shell("ls /dev/sd* | grep '[a-z]$'")
    return disks.splitlines()

def do_shell(cmd):
    p = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    while p.poll() is None:
        try:
            proc = psutil.Process(p.pid)
            for c in proc.children(recursive=True):
                c.kill()
            proc.kill()
        except psutil.NoSuchProcess:
            pass
    #if p.returncode == 1:
    #    print "Command {} exec error!".format(cmd)
    #    sys.exit(0)
    return output

def get_raid_cards():
    cmd = "lspci | grep '{}'".format("LSI Logic")
    raid_cards = do_shell(cmd).splitlines()
    return raid_cards

def get_disk_pcipath(disk):
    pcipath = ""
    cmd = "udevadm info --query=symlink --name={}".format(disk)
    output = do_shell(cmd)
    for line in output.split():
        if "by-path" in line:
            pcipath = line.split('/')[-1]
            break
    return pcipath

def get_disk_raid_busid(pcipath):
    busid = pcipath.split(":")[1].strip()
    return busid

def get_disk_targetid(pcipath):
    targetid = pcipath.split(":")[4].strip()
    return targetid

def get_controller_count():
    cmd = MEGACLI + " -adpCount -NoLog"
    output = do_shell(cmd)
    for line in output.splitlines():
        if re.match(r'^Controller Count.*$',line.strip()):
            return int(line.split(':')[1].strip().strip('.'))

def get_disk_controller(busid):
    count_number = get_controller_count()
    for cid in range(count_number):
        cmd = MEGACLI + " -AdpGetPciInfo -a{} -NoLog | " \
            "grep -E 'Controller|Bus Number'"
        output = do_shell(cmd.format(str(cid)))
        lines = output.splitlines()
        if lines[1].split(":")[-1].strip().zfill(2) == busid:
            controller = lines[0].split()[-1].strip()
            break
    return controller

def get_disk_location(busid, targetid):
    location = []
    controller = get_disk_controller(busid)
    cmd = MEGACLI + " -LdInfo -l{} -a{} -NoLog | grep 'Number Of Drives'" \
        .format(targetid, controller)
    group_disk_number = do_shell(cmd).split(":")[-1].strip()
    cmd = MEGACLI + " -LdPdInfo -a{} -NoLog | grep -E \
        'Target Id|Enclosure Device ID|Slot Number'"
    lines = do_shell(cmd.format(controller)).splitlines()
    for line in lines:
        if "(Target Id: {})".format(targetid) in line:
            index = lines.index(line)
            for i in range(int(group_disk_number)):
                enclosure_id = lines[index + 2*i + 1].split(':')[1].strip()
                slot_number = lines[index + 2*i + 2].split(':')[1].strip()
                location.append("{}:{}:{}".format(controller, enclosure_id, slot_number))
    return location

if __name__=="__main__":
    if len(sys.argv) < 2:
        print "Please add one disk as parameter!"
        sys.exit(0)

    disk = sys.argv[1]
    disks = get_all_disks()

    if "/dev/{}".format(disk) not in disks:
        print "Valid parameter, disk not found in system!"
        sys.exit(0)

    RaidCardModelMap = ['MegaRAID SAS-3 3108']
    pcipath = get_disk_pcipath(disk)
    busid = get_disk_raid_busid(pcipath)
    raidcards = get_raid_cards()
    result = []

    for card in raidcards:
        # Get raid card model by disk
        if busid == card.split(":")[0]:
            # Check raid card model whether in supported list
            result = [m for m in RaidCardModelMap if m in card]
            break

    if len(result) > 0:
        targetid = get_disk_targetid(pcipath)
        location = get_disk_location(busid, targetid)
    else:
        location = None
    print location
