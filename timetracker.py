#! /usr/local/bin/python3.6

import os
import re
import sys
import time
import yaml
import discord
from datetime import datetime, timedelta

# Create the bot client.
client = discord.Client()

# Used for localizing times.
LOCAL_UTC = None

# Global property variables.
BOT_NAME = 'TimeTracker'
BOT_APP_ID = None
BOT_TOKEN = None
SPEC_ROLE = 'Tracker'
LOG_URL = None
TIMEZONE = None
TIMESTAMP_FORMAT = None
CLOCK_IN_WORDS = ['In', 'On', 'Back']
CLOCK_OUT_WORDS = ['Out', 'Off']
RETRIEVABLE_MESSAGE_AMOUNT = 300

# Used in async functions to get message histories.
HISTORY = []
MEMBER_HISTORY = {}

# Contains members and their respective messages.
TRACKER = {}
BASE_TRACKER = {}

# Contains members and their respective invalid clocks.
INVALID_CLOCKS = {}

# Contains members and their respective single clocks.
SINGLE_CLOCKS = {}

# A file that contains invalid and single clock information for logging.
LOG_FILE = None

# Date variables used to filter messages.
FIRST_WEEK_START = None
FIRST_WEEK_END = None
SECOND_WEEK_START = None
SECOND_WEEK_END = None


# Read in global properties from properties.yml file.
def populate_global_properties():
    global LOCAL_UTC, BOT_NAME, BOT_APP_ID, BOT_TOKEN
    global SPEC_ROLE, LOG_URL, TIMEZONE, TIMESTAMP_FORMAT
    global CLOCK_IN_WORDS, CLOCK_OUT_WORDS, RETRIEVABLE_MESSAGE_AMOUNT
    if os.path.isfile('properties.yml'):
        stream = open('properties.yml')
        properties = yaml.load(stream)
        if len(properties) < 10:
            print('Missing properties in properties.yml file.')
            sys.exit()
        BOT_NAME = properties['name']
        BOT_APP_ID = properties['id']
        BOT_TOKEN = properties['token']
        SPEC_ROLE = properties['role']
        LOG_URL = properties['log-url']
        try:
            LOCAL_UTC = int(properties['local-utc'])
        except ValueError:
            print('Unable to parse UTC. Defaulting to -6.')
            LOCAL_UTC = -6
        TIMESTAMP_FORMAT = properties['timestamp-format']
        CLOCK_IN_WORDS = properties['in-words']
        CLOCK_OUT_WORDS = properties['out-words']
        try:
            RETRIEVABLE_MESSAGE_AMOUNT = int(properties['message-recall'])
        except ValueError:
            print(
                'Unable to parse RETRIEVABLE_MESSAGE_AMOUNT.'
                + 'Defaulting to ' + str(RETRIEVABLE_MESSAGE_AMOUNT)
            )


# Date and timestamp functions:

def set_dates(str_date):
    global FIRST_WEEK_START, FIRST_WEEK_END
    global SECOND_WEEK_START, SECOND_WEEK_END
    FIRST_WEEK_START = start_of_first_week(str_date)
    FIRST_WEEK_END = end_of_first_week()
    SECOND_WEEK_START = start_of_second_week()
    SECOND_WEEK_END = end_of_second_week()


def start_of_first_week(str_date):
    return datetime.strptime(str_date, '%m/%d/%y')


def end_of_first_week():
    return FIRST_WEEK_START + timedelta(days=6, hours=23, minutes=59)


def start_of_second_week():
    return FIRST_WEEK_START + timedelta(days=7)


def end_of_second_week():
    return FIRST_WEEK_START + timedelta(days=13, hours=23, minutes=59)


def in_datetime_range(dt):
    return FIRST_WEEK_START < dt < SECOND_WEEK_END


def within_first_week(timestamp):
    return FIRST_WEEK_START < timestamp < FIRST_WEEK_END


def format_message_timestamp(timestamp):
    return (timestamp + timedelta(hours=LOCAL_UTC)).strftime(TIMESTAMP_FORMAT)


def format_week_timestamp(timestamp):
    return timestamp.strftime('%m/%d/%y (%A)')


@client.event
async def on_ready():
    print('Successfully logged in as:', str(client.user)[:-5])
    print('Current time: ' + time.strftime('%X %x %Z'))


# Handles the bot's commands based on message received.
@client.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        command = message.content.lower()
        if not is_valid_command(command):
            return

        channel = message.channel
        if command.startswith('?timetracker'):
            author = message.author
            if not str(channel.type) == 'private':
                await client.delete_message(message)
            await client.send_message(author, list_commands())
            return

        if command.startswith('/clear'):
            if not str(channel.type) == 'private':
                await client.delete_message(message)
            await client.send_message(channel, 'Deleting messages . . .')
            logs = []
            async for log in client.logs_from(channel):
                if log.author.name == BOT_NAME:
                    logs.append(log)
            received = len(logs)
            while received > 0:
                tmp = []
                async for log in client.logs_from(channel):
                    if log.author.name == BOT_NAME:
                        tmp.append(log)
                        logs.append(log)
                received = len(tmp)
                for log in reversed(logs):
                    try:
                        await client.delete_message(log)
                        logs.remove(log)
                    except Exception as e:
                        if 'Unknown Message' not in str(e):
                            with open('error_log.txt', 'a') as error_log:
                                error_log.write(str(time.time()) + ': ' + str(e))
            return

        # Commands after this must be from a guild channel.
        if str(channel.type) == 'private':
            await client.send_message(
                channel, 'This command can only be used in a guild channel.'
            )
            return

        global HISTORY, MEMBER_HISTORY, TRACKER
        global BASE_TRACKER, INVALID_CLOCKS, SINGLE_CLOCKS

        if command.startswith('/clocks'):
            if valid_clocks_command(command):
                HISTORY = []
                MEMBER_HISTORY = {}
                command_user = message.author
                member = message.mentions[0]  # @name
                member_name = member.name
                if member.nick is not None:
                    member_name = member.nick
                await client.delete_message(message)

                args = command.split(' ')
                start_date = args[2]  # 'MM/dd/yy'
                set_dates(start_date)
                await get_member_history(member, channel)

                str_clocks = clocks_to_str_by_week(member, MEMBER_HISTORY[member])
                str_clocks = (
                    '__**' + member_name + '** (' + channel.name + '):__\n\n'
                    + format_week_timestamp(FIRST_WEEK_START)
                    + ' to ' + format_week_timestamp(FIRST_WEEK_END)
                    + ':\n\n' + str_clocks[0] + '\n'
                    + format_week_timestamp(SECOND_WEEK_START)
                    + ' to ' + format_week_timestamp(SECOND_WEEK_END)
                    + ':\n\n' + str_clocks[1]
                )
                if not len(str_clocks) > 2000:  # Character limit for Discord.
                    await client.send_message(command_user, str_clocks)
            else:
                await client.delete_message(message)
                error = 'Usage: /clocks @name mm/dd/yy'
                await client.send_message(message.author, error)

        if command.startswith('/times'):
            if has_spec_role(message.author):
                if valid_times_command(command):
                    HISTORY = []
                    MEMBER_HISTORY = {}
                    TRACKER = {}
                    BASE_TRACKER = {}
                    INVALID_CLOCKS = {}
                    SINGLE_CLOCKS = {}
                    command_user = message.author
                    await client.delete_message(message)
                    global LOG_FILE
                    LOG_FILE = open('log.txt', 'w')
                    args = command.split(' ')
                    start_date = args[1]  # 'MM/dd/yy'
                    set_dates(start_date)
                    await get_channel_history(channel)
                    times = get_times(channel)
                    for t in times:
                        if not len(t) > 2000:  # Character limit for Discord.
                            await client.send_message(command_user, t)
                    LOG_FILE.close()
                else:
                    error = 'Usage: /times mm/dd/yy'
                    await client.send_message(message.channel, error)
            else:
                await client.delete_message(message)
                error = 'You do not have permissions to use this command.'
                await client.send_message(message.author, error)

    except ValueError:
        with open('error_log.txt', 'w') as error_log:
            error_log.write(str(datetime.now().time()) + ': ' + str(sys.exc_info()) + '\n')
        print('An error occurred; check error_log.txt for more info.')
        pass


# Sets MEMBER_HISTORY to the member's history before SECOND_WEEK_END.
async def get_member_history(member, channel):
    history = []
    async for message in client.logs_from(
            channel, limit=RETRIEVABLE_MESSAGE_AMOUNT, after=FIRST_WEEK_START,
            reverse=True
    ):
        if message.mentions is not None:
            if len(message.mentions) > 0 and message.mentions[0] == member:
                history.append(message)
    # This while loop is needed to make sure
    # all messages are tested after async above.
    temp = len(history)
    while not temp == 0:
        test = temp
        for message in history:
            if not in_datetime_range(message.timestamp):
                history.remove(message)
        temp = len(history)
        if temp == test:
            temp = 0
    global MEMBER_HISTORY
    if member not in MEMBER_HISTORY:
        MEMBER_HISTORY[member] = history
    else:
        MEMBER_HISTORY[member] = history


# Sets HISTORY to the channel history before SECOND_WEEK_END.
async def get_channel_history(channel):
    history = []
    async for message in client.logs_from(
            channel, limit=RETRIEVABLE_MESSAGE_AMOUNT, after=FIRST_WEEK_START,
            reverse=True
    ):
        history.append(message)
    # This while loop is needed to make sure
    # all messages are tested after async above.
    temp = len(history)
    while not temp == 0:
        test = temp
        for message in history:
            if not in_datetime_range(message.timestamp):
                history.remove(message)
        temp = len(history)
        if temp == test:
            temp = 0
    global HISTORY
    HISTORY = history


# Converts a list of Discord messages into a single string.
# Returns a list containing each week's clocks.
def clocks_to_str_by_week(member, clocks):
    first_week = ''
    second_week = ''
    for clock in clocks:
        author = clock.author.name
        if clock.author.nick is not None:
            author = clock.author.nick
        member_name = member.name
        if member.nick is not None:
            member_name = member.nick
        content = clock.content
        replace_len = len(content.split('>')[0]) + 1
        if within_first_week(clock.timestamp):
            if clock.mentions[0] == member:
                first_week += (
                    format_message_timestamp(clock.timestamp)
                    + ' | ' + author + ': @' + member_name
                    + content[replace_len:] + '\n'
                )
        else:
            if clock.mentions[0] == member:
                second_week += (
                    format_message_timestamp(clock.timestamp)
                    + ' | ' + author + ': @' + member_name
                    + content[replace_len:] + '\n'
                )

    return [first_week, second_week]


def has_spec_role(member):
    for role in member.roles:
        if SPEC_ROLE in role.name:
            return True
    return False


def is_valid_command(command):
    return command.startswith('?') or command.startswith('/')


def valid_clocks_command(command):
    args = command.split(' ')
    if len(args) < 3:
        return False
    elif '@' not in args[1] or '/' not in args[-1]:
        return False
    else:
        date_parts = args[-1].split('/')
        for part in date_parts:
            if not is_integer(part):
                return False
    return True


def valid_times_command(command):
    args = command.split(' ')
    if len(args) < 2 or '/' not in args[1]:
        return False
    else:
        date_parts = args[1].split('/')
        for part in date_parts:
            if not is_integer(part):
                return False
    return True


def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def list_commands():
    message = (
        '__**Commands:**__\n```'
        + '/clear'
        + ' | Clears all messages from the bot'
        + ' in the channel the command was sent from.\n'
        + '/clocks @name mm/dd/yy'
        + ' | Sends the user clocks of the mentioned member.\n'
        + '/times mm/dd/yy'
        + ' | Sends the user clocks and times for all members.\n'
        + '?timetracker'
        + ' | Sends this list of commands to user.\n'
        + '```'
    )
    return message


def get_times(channel):
    for channel_member in client.get_all_members():
        update_tracker(channel_member)

    times = []
    for member in TRACKER:
        times.append(member_time_info(channel, member))

    return times


# Add members and their clocks to TRACKER.
def update_tracker(member):
    if member.bot:
        return

    member_clocks = []
    for message in HISTORY:
        if len(message.mentions) > 0:
            if message.mentions[0] == member:
                member_clocks.append(message)

    if member not in BASE_TRACKER:
        BASE_TRACKER[member] = []
    BASE_TRACKER[member] = member_clocks

    if len(member_clocks) > 0:
        update_clocks(member, member_clocks)


def update_clocks(member, member_clocks):
    for clock in member_clocks:
        converted = convert_clock(clock)
        clock_type = converted[0]
        quarter_time = converted[1]
        associate_clocks(member, clock, clock_type, quarter_time)


# Returns a list with the clock type and quarter_time.
def convert_clock(clock):
    value = ['Invalid', 0]
    has_in = contains_clock_in(clock)
    has_out = contains_clock_out(clock)

    if has_in and has_out:
        value = ['Invalid', 0]
    elif has_in:
        value = ['In', get_quarter_time(clock)]
    elif has_out:
        value = ['Out', get_quarter_time(clock)]

    return value


def contains_clock_in(clock):
    for in_word in CLOCK_IN_WORDS:
        if in_word.lower() in clock.content.lower():
            return True
    return False


def contains_clock_out(clock):
    for out_word in CLOCK_OUT_WORDS:
        if out_word.lower() in clock.content.lower():
            return True
    return False


# Handles parsing time.
def get_quarter_time(message):
    meridiem = ''
    content = message.content.lower()
    message_time = ''
    if content.endswith('am'):
        meridiem = 'am'
    if content.endswith('pm'):
        meridiem = 'pm'
    if ':' in content:
        colon_pos = content.index(':')
        time_start = content[colon_pos - 2:]
        message_time = time_start[:2] + time_start[2:][:3]
    else:
        try:
            time_spot = re.search(" \d\d\d\d", content)
            if time_spot is None:
                time_spot = re.search(" \d\d\d", content).start()
                time_start = content[time_spot:]
                message_time = time_start[:2] + ':' + time_start[2:][:2]
            else:
                time_spot = time_spot.start()
                time_start = content[time_spot + 1:]
                message_time = time_start[:2] + ':' + time_start[2:][:2]
        except ValueError:
            print('Could not get time for: ' + content)
    if is_integer(message_time[:2]) and is_integer(message_time[-2:]):
        return calc_quarter_time(message_time, meridiem)
    return 0


def calc_quarter_time(message_time, meridiem):
    if meridiem == '':
        return quarter_hour(message_time)
    else:
        if meridiem == 'am':
            return quarter_hour(message_time)
        else:
            hour = int(message_time[:2])
            minutes = message_time[-2:]
            if not hour == 12:
                hour += 12
            message_time = (str(hour) + ':' + minutes)
            return quarter_hour(message_time)


def quarter_hour(t):
    hour = float(t[:2])
    minutes = int(t[-2:])
    tens = int(minutes / 10)
    ones = int(minutes % 10)

    if tens == 0:
        if ones <= 7:
            ones = 0
        else:
            tens += 1
            ones = 5
    elif tens == 1:
        ones = 5
    elif tens == 2:
        if ones <= 3:
            tens -= 1
            ones = 5
        else:
            tens += 1
            ones = 0
    elif tens == 3:
        if ones <= 7:
            ones = 0
        else:
            tens += 1
            ones = 5
    elif tens == 4:
        ones = 5
    elif tens == 5:
        if ones <= 3:
            tens -= 1
            ones = 5
        else:
            hour += 1
            tens = 0
            ones = 0

    minutes = (tens * 10) + ones

    return hour + convert_minutes_to_quarter(minutes)


def convert_minutes_to_quarter(minutes):
    if minutes == 0:
        return 0
    if minutes == 15:
        return 0.25
    if minutes == 30:
        return 0.5
    if minutes == 45:
        return 0.75
    return 0


# Handles adding clock hashes to members in TRACKER.
def associate_clocks(member, message, clock_type, quarter_time):
    if member not in TRACKER:
        TRACKER[member] = []

    week = 2
    if within_first_week(message.timestamp):
        week = 1

    clock = {'Message': message, 'Week': week, clock_type: quarter_time}

    if clock_type == 'Out':
        if len(TRACKER[member]) > 0 and 'Out' not in TRACKER[member][-1]:
            TRACKER[member][-1].update(clock)
        else:
            update_single_clocks(member, message)

    if clock_type == 'In':
        for index, clock_key in enumerate(TRACKER[member]):
            if 'Out' not in clock_key:
                del (TRACKER[member][index])
                update_single_clocks(member, message)
        TRACKER[member].append(clock)

    if clock_type == 'Invalid':
        update_invalid_clocks(member, message)


def update_single_clocks(member, message):
    if member not in SINGLE_CLOCKS:
        SINGLE_CLOCKS[member] = []
    SINGLE_CLOCKS[member].append(message)


def update_invalid_clocks(member, message):
    if member not in INVALID_CLOCKS:
        INVALID_CLOCKS[member] = []
    INVALID_CLOCKS[member].append(message)


# Creates a string that contains a member's time info.
def member_time_info(channel, member):
    clocks = BASE_TRACKER[member]
    hours = hours_of_weeks(member)
    clocks_by_week = clocks_to_str_by_week(member, clocks)

    first_week_hours = hours[0]
    second_week_hours = hours[1]

    member_name = member.name
    if member.nick is not None:
        member_name = member.nick

    return (
        '__**' + member_name + '** (' + channel.name + '):__\n\n'
        + clocks_by_week[0] + '\n'
        + format_week_timestamp(FIRST_WEEK_START) + ' - '
        + format_week_timestamp(FIRST_WEEK_END) + ': '
        + str(first_week_hours) + ' hours'
        + '\n\n'
        + clocks_by_week[1] + '\n'
        + format_week_timestamp(SECOND_WEEK_START) + ' - '
        + format_week_timestamp(SECOND_WEEK_END) + ': '
        + str(second_week_hours) + ' hours'
        + '\n\n'
        + 'Total: '
        + str(first_week_hours + second_week_hours)
        + ' hours\n'
        + error_check(member)
        + '---------------\n'
    )


def hours_of_weeks(member):
    first_week_clocks = []
    second_week_clocks = []
    for clock in TRACKER[member]:
        if clock['Week'] == 1:
            first_week_clocks.append(clock)
        else:
            second_week_clocks.append(clock)

    first_week_hours = calc_week_hours(first_week_clocks)
    second_week_hours = calc_week_hours(second_week_clocks)

    return [first_week_hours, second_week_hours]


def calc_week_hours(week_clocks):
    total = 0.0
    if len(week_clocks) > 0:
        print(week_clocks[0])
    for clock in week_clocks:
        if 'Out' in clock and 'In' in clock:
            total += (clock['Out'] - clock['In'])
    return total


def error_check(member):
    error = 'Hours calculated may be invalid due to:\n'
    base_len = len(error)
    has_invalids = has_invalid_clocks(member)
    has_singles = has_single_clocks(member)

    if has_invalids and has_singles:
        error += 'Having single or incorrectly formatted clocks.\n'
    elif has_invalids:
        error += 'Invalid format for clocks.\n'
    elif has_singles:
        error += 'Single clocks.\n'
    else:
        error = ''

    if has_invalids or has_singles:
        error += 'Check ' + str(LOG_URL) + ' for more info.\n'

    if len(error) > base_len:
        log_errors(member, has_invalids, has_singles)

    return error


def has_invalid_clocks(member):
    return member in INVALID_CLOCKS


def has_single_clocks(member):
    return member in SINGLE_CLOCKS


def log_errors(member, has_invalids, has_singles):
    member_name = member.name
    if member.nick is not None:
        member_name = member.nick

    if has_invalids or has_singles:
        LOG_FILE.write('<hr>')
        LOG_FILE.write(member_name + "'(s) clock errors:\n\n")
    if has_invalids:
        LOG_FILE.write('Invalid Clocks:\n')
        for invalid in INVALID_CLOCKS[member]:
            LOG_FILE.write(format_message(member, invalid) + '\n')
        LOG_FILE.write('\n')
    if has_singles:
        LOG_FILE.write('Single Clocks:\n')
        for single in SINGLE_CLOCKS[member]:
            LOG_FILE.write(format_message(member, single) + '\n')
        LOG_FILE.write('\n')
    LOG_FILE.write('\n')


def format_message(member, message):
    author = message.author.name
    if message.author.nick is not None:
        author = message.author.nick
    member_name = member.name
    if member.nick is not None:
        member_name = member.nick
    content = message.content
    replace_len = len(content.split('>')[0]) + 1
    return (
        format_message_timestamp(message.timestamp)
        + ' | ' + author + ': @' + member_name
        + content[replace_len:]
    )

# Get the bot's properties then start it.
populate_global_properties()
client.run(BOT_TOKEN)
