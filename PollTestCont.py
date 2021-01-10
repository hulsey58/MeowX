# Continuous Testing without saving data to a file

import RPi.GPIO as GPIO
import time

from datetime import datetime, timedelta


def generateFilenameTimestamp():
    return str(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

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


        if variable_part == 'SENSOR_PIN':
            SENSOR_PIN = int(value_part)



# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SENSOR_PIN, GPIO.IN)

record_length_seconds = 3
min_ms_between_polls = 0.094 # With overhead, 0.094 gives about 0.1 ms between samples

output_filename_base = '/home/pi/MeowX/Logs/poll_test_'
output_filename_ext = '.csv'

test_log_file_name = '{}{}{}'.format(output_filename_base, generateFilenameTimestamp(), output_filename_ext)

## input('Press enter to record for {} seconds...'.format(record_length_seconds))

print ('\nListening...')

while True:
    pin_values = []
    start_time = time.time()
    last_poll_time = time.time() - (min_ms_between_polls/1000)
    while True:
        if (time.time() - last_poll_time) * 1000 < min_ms_between_polls:
            continue

        pin_values.append(GPIO.input(SENSOR_PIN)) ## pin_values.append((time.time(), GPIO.input(SENSOR_PIN)))
        last_poll_time = time.time()
        if time.time() - start_time > record_length_seconds:
            break

    ## print ('Listening finished.')
    ## print ('Writing to file...')

    ## with open(test_log_file_name, 'w') as f:
    ##for i in range(len(pin_values)):
    ##    poll_time, poll_value = pin_values[i]
    ##    f.write('{}, {}\n'.format(poll_time-start_time, poll_value))
    ##    poll_value_sum = poll_value_sum + poll_value
        
    poll_value_sum = sum(pin_values)
    ## print ('Log written to {}'.format(test_log_file_name))
    detections = len(pin_values) - poll_value_sum # because 0 = detection, 1 = below threshold
    detection_rate = detections/record_length_seconds
    detection_percent = detections/len(pin_values)*100
    print ('{} detections/sec, {}% of the time'.format(detection_rate, detection_percent))

# input ('\n- Press enter to exit -')

# print ('----------------')
# for pin_value in pin_values:
#     print ('{}\t{}'.format(pin_value[0],pin_value[1]))

