#   Copyright 2009, Alexey Sidorov (sidorov.alexey.vyacheslavovich@gmail.com) 
#	
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#	
#           http://www.apache.org/licenses/LICENSE-2.0
#	
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import imaplib
import smtplib
import couchdb

IMAP_SERVER = 'imap..com'
IMAP_SERVER_PORT = '993'
IMAP_SERVER_TYPE = 'SSL'
SMTP_SERVER = 'smtp..com'
SMTP_SERVER_PORT = '465'
SMTP_SERVER_TYPE = 'SSL'


def send_email_smtp(message, recepient, sender, senderPassword, server=SMTP_SERVER, port=SMTP_SERVER_PORT, type=IMAP_SERVER_TYPE):
    if (type == 'SSL'):
        smtpObj = smtplib.SMTP(server)
        smtpObj.starttls()
    else:
        smtpObj = smtplib.SMTP(server, port)
    try:
        smtpObj.login(sender, senderPassword)
        smtpObj.sendmail(sender, recepient, message)         
        return "Successfully sent email to"+str(recepient)
    except SMTPException:
        return "Error: unable to send email"
