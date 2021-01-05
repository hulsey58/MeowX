# Listens for cat meows by detecting loud sounds at night with the right frequency
# Logs to 2 files - one with timestamps of sounds, one that shows sounds per minute (or per 5-min interval) for each minute

# ** Use restarter script on pi to monitor this script


# Current version: v0.1.0a

# Changelog:
# v0.1.0 - Split settings out into SETTINGS.txt file which is loaded at the beginning
# v0.0.3 - Added missed import SimpleMessage, updated to record all sounds on the rise, replaced F strings with format()


import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import os
import pygame

from random import choice

import time

import SimpleMessage



def getSoundList():
    # Returns list of sounds in ./Sounds directory
    SOUNDS_DIRECTORY = '/home/pi/MeowX/Sounds'
    sound_list = [os.path.join(SOUNDS_DIRECTORY, f) for f in os.listdir(SOUNDS_DIRECTORY) if os.path.isfile(os.path.join(SOUNDS_DIRECTORY, f))]
    return sound_list


def generateTimestamp():
    return str(datetime.now().strftime("%Y-%m-%d|%H:%M:%S"))

def generateFilenameTimestamp():
    return str(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

def convertTimeToTimestamp(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d|%H:%M:%S")


def currentTimeWithinRange():
    # Returns if the current time is within the monitoring range or not

    year, month, day, hour, minute = map(int, datetime.now().strftime("%Y %m %d %H %M").split())

    now = datetime.now()
    today_start_time = now.replace(hour=MONITOR_START_HOUR, minute=MONITOR_START_MINUTE, second=0, microsecond=0)
    tomorrow_end_time = now.replace(hour=MONITOR_END_HOUR, minute=MONITOR_END_MINUTE, second=0, microsecond=0)
    tomorrow_end_time += timedelta(days=1)

  #  print ('NOW:')
  #  print (now)
  #  print (today_start_time)
  #  print (tomorrow_end_time)
  #  print ('----------')

    if now < today_start_time:
        return False
    if now > tomorrow_end_time:
        return False

    return True


def callback(channel):
    global last_sound_time
    global sound_events

    # Called only on rising now
    print ('Sound!  {}s since last'.format(round(time.time() - last_sound_time),2))
    sound_events.append((time.time(), time.time() - last_sound_time))
    last_sound_time = time.time()

    #if GPIO.input(channel):
    #        print ('--- Sound start ---')
    #        last_sound_time = time.time()
    #else:
    #        print ('--- Sound end ---')
    #        sound_events.append((time.time(), time.time() - last_sound_time))

       ##     # Check if length of meow
       ##     sound_duration = time.time() - last_sound_time

       ##     if abs(sound_duration - MEOW_DURATION_AVG) <= MEOW_DURATION_RANGE:
       ##         print (f'Meow detected - Sound length: {round(sound_duration,2)}s')
       ##         meow_events.append(f'{generateTimestamp()}, {sound_duration}\n')

       ##     else:
       ##         print (f'Not a meow - Sound length: {round(sound_duration,2)}s')


def playSound(path, wait_until_done = False, play_over_other_sound = False):
    if pygame.mixer.music.get_busy():
        if not play_over_other_sound:
            print ('Another sound is currently playing')
            return

    print ('Loading sound...')
    pygame.mixer.music.load(path)
    print ('Playing sound...')
    pygame.mixer.music.play()

    if wait_until_done:
        for event in pygame.event.get():
            if event.type == SOUND_END:
                print ('The sound ended!')
                return
    else:
        return


def playRandomSound():
    sound_choice = choice(SOUND_LIST)
    print ('Random sound chosen: {}'.format(sound_choice))
    playSound(sound_choice)
    return sound_choice

def stopSound():
    pygame.mixer.music.stop()
# -------------------------------------------------------------------------------------------------------------------

def emailLogs(event_log_file_name_to_send = 'current', time_log_file_name_to_send = 'current'):
    # Sends both logs via email
    # TODO: Attach both logs to the same email

    if event_log_file_name_to_send == 'current':
        subject = '[MeowX] Log file - Events'
        message_text = 'Log file of events from MeowX'
        SimpleMessage.sendMessage(sender=DEFAULT_SENDER, to=TO_EMAIL_ADDRESS, subject=subject,
                                  message_text=message_text, attached_file=event_log_file_name)
    else:
        subject = '[MeowX] Log file - Meow Counts - {}'.format(event_log_file_name_to_send)
        message_text = 'Log file of meow counts per minute from MeowX'
        SimpleMessage.sendMessage(sender=DEFAULT_SENDER, to=TO_EMAIL_ADDRESS, subject=subject,
                                  message_text=message_text, attached_file=event_log_file_name_to_send)

    if time_log_file_name_to_send == 'current':
        subject = '[MeowX] Log file - Meow Counts'
        message_text = 'Log file of meow counts per minute from MeowX'
        SimpleMessage.sendMessage(sender=DEFAULT_SENDER, to=TO_EMAIL_ADDRESS, subject=subject,
                                  message_text=message_text, attached_file=time_log_file_name)
    else:
        subject = '[MeowX] Log file - Meow Counts - {}'.format(time_log_file_name_to_send)
        message_text = 'Log file of meow counts per minute from MeowX'
        SimpleMessage.sendMessage(sender=DEFAULT_SENDER, to=TO_EMAIL_ADDRESS, subject=subject,
                                  message_text=message_text, attached_file=time_log_file_name_to_send)


class Logger():
    def __init__(self, log_path):
        self.log_path = log_path
        self.log_cache = []
        self.last_log_added = 0

        self.last_write_time = 0
        self.min_s_between_writes = 15

        if not self.log_exists():
            self.create_log()

    def time_stamp(self):
        return str(datetime.now().strftime("%Y-%m-%d|%H:%M:%S"))

    def log_exists(self):
        return os.path.exists(self.log_path)

    def create_log(self):
        open(self.log_path, 'w').close()

    def log(self, log_string):
        self.last_log_added = time.time()
        log_line = '{}{}\n'.format(self.time_stamp(), log_string)
        self.log_cache.append(log_line)
        self.flush_if_time()

    def add_line(self, line):
        self.last_log_added = time.time()
        self.log_cache.append(line)
        self.flush_if_time()

    def add_lines(self, event_list):
        self.last_log_added = time.time()
        self.log_cache += event_list
        self.flush_if_time()

    def flush_if_time(self):
        if time.time() - self.last_write_time > self.min_s_between_writes:
            self.flush()


    def flush(self):
        if self.log_cache:
            with open(self.log_path, 'a') as f:
                for line in self.log_cache:
                    f.write(line)

            print ('Log cache written to file')

            self.log_cache = []
            self.last_write_time = time.time()

    def final_flush(self):
        self.flush()






# Load Settings
SETTINGS_FILE_PATH = '/home/pi/MeowX/SETTINGS.txt'
with open(SETTINGS_FILE_PATH, 'r') as f:
    for settings_line_raw in f:

        settings_line = settings_line_raw.strip('\n')

        if not settings_line:
            continue

        if settings_line.startswith('#'):
            continue

        variable_part, the_rest = settings_line.split('=')

        if the_rest.startswith("'"):
            # The rest is a string, read until the next '
            value_part = ''
            for char in the_rest[1:]:
                if char == "'":
                    break
                value_part += char
        else:
            # The rest is an integer or boolean and may have a comment at the end.  Split at the first space, if there is one
            if ' ' in the_rest:
                value_part = the_rest.split(' ')[0]
            else:
                # No space or comments, the_rest is a value (int or boolean)
                value_part = the_rest

        #print('Variable: |{}|'.format(variable_part))
        #print('Value: |{}|'.format(value_part))
        #print('--------------')

        if variable_part == 'SENSOR_PIN':
            SENSOR_PIN = int(value_part)
        elif variable_part == 'BLUE_LED_PIN':
            BLUE_LED_PIN = int(value_part)
        elif variable_part == 'YELLOW_LED_PIN':
            YELLOW_LED_PIN = int(value_part)
        elif variable_part == 'BUTTON_PIN':
            BUTTON_PIN = int(value_part)
        elif variable_part == 'TRIGGER_HIGH_PIN':
            TRIGGER_HIGH_PIN = int(value_part)
        elif variable_part == 'TRIGGER_LOW_PIN':
            TRIGGER_LOW_PIN = int(value_part)
        elif variable_part == 'MEOW_DURATION_AVG':
            MEOW_DURATION_AVG = float(value_part)
        elif variable_part == 'MEOW_DURATION_RANGE':
            MEOW_DURATION_RANGE = float(value_part)
        elif variable_part == 'NUMBER_OF_MEOWS_TO_TRIGGER':
            NUMBER_OF_MEOWS_TO_TRIGGER = int(value_part)
        elif variable_part == 'TRIGGER_WATCH_SECONDS':
            TRIGGER_WATCH_SECONDS = int(value_part)
        elif variable_part == 'TRIGGER_HOLD_DURATION':
            TRIGGER_HOLD_DURATION = float(value_part)
        elif variable_part == 'MAX_TRIGGERS_PER_MINUTE':
            MAX_TRIGGERS_PER_MINUTE = int(value_part)
        elif variable_part == 'MAX_TRIGGERS_PER_15_MIN':
            MAX_TRIGGERS_PER_15_MIN = int(value_part)
        elif variable_part == 'MAX_TRIGGERS_PER_DAY':
            MAX_TRIGGERS_PER_DAY = int(value_part)
        elif variable_part == 'EVENT_LOG_FILE_NAME_BASE':
            EVENT_LOG_FILE_NAME_BASE = value_part
        elif variable_part == 'TIME_LOG_FILE_NAME_BASE':
            TIME_LOG_FILE_NAME_BASE = value_part
        elif variable_part == 'LOG_FILE_EXT':
            LOG_FILE_EXT = value_part
        elif variable_part == 'LOG_DURATION_HOURS':
            LOG_DURATION_HOURS = int(value_part)
        elif variable_part == 'EMAIL_LOGS_ENABLED':
            if value_part.lower() == 'true':
                EMAIL_LOGS_ENABLED = True
            else:
                EMAIL_LOGS_ENABLED = False
        elif variable_part == 'EMAIL_LOGS_FREQUENCY_HOURS':
            EMAIL_LOGS_FREQUENCY_HOURS = int(value_part)
        elif variable_part == 'TO_EMAIL_ADDRESS':
            TO_EMAIL_ADDRESS = value_part
        elif variable_part == 'MONITOR_START_HOUR':
            MONITOR_START_HOUR = int(value_part)
        elif variable_part == 'MONITOR_START_MINUTE':
            MONITOR_START_MINUTE = int(value_part)
        elif variable_part == 'MONITOR_END_HOUR':
            MONITOR_END_HOUR = int(value_part)
        elif variable_part == 'MONITOR_END_MINUTE':
            MONITOR_END_MINUTE = int(value_part)
        elif variable_part == 'FORCE_MONITORING_ON':
            if value_part.lower() == 'true':
                FORCE_MONITORING_ON = True
            else:
                FORCE_MONITORING_ON = False

################################################################################

DEFAULT_SENDER = 'autosecretary.p2p@gmail.com'  # Can't be easily changed


# DEBUG - TESTING EMAIL --------------------------
#emailLogs('/home/pi/MeowX/fake-log-1.txt', '/home/pi/MeowX/fake-log-2.txt')
#print ('Fake logs emailed, sleeping...')
#time.sleep(99999)
# ------------------------------------------------



event_log_file_name = '{}{}{}'.format(EVENT_LOG_FILE_NAME_BASE, generateFilenameTimestamp(), LOG_FILE_EXT)
time_log_file_name = '{}{}{}'.format(TIME_LOG_FILE_NAME_BASE, generateFilenameTimestamp(), LOG_FILE_EXT)

SOUND_LIST = getSoundList()  # Gets list of sounds in ./Sounds directory

last_button_press_time = time.time() # Sound test button
BUTTON_DEBOUNCE = 2  # Button debounce in seconds

last_sound_time = time.time()
meow_events = []

sound_events = []  # All sound events, including meows

trigger_times = []
trigger_turned_on_time = None  # Used to hold trigger

# Create logs
event_log = Logger(event_log_file_name)
time_log = Logger(time_log_file_name)
last_log_creation_time = time.time()

# Set last email sent time to now
last_email_sent_time = time.time()

# Init Pygame for sound and clock ----------
# Setup mixer to avoid sound lag - TODO: Do I need this?
# pygame.mixer.pre_init(44100, -16, 2, 2048)
print('Initializing PyGame...')
pygame.init()
print('Initializing mixer...')
pygame.mixer.init()

SOUND_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SOUND_END)

pyclock = pygame.time.Clock()  # TODO: Not currently used, do I need this?
# ----------------------------------------


# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SENSOR_PIN, GPIO.IN)
#GPIO.add_event_detect(SENSOR_PIN, GPIO.BOTH, bouncetime=100)  # Old way when trying to detect meow length
GPIO.add_event_detect(SENSOR_PIN, GPIO.RISING, bouncetime=100)
GPIO.add_event_callback(SENSOR_PIN, callback)

GPIO.setup(BLUE_LED_PIN, GPIO.OUT)
GPIO.setup(YELLOW_LED_PIN, GPIO.OUT)

GPIO.setup(TRIGGER_HIGH_PIN, GPIO.OUT)
GPIO.setup(TRIGGER_LOW_PIN, GPIO.OUT)

GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


meow_count = 0
meow_count_duration = 60  # Count total meow per meow_count_duration seconds (eg per minute)
meow_count_last_save = time.time()

recent_meow_times = []

if currentTimeWithinRange():
    print ('Current time within monitor range')
else:
    print ('Current time not within monitor range')

if FORCE_MONITORING_ON:
    print ('Force monitor is ON - Monitoring outside set range')

# TODO: Do I need this?
#min_time_between_loops_ms = 1000  # Non-blocking loop limiter, passes if not time

running = True
while running:
    if currentTimeWithinRange() or FORCE_MONITORING_ON:
        GPIO.output(BLUE_LED_PIN, GPIO.HIGH)


        # TODO: TEMP DEBUG - there are no meow_events, only sound_events

        # Read events_to_write to detect trigger
        if meow_events:

            # Add newly detected meows to meow_count and recent_meow_times
            for meow_event in meow_events:
                meow_count += 1  # Used for count per hour
                recent_meow_times.append(meow_event[0])

            # Throw out old meow times
            recent_meow_times = [x for x in recent_meow_times if time.time() - x <= TRIGGER_WATCH_SECONDS]

            if len(recent_meow_times) >= NUMBER_OF_MEOWS_TO_TRIGGER:

                # Check trigger limits ---------------
                triggers_in_last_minute = 0
                triggers_in_last_15_min = 0
                triggers_in_last_day = 0

                for trigger_time in trigger_times:
                    time_diff = time.time() - trigger_time
                    if time_diff <= 60:
                        triggers_in_last_minute += 1
                        triggers_in_last_15_min += 1
                        triggers_in_last_day += 1
                    elif time_diff <= 60*15:
                        triggers_in_last_15_min += 1
                        triggers_in_last_day += 1
                    elif time_diff <= 24 * 3600:
                        triggers_in_last_day += 1

                if triggers_in_last_minute > MAX_TRIGGERS_PER_MINUTE:
                    print ('Too many triggers in the last minute! Triggers: {}, Limit: {}'.format(triggers_in_last_minute, MAX_TRIGGERS_PER_MINUTE))
                elif triggers_in_last_15_min > MAX_TRIGGERS_PER_15_MIN:
                    print ('Too many triggers in the last minute! Triggers: {}, Limit: {}'.format(triggers_in_last_15_min, MAX_TRIGGERS_PER_15_MIN))
                elif triggers_in_last_day > MAX_TRIGGERS_PER_DAY:
                    print ('Too many triggers in the last minute! Triggers: {}, Limit: {}'.format(triggers_in_last_day, MAX_TRIGGERS_PER_DAY))
                else:
                    # Trigger event
                    trigger_times.append(time.time())
                    random_sound_played = playRandomSound()
                    event_log.add_line('{},"trigger",{}\n'.format(meow_timestamp, random_sound_played))
                    GPIO.output(YELLOW_LED_PIN, GPIO.HIGH)
                    trigger_turned_on_time = time.time()

                    GPIO.output(TRIGGER_HIGH_PIN, GPIO.HIGH)
                    GPIO.output(TRIGGER_LOW_PIN, GPIO.LOW)

                # ------------------------------------

            # Log 1: Log sound events with timestamp
            for meow_event in meow_events:
                meow_time_unconverted, meow_length = meow_event

                meow_timestamp = convertTimeToTimestamp(meow_time_unconverted)
                meow_length = round(meow_length, 2)
                event_log.add_line('{},"meow",{}\n'.format(meow_timestamp, meow_length))

            # Reset meow_events after reading
            meow_events = []



        if sound_events:
            #print ('SOUND EVENTS FOUND')
            # TODO: Use these to detect meows in the loop rather than detecting in the callback

            # Log 1: Log sound events with timestamp
            for sound_event in sound_events:
                # TODO: Debugging - Counting all sounds in meow_count.  Rename this if you still want to use it
                meow_count += 1  # Used for count per hour

                sound_time_unconverted, sound_length = sound_event

                sound_timestamp = convertTimeToTimestamp(sound_time_unconverted)
                sound_length = round(sound_length, 2)
                event_log.add_line('{},"sound",{}\n'.format(sound_timestamp, sound_length))

                print ('Cache size: {}'.format(len(event_log.log_cache)))


            # Reset sound_events after reading
            sound_events = []
        #else:
        #    print ('...')


        # TODO: Temporarily writing sound count for meow count
        # Log 2: Log total sounds per minute, even if there are 0
        if time.time() - meow_count_last_save >= meow_count_duration:
            # Write number of meows in this duration to 2nd log file
            print ('Adding meow counts to log...')
            meow_count_last_save = time.time()
            time_log.add_line('{}, {}\n'.format(convertTimeToTimestamp(time.time()), meow_count))
            #time_log.log(meow_count)
            meow_count = 0
        #else:
        #    print ('Time since last save: {}'.format(round(time.time() - meow_count_last_save, 2)))


    else:
        # Ignore events while not in monitoring time range
        GPIO.output(BLUE_LED_PIN, GPIO.LOW)
        GPIO.output(YELLOW_LED_PIN, GPIO.LOW)
        meow_events = []


    # Turn off trigger after trigger hold time, if on
    if trigger_turned_on_time:
        if time.time() - trigger_turned_on_time >= TRIGGER_HOLD_DURATION:
            GPIO.output(TRIGGER_HIGH_PIN, GPIO.LOW)
            GPIO.output(TRIGGER_LOW_PIN, GPIO.HIGH)
            trigger_turned_on_time = None


    # Flush logs to file if time (each log stores its own last flushed time)
    event_log.flush_if_time()
    time_log.flush_if_time()

    # Send logs if time
    if EMAIL_LOGS_ENABLED:
        seconds_since_last_email = time.time() - last_email_sent_time
        if seconds_since_last_email >= EMAIL_LOGS_FREQUENCY_HOURS * 3600:
            # Send email
            try:
                emailLogs()
            except:
                print ('Emailing logs failed!')

            last_email_sent_time = time.time()


    # Start new logs if time
    if time.time() - last_log_creation_time >= LOG_DURATION_HOURS * 3600:
        last_log_creation_time = time.time()

        event_log_file_name = '{}{}{}'.format(EVENT_LOG_FILE_NAME_BASE, generateFilenameTimestamp(), LOG_FILE_EXT)
        time_log_file_name = '{}{}{}'.format(TIME_LOG_FILE_NAME_BASE, generateFilenameTimestamp(), LOG_FILE_EXT)

        event_log.final_flush()
        time_log.final_flush()

        # Create logs
        event_log = Logger(event_log_file_name)
        time_log = Logger(time_log_file_name)


    # Check for sound test button
    if GPIO.input(BUTTON_PIN) == 0:
        if time.time() - last_button_press_time > BUTTON_DEBOUNCE:
            last_button_press_time = time.time()
            print ('!!!!!!!!!!! Button pressed !!!!!!!!!!!!!!')
            #playRandomSound()  # TODO: Disabled for now while debugging pygame

    # Loop delay
    #pyclock.tick(run_delay)