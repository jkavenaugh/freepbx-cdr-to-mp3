"""
        This script creates a new folder on the NAS and then converts yesterdays .wav recordings to .mp3. 
        If conversion is sucessful it then moves the file to the NAS server mounted as /mnt/asterisk. 
        It then updates the file name in the CDR to an mp3 extension and changes thepath. Upon processing 
        all the files in the directory, it removes the directory and creates a syslink to the new folder 
        containing the converted files on the NAS. Logging information is e-mailed over SMTP SSL.
"""

import logging
import io
import mysql.connector
import smtplib
import socket
import subprocess

from email.mime.text import MIMEText
from os import listdir, remove, makedirs, rmdir, symlink, chown, path
from datetime import date, timedelta
from time import localtime, strftime

# Delta should be set to 1. Delta may be changed to process recordings from earlier dates

delta = 1
lame = 'lame'

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
log_string = io.StringIO()
ch = logging.StreamHandler(log_string)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

recordings_root = '/var/spool/asterisk/monitor'
nas_root = '/mnt/asterisk/monitor'

MySQLUser = 'username'
MySQLPass = 'password'
MySQLHost = '127.0.0.1'
MySQLDB = 'asteriskcdrdb'

mail_to = 'me@mydomain.com'
mail_from = socket.gethostname()+'@mydomain.com'
mail_username = 'me@mydomain.com'
mail_password = 'password'
mail_server = 'smtp.mydomain.com'

def main():

    year, month, day = get_date(delta)
    recordings_path, nas_path = build_paths(year, month, day)
    if not process_directory(recordings_path, nas_path):
        logger.critical('Error proccessing directory')

    log_content = log_string.getvalue()
    log_string.close()
    ch.flush()
    send_report(log_content)

def get_date(delta):
    """Return year, month and day as zero padded strings

    Gets the date with the provided delta. Returns year, month and day as strings. Time delta should be default of 1 for yesterdays date.
    These strings will allow us to create file paths for our recordings.
    """
    this_date = date.today() - timedelta(delta)
    year = this_date.strftime('%Y')
    month = this_date.strftime('%m')
    day = this_date.strftime('%d')

    return year, month, day

def build_paths(year, month, day):
    """Return recordings_path and nas_path

    Builds paths to yesterdays recordings and the target folder on the NAS.
    """

    recordings_path = recordings_root+'/'+year+'/'+month+'/'+day
    nas_path = nas_root+'/'+year+'/'+month+'/'+day

    return recordings_path, nas_path

def create_nas_directory(nas_path):
    """Creates directory if doesn't exist. Assigns owner as Asterisk
    """
    if path.isdir(nas_path):
        return

    logger.info('Creating new NAS directory: '+nas_path)
    print('Creating new NAS directory')
    makedirs(nas_path)

def update_mysql(filename, cnx):
    """Updates mysql asteriskcdrdb with new filename extension. We create a softlink
       to the directory on the NAS Server so all we have to do is update the file extension.
    """

    new_filename = filename.replace('wav', 'mp3')
       
    cursor = cnx.cursor()
    cursor.execute("""
        UPDATE cdr
        SET recordingfile=%s
        WHERE recordingfile LIKE %s
        """, (new_filename, filename))

    if cursor.rowcount == 0:
        logger.error('Failed to update database for file: '+filename) 
    else: 
        logger.info('Updated database for file: '+new_filename)

    cursor.close()
    return True

def wav_to_mp3(recordings_path, filename, nas_path, cnx):
    """Convert wav file to mp3 and move it to NAS
    """
    print(recordings_path+':'+nas_path)
    
    if filename[-3:] == 'mp3':
        logger.info(filename+' already in mp3 format')
        return True

    exit_code = subprocess.call([lame, recordings_path+'/'+filename, nas_path+'/'+filename.replace('wav', 'mp3')])
    if exit_code != 0:
        logger.error('Could not convert '+recordings_path+'/'+filename+' to mp3')
        return False

    if not update_mysql(filename, cnx):
        return False

    remove(recordings_path+'/'+filename)
    return True 

def process_directory(recordings_path, nas_path):
    """Process wav files in directory
    """

    if path.islink(recordings_path):
        logging.info(recordings_path+' directory already processed')
        return True

    create_nas_directory(nas_path)
    cnx = mysql.connector.connect(user=MySQLUser, password=MySQLPass, host=MySQLHost, database=MySQLDB)
    try:
        files = listdir(recordings_path)
    except FileNotFoundError:
        logger.error('Path not found: '+recordings_path)
        return False

    for filename in files:
        if not wav_to_mp3(recordings_path, filename, nas_path, cnx):
            return False


    logger.info('Asterisk recordings processed sucessfully!')

    rmdir(recordings_path)
    symlink(nas_path, recordings_path)
    logging.info('Creating symbolic link for '+recordings_path)

    return True
    cnx.close()

def send_report(log_content):

    """ Send some reporting
    """
	
    text_subtype = 'plain'
    content = mail_from+' recordings processed at'+strftime('%a, %d %b %Y %H:%M:%S', localtime())+'\r'
    if log_content:
        content += 'Logging follows: \r'
        content += str(log_content)


    msg = MIMEText(content, text_subtype)
    if 'ERROR' in str(log_content):
        msg['Subject'] = mail_from+': Error processing recordings'
    else:
        msg['Subject'] = mail_from+': Success processing recordings'
        msg['Subject'] = mail_from
    msg['From'] = mail_from
    msg['To'] = mail_to

    server = smtplib.SMTP_SSL(mail_server)
    server.login(mail_username, mail_password)
    server.sendmail(mail_username, mail_to, msg.as_string())
    server.quit()

if __name__ == "__main__":
    main()
