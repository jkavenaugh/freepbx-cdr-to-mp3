#!/bin/bash
#
#Checks to see if cdr_play.php has been modified to play mp3s.
#If not it modifies the cdr_play.php so mp3s can be played in the cdr interface.
#Updates to the cdr module will remove this change. Best to cron it every
#hour or so.
#This will result in FreePBX displaying warnings about unsigned and modified code.


if ! grep '[c]ase "mp3":' /var/www/html/admin/modules/cdr/cdr_play.php ; then 
    echo "Adding to cdr_play.php"
    sed -i '
        /switch( $extension )/  a\
                case "mp3":\
                        $ctype="audio/x-mp3";'  /var/www/html/admin/modules/cdr/cdr_play.php  
else 
    echo "Not adding to cdr_play.php"
fi
