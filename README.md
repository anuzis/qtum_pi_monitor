# QTUM Raspberry Pi Monitor

- Simple script to notify of block wins, monitor temperature, and performs basic sanity checks.
- Under 100 lines (on release), easy to review and modify.

# Setup Instructions
- Set RECIPIENT_EMAIL to your address.
- Set QTUM_PATH to where you have QTUM installed.
- Add a cronjob to run the script at your desired frequency. (examples in script)

Easy areas for improvement:
- Report on weekly/monthly/overall growth relative to initial balance
- Report on whether block win timing is lucky/unlucky relative to statistical expectation
