# Takes the place of SimpleSMS and SimpleMMS for sending texts and emails through Gmail
###################################################
# Sends text messages and messages with attachments
# Works with email addresses and cell phone gateway addresses

# Hard-coded for autosecretary@gmail.com
# New credentials file would need to be created for a different account,
# as well as setting up the API in the new Google Account


# Combined examples taken from:


# pip install google-api-python-client

# Removed oauth2client and replaced with loading credentials stored in a pickle file

# Current version: v0.1


# v0.1 # Converted style and formatting


import httplib2
import os
import base64

import smtplib
import mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# List of all mimetype per extension: http://help.dottoro.com/lapuadlp.php  or http://mime.ritey.com/

from apiclient import errors, discovery  #needed for gmail service

import pickle
from googleapiclient.discovery import build

import time


def createGmailSession():
    # Load credentials
    if not os.path.exists('token.pickle'):
        return None
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)

    # Initialize authorized gmail API session
    service = build('gmail', 'v1', credentials=creds)
    return service



## Get creds, prepare message and send it
def sendMessage(sender, to, subject, message_text = None, attached_file = None):
    # Set attached_file to None to send without attachment

    # Load credentials and initiate gmail api instance
    service = createGmailSession()

    if attached_file:
        ## Send message with attachment
        # Create message
        message_with_attachment = createMessageWithAttachment(sender, to, subject, message_text, attached_file)
        # Send message
        sendMessageWithAttachment(service, "me", message_with_attachment, message_text, attached_file)
    else:
        ## Send message without attachment
        # Create message
        message_without_attachment = createMessageWithoutAttachment(sender, to, subject, message_text)
        # Send message
        sendMessageWithoutAttachment(service, "me", message_without_attachment, message_text)



def createMessageWithoutAttachment(sender, to, subject, message_text):
    #Create message container
    message = MIMEMultipart('alternative') # needed for both plain & HTML (the MIME type is multipart/alternative)
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = to

    # TODO: Handle html text differently - detect if the text is formatted and decide how to send it
    # For now, just send

    #Create the body of the message (a plain-text and an HTML version)
    if message_text:
        message.attach(MIMEText(message_text, 'plain'))
        message.attach(MIMEText(message_text, 'html'))

    raw_message_no_attachment = base64.urlsafe_b64encode(message.as_bytes())
    raw_message_no_attachment = raw_message_no_attachment.decode()   # TODO: Combine with previous line and test
    body  = {'raw': raw_message_no_attachment}
    return body



def createMessageWithAttachment(sender, to, subject, message_text, attached_file):
    # Create a message with attachment


    ##An email is composed of 3 part :
        #part 1: create the message container using a dictionary { to, from, subject }
        #part 2: attach the message_text with .attach() (could be plain and/or html)
        #part 3(optional): an attachment added with .attach()

    ## Part 1
    message = MIMEMultipart() #when alternative: no attach, but only plain_text
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject


    ## Part 2   (the message_text)

    # -----------
    # TODO: Handle html text differently - detect if the text is formatted and decide how to send it
    # For now, just send
    # ------------------


    # The order count: the first (html) will be use for email, the second will be attached (unless you comment it)

    # Leave off message completely if it's blank - adds 2 new line chars for some reason - TODO:  Find what causes the new lines and remove them
    if message_text:
        message.attach(MIMEText(message_text, 'html'))
    #message.attach(MIMEText(message_text, 'plain'))

    ## Part 3 (attachment)
    # # to attach a text file you containing "test" you would do:
    # # message.attach(MIMEText("test", 'plain'))

    #-----About MimeTypes:
    # It tells gmail which application it should use to read the attachment (it acts like an extension for windows).
    # If you dont provide it, you just wont be able to read the attachment (eg. a text) within gmail. You'll have to download it to read it (windows will know how to read it with it's extension).

    #-----3.1 get MimeType of attachment
        #option 1: if you want to attach the same file just specify it’s mime types

        #option 2: if you want to attach any file use mimetypes.guess_type(attached_file)

    my_mimetype, encoding = mimetypes.guess_type(attached_file)

    # If the extension is not recognized it will return: (None, None)
    # If it's an .mp3, it will return: (audio/mp3, None) (None is for the encoding)
    #for unrecognized extension it set my_mimetypes to  'application/octet-stream' (so it won't return None again).
    if my_mimetype is None or encoding is not None:
        my_mimetype = 'application/octet-stream'


    main_type, sub_type = my_mimetype.split('/', 1)# split only at the first '/'
    # if my_mimetype is audio/mp3: main_type=audio sub_type=mp3

    #-----3.2  creating the attachment
        #you don't really "attach" the file but you attach a variable that contains the "binary content" of the file you want to attach

        #option 1: use MIMEBase for all my_mimetype (cf below)  - this is the easiest one to understand
        #option 2: use the specific MIME (ex for .mp3 = MIMEAudio)   - it's a shorcut version of MIMEBase

    #this part is used to tell how the file should be read and stored (r, or rb, etc.)
    if main_type == 'text':
        print("text")
        temp = open(attached_file, 'r')  # 'rb' will send this error: 'bytes' object has no attribute 'encode'
        attachment = MIMEText(temp.read(), _subtype=sub_type)
        temp.close()

    elif main_type == 'image':
        print("image")
        temp = open(attached_file, 'rb')
        attachment = MIMEImage(temp.read(), _subtype=sub_type)
        temp.close()

    elif main_type == 'audio':
        print("audio")
        temp = open(attached_file, 'rb')
        attachment = MIMEAudio(temp.read(), _subtype=sub_type)
        temp.close()

    elif main_type == 'application' and sub_type == 'pdf':
        temp = open(attached_file, 'rb')
        attachment = MIMEApplication(temp.read(), _subtype=sub_type)
        temp.close()

    else:
        attachment = MIMEBase(main_type, sub_type)
        temp = open(attached_file, 'rb')
        attachment.set_payload(temp.read())
        temp.close()

    #-----3.3 encode the attachment, add a header and attach it to the message
    # encoders.encode_base64(attachment)  #not needed (cf. randomfigure comment)
    #https://docs.python.org/3/library/email-examples.html

    filename = os.path.basename(attached_file)
    attachment.add_header('Content-Disposition', 'attachment', filename=filename) # name preview in email
    message.attach(attachment)


    ## Part 4 encode the message (the message should be in bytes)
    message_as_bytes = message.as_bytes() # the message should converted from string to bytes.
    message_as_base64 = base64.urlsafe_b64encode(message_as_bytes) #encode in base64 (printable letters coding)
    raw = message_as_base64.decode()  # need to JSON serializable (no idea what does it means)
    return {'raw': raw}



def sendMessageWithoutAttachment(service, user_id, body, message_text):
    # Sends message created without attachment (create message first)
    try:
        message_sent = (service.users().messages().send(userId=user_id, body=body).execute())
        message_id = message_sent['id']
        # print(attached_file)
        print ('Message sent \n\n Message Id: {}\n\n Message:\n\n {}'.format(message_id, message_text))
        # return body
    except errors.HttpError as error:
        print ('An error occurred: {}'.format(error))




def sendMessageWithAttachment(service, user_id, message_with_attachment, message_text, attached_file):
    # Sends message created with attachment (create message first)
    try:
        message_sent = (service.users().messages().send(userId=user_id, body=message_with_attachment).execute())
        message_id = message_sent['id']
        # print(attached_file)
        print ('Message sent \n\n Message Id: {}\n\n Message:\n\n {} \n\n Attached file:{}'.format(message_id, message_text, attached_file))

        # return message_sent
    except errors.HttpError as error:
        print ('An error occurred: {}'.format(error))

