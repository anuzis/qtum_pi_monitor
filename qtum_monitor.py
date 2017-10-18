#!/usr/bin/python

""" Simple script to monitor QTUM wallet and notify when blocks are won.

Runs via cron. Ref: https://www.howtoforge.com/a-short-introduction-to-cron-jobs
Example running hourly. Change the first 0 to * if you want updates each minute.
0 * * * * /usr/bin/python /home/pi/qtum_monitor.py

First time the script runs it saves the current balance and stake data to a file.
On subsequent runs, if 'stake' increases the script emails you at RECIPIENT_EMAIL
"""
import subprocess
import json
import os
import sys
import datetime

# Configuration options
NOTIFY_ALWAYS = False # False notifies on wins only, if True also reports general balance updates
DAILY_STATUS_UPDATE = True # Send a daily status update to confirm still running
MONITOR_TEMPERATURE = True # only set true for Raspberry Pi or a system with similar temperature monitoring
TEMPERATURE_WARNING_THRESHOLD = 80.0 # warn if temperature exceeds this threshold in Celsius

# Assumes system is configured to use /usr/bin/mail.
# Easy setup ref: http://www.raspberry-projects.com/pi/software_utilities/email/ssmtp-to-send-emails
RECIPIENT_EMAIL = 'YOUR_EMAIL_HERE@gmail.com'

QTUM_PATH = '/home/pi/qtum/'
LOG_FILE = QTUM_PATH + 'qtum_monitor.log'

STATE_DATA = {
    'initial_balance': 0.0,
    'balance': 0.0,
    'stake': 0.0,
    'total_balance': 0.0,
    'last_block_time_won': 0, # epoch seconds of last block win
    'date': datetime.date.today().isoformat()
}

if __name__ == '__main__':
    # Get latest wallet info.
    try:
        wallet_info = json.loads(subprocess.check_output([QTUM_PATH + 'bin/qtum-cli', 'getwalletinfo']))
        staking_info = json.loads(subprocess.check_output([QTUM_PATH + 'bin/qtum-cli', 'getstakinginfo']))
    except subprocess.CalledProcessError:
        cmd = 'echo "Error running qtum-cli. Verify settings" | /usr/bin/mail -s "Error running qtum-cli" %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()

    # Pre-checks
    if (not wallet_info['balance']) and (not wallet_info['stake']):
        cmd = 'echo "No QTUM balance." | /usr/bin/mail -s "No QTUM balance" %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()
    if staking_info['errors']:
        cmd = 'echo "QTUM Errors: %s" | /usr/bin/mail -s "QTUM Errors" %s' % (str(staking_info['errors']), RECIPIENT_EMAIL)
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()
    if wallet_info['unlocked_until'] == 0:
        cmd = 'echo "QTUM Locked - Not Staking" | /usr/bin/mail -s "QTUM Locked - Not Staking" %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()
    if staking_info['enabled'] != True:
        cmd = 'echo "QTUM Staking disabled." | /usr/bin/mail -s "QTUM staking disabled." %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()
    if staking_info['staking'] != True:
        cmd = 'echo "QTUM Not Yet Staking" | /usr/bin/mail -s "QTUM Not Yet Staking" %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()
    if MONITOR_TEMPERATURE:
        temp_str = subprocess.check_output(['/opt/vc/bin/vcgencmd', 'measure_temp'])
        temp = float(temp_str[temp_str.find('=')+1:temp_str.find("'")])
        if temp > TEMPERATURE_WARNING_THRESHOLD:
            cmd = 'echo "QTUM Pi Temperature Warning! %fC above %fC" | /usr/bin/mail -s "QTUM Pi Temperature Warning" %s' % (temp, TEMPERATURE_WARNING_THRESHOLD, RECIPIENT_EMAIL)
            ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Prepare relevant state data
    latest_data = STATE_DATA.copy()
    latest_data['balance'] = wallet_info['balance']
    latest_data['stake'] = wallet_info['stake']
    latest_data['total_balance'] = wallet_info['balance'] + wallet_info['stake']
    latest_data['date'] = datetime.date.today().isoformat()

    # Read prior status for comparison, creating log file if none.
    if not os.path.exists(LOG_FILE):
        latest_data['initial_balance'] = wallet_info['balance']
        f = open(LOG_FILE, 'w')
        f.write(json.dumps(latest_data))
        f.close()
        cmd = 'echo "QTUM Monitor initialized" | /usr/sbin/ssmtp %s' % RECIPIENT_EMAIL
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sys.exit()

    # Read prior data.
    log_file = open(LOG_FILE, 'r')
    prior_data = json.loads(log_file.read())
    log_file.close()

    # Report on results
    if latest_data['stake'] > prior_data['stake']:
        latest_data['last_block_time_won'] = int(time.time())
        cmd = 'echo "Stake earned! Balance: %d Stake: %d" | /usr/bin/mail -s "Stake earned!" %s' % (int(latest_data['balance']), int(latest_data['stake']), RECIPIENT_EMAIL)
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if NOTIFY_ALWAYS:
        cmd = 'echo "Balance: %d Stake: %d" | /usr/bin/mail -s "Update" %s' % (int(latest_data['balance']), int(latest_data['stake']), RECIPIENT_EMAIL)
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if DAILY_STATUS_UPDATE and (latest_data['date'] != prior_data['date']):
        cmd = 'echo "Balance: %d Stake: %d" | /usr/bin/mail -s "%s Daily Update: %d" %s' % (
            int(latest_data['balance']), int(latest_data['stake']), latest_data['date'], int(latest_data['total_balance']), RECIPIENT_EMAIL)
        ssmpt = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Write latest state to log
    log_file = open(LOG_FILE, 'w')
    log_file.write(json.dumps(latest_data))
    log_file.close()
