# Listens for cat meows by detecting loud sounds at night with the right frequency
# Logs to 1 file - timestamp of time chunk, detection cycles/second, and percent of time with sound detection

# ** Use restarter script on pi to monitor this script


Current_version = 'v0.3.8'


# Changelog:
# v0.3.8 - Fixed bug of not clearing "times", added fine time to event logs, added log headers, added lines to resume sampling when TimeToRun goes from false to true.
# v0.3.7 - Took currentTimeWithinRange calculation out of the polling loop to try speeding it up
# v0.3.6 - Expanded application of test for no samples to the other processing steps that would crash without samples
# v0.3.5 - Fixed bug in writing times to event log. Now each chunk starts with full date and time followed by seconds of offset from that time
# v0.3.4 - Added test to prevent divide by 0 and dump of chunk data to event log once per hour
# v0.3.3 - Fixed timestamp and log detections during meows according to cycles/sec
# v0.3.2 - Minor code cleanup
# v0.3.1 - Updated to single log file in format: time, detection rate, detection percent, rate triggered, percent triggered
# v0.3.0 - Changed from interrupts to polling
# v0.2.0 - Put chunk size and test limits in settings file. Added calculations for detection cycles/second
# v0.1.1 - Took vertical bar out of datetime format and used that same format for both log files
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
    return str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def generateFilenameTimestamp():
    return str(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))


def convertTimeToTimestamp(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def convertTimeToFineTimestamp(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S.%f")


def currentTimeWithinRange():
    # Returns if the current time is within the monitoring range or not

    year, month, day, hour, minute = map(int, datetime.now().strftime("%Y %m %d %H %M").split())

    now = datetime.now()
    today_start_time = now.replace(hour=MONITOR_START_HOUR, minute=MONITOR_START_MINUTE, second=0, microsecond=0)
    tomorrow_end_time = now.replace(hour=MONITOR_END_HOUR, minute=MONITOR_END_MINUTE, second=0, microsecond=0)
    tomorrow_end_time += timedelta(days=1)

    if now < today_start_time:
        return False
    if now > tomorrow_end_time:
        return False

    return True


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
        self.min_s_between_writes = 5

        if not self.log_exists():
            self.create_log()

    def time_stamp(self):
        return str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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
        elif variable_part == 'TIME_CHUNK_SIZE':
            TIME_CHUNK_SIZE = float(value_part)
        elif variable_part == 'DET_PERCENT_THRESH':
            DET_PERCENT_THRESH = float(value_part)
        elif variable_part == 'DET_CYCLES_THRESH':
            DET_CYCLES_THRESH = float(value_part)


################################################################################

DEFAULT_SENDER = 'autosecretary.p2p@gmail.com'  # Can't be easily changed

FilenameTimestamp = generateFilenameTimestamp()
time_log_file_name = '{}{}{}'.format(TIME_LOG_FILE_NAME_BASE, FilenameTimestamp, LOG_FILE_EXT)
event_log_file_name = '{}{}{}'.format(EVENT_LOG_FILE_NAME_BASE, FilenameTimestamp, LOG_FILE_EXT)

SOUND_LIST = getSoundList()  # Gets list of sounds in ./Sounds directory

last_button_press_time = time.time() # Sound test button
BUTTON_DEBOUNCE = 2  # Button debounce in seconds


trigger_times = []
trigger_turned_on_time = None  # Used to hold trigger

# Create logs
time_log = Logger(time_log_file_name)
time_log.add_line('Time Log {},,,, Generated by MeowX {}\n'.format(FilenameTimestamp, Current_version))
time_log.add_line('\n')
time_log.add_line('DateTime, Cycle/sec, % Det., Samples, >{} Hz, >{}%\n'.format(DET_CYCLES_THRESH, DET_PERCENT_THRESH))

event_log = Logger(event_log_file_name)
event_log.add_line('Event Log {},,,, Generated by MeowX {}\n'.format(FilenameTimestamp, Current_version))
event_log.add_line('\n')
event_log.add_line('DateTime, Sec After, Pin Value\n')

last_log_creation_time = time.time()

# Set last email sent time to now
last_email_sent_time = time.time()

# Init Pygame for sound  ---------------
# Setup mixer to avoid sound lag - TODO: Do I need this?
# pygame.mixer.pre_init(44100, -16, 2, 2048)
print('Initializing PyGame...')
pygame.init()
print('Initializing mixer...')
pygame.mixer.init()

SOUND_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SOUND_END)

# ----------------------------------------


# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SENSOR_PIN, GPIO.IN)

GPIO.setup(BLUE_LED_PIN, GPIO.OUT)
GPIO.setup(YELLOW_LED_PIN, GPIO.OUT)

GPIO.setup(TRIGGER_HIGH_PIN, GPIO.OUT)
GPIO.setup(TRIGGER_LOW_PIN, GPIO.OUT)

GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


if currentTimeWithinRange():
    print ('Current time within monitor range')
else:
    print ('Current time not within monitor range')

if FORCE_MONITORING_ON:
    print ('Force monitor is ON - Monitoring outside set range')


record_length_seconds = TIME_CHUNK_SIZE
min_ms_between_polls = 0.094 # With overhead, 0.094 gives about 0.1 ms between samples


record_start_time = time.time()  # Used with record_length_seconds
last_poll_time = time.time() - min_ms_between_polls
last_hour = time.localtime().tm_hour
currently_recording = True
times = []
pin_values = []
last_pin_value = 1
cycles = 0
rate_triggered = 0
percent_triggered = 0
TimeToRun = currentTimeWithinRange() or FORCE_MONITORING_ON
running = True
while running:
    if TimeToRun:
        # Monitoring on
        GPIO.output(BLUE_LED_PIN, GPIO.HIGH)

        if currently_recording:
            # Check if time to stop recording
            if time.time() - record_start_time >= record_length_seconds:
                currently_recording = False
            else:
                # Check if time to read pin
                if time.time() - last_poll_time >= min_ms_between_polls / 1000:
                    new_pin_value = GPIO.input(SENSOR_PIN)
                    last_poll_time = time.time()
                    times.append(last_poll_time)
                    pin_values.append(new_pin_value)
                    if last_pin_value == 1 and new_pin_value == 0:
                        cycles = cycles + 1
                    last_pin_value = new_pin_value



        else:
            # Recording just ended, read values
            poll_value_sum = sum(pin_values)
            detections = len(pin_values) - poll_value_sum  # because 0 = detection, 1 = below threshold
            cycle_rate = cycles / record_length_seconds

            
            if len(pin_values) == 0:   # Added because sometimes it crashes due to no samples collected.
                print('WARNING: len(pin_values) = 0')
                detection_percent = 0
                cycle_rate = 0
                event_log.add_line('{}, , WARNING: len(pin_values) = 0\n'.format(convertTimeToFineTimestamp(time.time())))


            else:
                detection_percent = detections / len(pin_values) * 100
                print('{} cycles/sec, detections {}% of the time'.format(cycle_rate, detection_percent))


                # Dump detection data from current chunk to event log once an hour
                hour = time.localtime().tm_hour
                if hour > last_hour:
                    # Dump detection data from current chunk to event log
                    event_log.add_line('{}\n'.format(convertTimeToFineTimestamp(times[0])))
                    for i in range(len(pin_values)):
                        event_log.add_line(', {}, {}\n'.format(times[i] - times[0], pin_values[i]))
                    if hour < 23:
                        last_hour = hour
                    else:
                        last_hour = -1


                # Check for a possible meow based on cycle rate
                if cycle_rate >= DET_CYCLES_THRESH:
                    # print ('Detection cycles above threshold: Rate: {}, Thresh: {}'.format(cycle_rate, DET_CYCLES_THRESH))
                    rate_triggered = 1
                    # Dump detection data from current chunk to event log
                    event_log.add_line('{}\n'.format(convertTimeToFineTimestamp(times[0])))
                    for i in range(len(pin_values)):
                        event_log.add_line(', {}, {}\n'.format(times[i] - times[0], pin_values[i]))
                    

                # Check for a possible meow based on detection percent
                if detection_percent >= DET_PERCENT_THRESH:
                    # print ('Detection percent above threshold: %: {}, Thresh: {}'.format(detection_percent, DET_PERCENT_THRESH))
                    percent_triggered = 1


            time_log.add_line('{}, {}, {}, {}, {}, {}\n'.format(convertTimeToTimestamp(time.time()), cycle_rate, detection_percent, len(pin_values), rate_triggered, percent_triggered))


            # Reset values
            times = []
            pin_values = []
            cycles = 0
            rate_triggered = 0
            percent_triggered = 0
            last_poll_time = time.time() - min_ms_between_polls

            # Record again
            currently_recording = True
            TimeToRun = currentTimeWithinRange() or FORCE_MONITORING_ON
            record_start_time = time.time()

    else:
        # Monitoring off
        GPIO.output(BLUE_LED_PIN, GPIO.LOW)
        TimeToRun = currentTimeWithinRange() or FORCE_MONITORING_ON
        record_start_time = time.time()


