# freepbx-cdr-to-mp3
Converts FreePBX CDR files from wav to mp3 immensely decreasing storage space.

archive_asterisk.py

1. Converts wav recordings to mp3.
2. Copies mp3s to a new directory (ie: mounted NAS).
3. Modifies recordings in the MySQL database to reflect new extension and path of recording files.
4. Sends a log to an e-mail address using smtp with SSL.
5. Should be run afterhours for performance.

add_mp3_content_type.sh

1. Checks to see if the CDR has been changed to play mp3 files natively.
2. If not it modifies the proper CDR file.
3. Warning! This will cause security alerts in FreePBX about modified files and unsigned modules.
4. Add to cron every hour for good results.
