#!/usr/bin/python

import sys
import getopt
import getpass
import rubrik_cdm
import time
import urllib3
urllib3.disable_warnings()


def usage():
    sys.stderr.write("Usage: rbk_smb_export.py [-hD] [-c creds] rubrik \"src_unc\" \"dest_unc\"\n")
    sys.stderr.write("    -h | --help : Prints Usage\n")
    sys.stderr.write("    -D | --debug : Debug mode.  More output for debugging purposes\n")
    sys.stderr.write("    -c | --creds= : Rubrik Credentials.  Either user:password or a file\n")
    sys.stderr.write("rubrik: Hostname or IP of the Rubrik\n")
    sys.stderr.write("\"src_unc\" : UNC path of the file to be restored.  NOTE: Use quotes\n")
    sys.stderr.write("\"dest_unc\" : UNC path to the restore location.  NOTE Use quotas\n")
    exit(0)

def get_creds_from_file(file, array):
    with open(file) as fp:
        data = fp.read()
    fp.close()
    data = data.decode('uu_codec')
    data = data.decode('rot13')
    lines = data.splitlines()
    for x in lines:
        if x == "":
            continue
        xs = x.split(':')
        if xs[0] == array:
            user = xs[1]
            password = xs[2]
    return (user, password)

def dprint(message):
    if DEBUG:
        print message + "\n"
    return()

def find_latest_snapshot(rubrik_api,rbk_search):
    latest_date = "1970-01-01T01:00:00"
    latest_snap_id = ""
    for snap in rbk_search['data'][0]['fileVersions']:
        snap_id = snap['snapshotId']
        rbk_snap = rubrik_api.get('v1','/fileset/snapshot/' + str(snap_id))
        if rbk_snap['date'] > latest_date:
            latest_snap_id = snap_id
    return (latest_snap_id)

def get_share_id(rbk_host_share, host, share):
    share_id = ""
    host_id = ""
    for hs in rbk_host_share['data']:
        if hs['hostname'] == host and hs['exportPoint'] == share:
            share_id = hs['id']
            host_id = hs['hostId']
            break
    return(share_id, host_id)

def dir_match(rubrik_api, rbk_search, src_path):
    filename = ""
    latest_date = "1970-0101T01:00:00"
    latest_snap_id = ""
    for f in rbk_search['data']:
        if f['path'] == src_path:
            filename = f['filename']
            for snap in f['fileVersions']:
                if snap['fileMode'] == "directory":
                    snap_id = snap['snapshotId']
                    rbk_snap = rubrik_api.get('v1', '/fileset/snapshot/' + str(snap_id))
                    if rbk_snap['date'] > latest_date:
                        latest_snap_id = snap_id
    return (filename, latest_snap_id)






if __name__ == "__main__":
    user = ""
    password = ""
    rubrik_host = ""
    src_path = ""
    target_path = ""
    DEBUG = False
    filename = ""

    optlist, args = getopt.getopt(sys.argv[1:], 'hc:D', ['--help', '--creds=', '--debug'])
    for opt, a in optlist:
        if opt in ('-h', '--help'):
            usage()
        if opt in ('-c', '--creds'):
            if ':' in a:
                (user, password) = a.split(':')
            else:
                (user, password) = get_creds_from_file(a, 'rubrik')
        if opt in ('-D', '--debug'):
            DEBUG = True

    if args[0] == '?':
        usage()
    (rubrik_host, src_path, dest_path_full) = args
    src_f = src_path.split("\\")
    src_host = src_f[1]
    src_share = src_f[2]
    src_path = "\\".join(src_f[3:])
    src_path = "\\" + src_path
    dest_f = dest_path_full.split('\\')
    dest_host = dest_f[1]
    dest_share = dest_f[2]
    dest_path = "\\".join(dest_f[3:])
    dest_path = "\\" + dest_path
    if user == "":
        user = raw_input("User: ")
    if password == "":
        password = getpass.getpass("Password: ")
    rubrik_api = rubrik_cdm.Connect(rubrik_host, user, password)
    rbk_host_share = rubrik_api.get('internal', '/host/share')
    (src_share_id, src_host_id) = get_share_id(rbk_host_share, src_host, src_share)
    if src_share_id == "":
        sys.stderr.write("Can't find source share on Rubrik\n")
        exit(1)
    dprint("Source ShareID: " + src_share_id)
    src_snap_id = ""
    rbk_search = rubrik_api.get('internal', '/host/share/' + str(src_share_id) + "/search?path=" + src_path)
    if rbk_search['total'] == 0:
        sys.stderr.write("Can't find file on source\n")
        exit(1)
    if rbk_search['total'] > 1:
        (filename, src_snap_id) = dir_match(rubrik_api, rbk_search, src_path)
        if filename == "":
            sys.stderr.write("Multiple instances of the file found: " + src_path + "\n")
            exit(1)
    if filename == "":
        filename = rbk_search['data'][0]['filename']
        src_snap_id = find_latest_snapshot(rubrik_api,rbk_search)
    if src_snap_id == "":
        sys.stderr.write("Snapshot for source file not found\n")
        exit(1)
    dprint("Source SnapshotID: " + src_snap_id)
    (dest_share_id, dest_host_id) = get_share_id(rbk_host_share, dest_host, dest_share)
    if dest_share_id == "":
        sys.stderr.write("Can't find destination share on Rubrik\n")
        exit(1)
    dprint("Destination ShareId: " + dest_share_id)
    payload = {"sourceDir": src_path, "destinationDir": dest_path, "hostId": dest_host_id, "shareId": dest_share_id}
    rbk_export = rubrik_api.post('v1', '/fileset/snapshot/' + str(src_snap_id) + '/export_file', payload)
    job_url = rbk_export['links'][0]['href'].split('/')
    job_url = "/" + "/".join(job_url[5:])
    done = False
    while not done:
        job_check = rubrik_api.get('v1', str(job_url))
        job_status = str(job_check['status'])
        dprint("JOB Status: " + job_status)
        if job_status in ['RUNNING', 'QUEUED', 'ACQIUIRING', 'FINISHING']:
            time.sleep(5)
        elif job_status == "SUCCEEDED":
            done = True
        else:
            sys.stdeerr.write("Job Ended with status: " + job_status + "\n")
            exit(1)
    print "\\" + dest_path_full + "\\" + filename

