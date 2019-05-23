# rbk_smb_export
A quick script to automate finding the latest version of a backed up file on a SMB share and exporting it to a new location

This script helps automate restoring a single file from a Rubrik backup and restores it to a different share.  
As is usual with the Rubrik export feature the destination share must be registered with Rubrik even if there is no SLA to protect that share.  The inputs are the UNC path to the source file and the UNC path to the destination directory.  The output is simply the UNC path of the restored file.

The script is in Python so Linux is preferable.  However Python can be installed on Windows or the code can be compiled into a .exe if needed.  It uses one special package for the <a href="https://github.com/rubrikinc/rubrik-sdk-for-python SDK">Rubrik SDK</a>, the rest are standard.

Currently the credentials can be enetered on the CLI, included on the CLI with -c or use -c to point to a file that has been obfuscated using <a href="https://github.com/adamrfox/creds_encode">creds_encode tool I wrote (use array type "rubrik").  I'm open to other ideas on credentials, but did these options for speed of development.

The syntax is as follows:
<pre>Usage: rbk_smb_export.py [-hD] [-c creds] rubrik "src_unc" "dest_unc"
    -h | --help : Prints Usage
    -D | --debug : Debug mode.  More output for debugging purposes
    -c | --creds= : Rubrik Credentials.  Either user:password or a file
rubrik: Hostname or IP of the Rubrik
"src_unc" : UNC path of the file to be restored.  NOTE: Use quotes
"dest_unc" : UNC path to the restore location.  NOTE Use quotas
</pre>
Note that quotes should be used around the UNC paths since the shell will pick up backslashes.
