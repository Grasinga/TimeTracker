import discord
from discord.ext import commands

import os
import re
import sys
import yaml
from datetime import datetime, timedelta

properties_file_path = 'TimeTracker_Properties.yml'

# ----- Global properties defined in the properties file -----

EXCEPTION_LOG = './default_exceptions.txt'
CLOCK_LOG = './default_clock_exceptions.txt'
BOT_TOKEN = ''
CMD_PREFIX = ''
PROTECTED_ROLE = 'Tracker'
LOCAL_UTC = -7
DAYLIGHT_SAVINGS = False
MESSAGE_TIMESTAMP_FORMAT = ''
WEEK_TIMESTAMP_FORMAT = ''
CLOCK_IN_WORDS = []
CLOCK_OUT_WORDS = []
RETRIEVABLE_MESSAGE_AMOUNT = 300

# ----- Global properties not defined in the properties file -----

BOT = None
FIRST_WEEK_START = datetime.now()
FIRST_WEEK_END = datetime.now()
SECOND_WEEK_START = datetime.now()
SECOND_WEEK_END = datetime.now()
SINGLE_CLOCKS = {}
INVALID_CLOCKS = {}


# Read in global properties from properties file.
def initialize_bot():
    if os.path.isfile(properties_file_path):
        properties = yaml.load(open(properties_file_path))

        global EXCEPTION_LOG, CLOCK_LOG, BOT_TOKEN, CMD_PREFIX, PROTECTED_ROLE, LOCAL_UTC, DAYLIGHT_SAVINGS, \
            MESSAGE_TIMESTAMP_FORMAT, WEEK_TIMESTAMP_FORMAT, CLOCK_IN_WORDS, CLOCK_OUT_WORDS, \
            RETRIEVABLE_MESSAGE_AMOUNT

        try:
            EXCEPTION_LOG = properties['exception-log']
            if EXCEPTION_LOG is None or EXCEPTION_LOG == '':
                EXCEPTION_LOG = 'TimeTracker_Exception_Log.txt'
                exception_log_write('WARNING',
                                    'An exception log path was not specified; using default value: {}'
                                    .format(EXCEPTION_LOG))
        except KeyError as ke:
            EXCEPTION_LOG = 'TimeTracker_Exception_Log.txt'
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, EXCEPTION_LOG))
            pass

        try:
            CLOCK_LOG = properties['clock-log']
            if CLOCK_LOG is None or CLOCK_LOG == '':
                CLOCK_LOG = 'Clock_Exceptions_Log.txt'
                exception_log_write('WARNING',
                                    'An exception log path was not specified; using default value: {}'
                                    .format(EXCEPTION_LOG))
        except KeyError as ke:
            CLOCK_LOG = 'Clock_Exceptions_Log.txt'
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, CLOCK_LOG))
            pass

        try:
            BOT_TOKEN = properties['token']
            if BOT_TOKEN is None or BOT_TOKEN == '':
                exception_log_write('CRITICAL',
                                    'A bot Token was not specified.')
        except KeyError as ke:
            exception_log_write('CRITICAL',
                                '{} property is missing in the properties file.'.format(ke))
            pass

        try:
            CMD_PREFIX = properties['prefix']
            if CMD_PREFIX is None or CMD_PREFIX == '':
                CMD_PREFIX = '/'
                exception_log_write('WARNING',
                                    'A command prefix was not specified; using default value: {}'
                                    .format(CMD_PREFIX))
        except KeyError as ke:
            CMD_PREFIX = '/'
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, CMD_PREFIX))
            pass

        try:
            PROTECTED_ROLE = properties['role']
            if PROTECTED_ROLE is None or PROTECTED_ROLE == '':
                PROTECTED_ROLE = 'Tracker'
                exception_log_write('WARNING',
                                    'A protected commands role name was not specified; using default value: {}'
                                    .format(PROTECTED_ROLE))
        except KeyError as ke:
            PROTECTED_ROLE = 'Tracker'
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, PROTECTED_ROLE))
            pass

        try:
            LOCAL_UTC = int(properties['local-utc'])
        except TypeError:
            LOCAL_UTC = -7
            exception_log_write('WARNING',
                                'Unable to get the local UTC from the value provided; using default value: {}'
                                .format(LOCAL_UTC))
        except KeyError as ke:
            LOCAL_UTC = -7
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, LOCAL_UTC))
            pass

        try:
            DAYLIGHT_SAVINGS = properties['daylight-savings']
            if DAYLIGHT_SAVINGS is None:
                DAYLIGHT_SAVINGS = True
                exception_log_write('WARNING', 'Daylight Savings not specified; using default value: {}'
                                    .format(DAYLIGHT_SAVINGS))
        except KeyError as ke:
            DAYLIGHT_SAVINGS = True
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, DAYLIGHT_SAVINGS))
            pass

        try:
            MESSAGE_TIMESTAMP_FORMAT = properties['message-timestamp-format']
            if MESSAGE_TIMESTAMP_FORMAT is None or MESSAGE_TIMESTAMP_FORMAT == '':
                MESSAGE_TIMESTAMP_FORMAT = "%m/%d/%y (%A) @ %I:%M %p"
                exception_log_write('WARNING',
                                    'Message Timestamp Format not specified; using default value: {}'
                                    .format(MESSAGE_TIMESTAMP_FORMAT))
        except KeyError as ke:
            MESSAGE_TIMESTAMP_FORMAT = "%m/%d/%y (%A) @ %I:%M %p"
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, MESSAGE_TIMESTAMP_FORMAT))
            pass

        try:
            WEEK_TIMESTAMP_FORMAT = properties['week-timestamp-format']
            if WEEK_TIMESTAMP_FORMAT is None or WEEK_TIMESTAMP_FORMAT == '':
                WEEK_TIMESTAMP_FORMAT = "%m/%d/%y (%A)"
                exception_log_write('WARNING',
                                    'Week Timestamp Format not specified; using default value: {}'
                                    .format(WEEK_TIMESTAMP_FORMAT))
        except KeyError as ke:
            WEEK_TIMESTAMP_FORMAT = "%m/%d/%y (%A)"
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, WEEK_TIMESTAMP_FORMAT))
            pass

        try:
            CLOCK_IN_WORDS = properties['in-words']
            if CLOCK_IN_WORDS is None or len(CLOCK_IN_WORDS) == 0:
                CLOCK_IN_WORDS = ['In', 'Back']
                exception_log_write('WARNING',
                                    'Clock in words not specified; using default values: {}'
                                    .format(CLOCK_IN_WORDS))
        except KeyError as ke:
            CLOCK_IN_WORDS = ['In', 'Back']
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default values: {}'
                                .format(ke, CLOCK_IN_WORDS))
            pass

        try:
            CLOCK_OUT_WORDS = properties['out-words']
            if CLOCK_OUT_WORDS is None or len(CLOCK_OUT_WORDS) == 0:
                CLOCK_OUT_WORDS = ['Out', 'Off']
                exception_log_write('WARNING',
                                    'Clock in words not specified; using default values: {}'
                                    .format(CLOCK_OUT_WORDS))
        except KeyError as ke:
            CLOCK_OUT_WORDS = ['Out', 'Off']
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default values: {}'
                                .format(ke, CLOCK_OUT_WORDS))
            pass

        try:
            RETRIEVABLE_MESSAGE_AMOUNT = int(properties['message-recall'])
        except TypeError:
            RETRIEVABLE_MESSAGE_AMOUNT = 300
            exception_log_write('WARNING',
                                'Unable to get the message recall amount from the value provided; '
                                'using default value: {}'
                                .format(RETRIEVABLE_MESSAGE_AMOUNT))
        except KeyError as ke:
            RETRIEVABLE_MESSAGE_AMOUNT = 300
            exception_log_write('WARNING',
                                '{} property is missing in the properties file; using default value: {}'
                                .format(ke, RETRIEVABLE_MESSAGE_AMOUNT))
            pass

        # Updates the bot to use the specified command prefix and creates the client.
        # Disabling the help_attrs allows for custom help commands.
        global BOT
        BOT = commands.Bot(command_prefix=CMD_PREFIX, help_attrs={'disabled': True})

        print('Exception Log File Path: {}'.format(EXCEPTION_LOG))
        print('Command Prefix: {}'.format(CMD_PREFIX))
        print('Protected Command Role: {}'.format(PROTECTED_ROLE))
        print('Clock Log Path: {}'.format(CLOCK_LOG))
        print('Local UTC: {}'.format(LOCAL_UTC))
        print('Daylight Savings: {}'.format(DAYLIGHT_SAVINGS))
        print('Message Timestamp Format: {}'.format(MESSAGE_TIMESTAMP_FORMAT))
        print('Week Timestamp Format: {}'.format(WEEK_TIMESTAMP_FORMAT))
        print('Clock-in Words: {}'.format(CLOCK_IN_WORDS))
        print('Clock-out Words: {}'.format(CLOCK_OUT_WORDS))
        print('Retrievable Message Amount: {}'.format(RETRIEVABLE_MESSAGE_AMOUNT))
        print()
    else:
        exception = 'Properties file does not exist at {}.'.format(properties_file_path)
        exception_log_write('CRITICAL', exception)


# Handles exception logging and stopping the program if a critical exception is passed.
def exception_log_write(warning_type, exception, channel=None):
    message = '{} | {}: {}\n'.format(datetime.now(), warning_type, exception)
    with open(EXCEPTION_LOG, 'a') as exception_log:
        exception_log.write(message)

    if BOT is not None and channel is not None:
        BOT.send_message(channel, message)
    else:
        print(message)

    if warning_type == 'CRITICAL':
        try:
            BOT.close()
        except Exception as ex:
            print(ex)
            pass
        sys.exit()


initialize_bot()


class Clock:
    def __init__(self, discord_message):
        self.error = None
        self.raw = discord_message
        self.author = discord_message.author
        self.message = discord_message.content
        self.channel = discord_message.channel
        self.timestamp = discord_message.timestamp
        try:
            if len(discord_message.mentions) > 1:
                self.error = 'Too many mentions.'
            else:
                self.member = discord_message.mentions[0]
        except IndexError:
            self.error = 'Missing mention.'
            return
        self.type = self.get_clock_type()
        if len(self.type) > 3:
            self.error = 'Unknown clock type.'
        self.value = self.get_quarter_time()
        if not is_integer(self.value):
            self.error = self.value
        if self.error is not None:
            self.type = 'Invalid'  # Clock will get added to invalids during association.

    def get_clock_type(self):
        words = self.message.split(' ')
        for word in words:
            if word.title() in CLOCK_IN_WORDS:
                return 'In'
            elif word.title() in CLOCK_OUT_WORDS:
                return 'Out'
        return 'Missing clock type key word.'

    def get_quarter_time(self):
        # Check for the time in the message.
        time_spot = re.search(" \d\d\d\d", self.message)
        if time_spot is None:
            time_spot = re.search(" \d\d\d", self.message)
            if time_spot is None:
                time_spot = re.search(" \d\d:\d\d", self.message)
                if time_spot is None:
                    time_spot = re.search(" \d:\d\d", self.message)
                    if time_spot is None:
                        return "Unable to find the clock's time."
                    else:
                        time_spot = time_spot.start()
                        time_count = 4
                        requires_meridiem = True
                else:
                    time_spot = time_spot.start()
                    time_count = 5
                    requires_meridiem = True
            else:
                time_spot = time_spot.start()
                time_count = 3
                requires_meridiem = False
        else:
            time_spot = time_spot.start()
            time_count = 4
            requires_meridiem = False

        # Get the clock's meridiem if required.
        meridiem = ''
        time_start = self.message[time_spot + 1:]  # Index of time without the space.
        if requires_meridiem:
            words = time_start.split(' ')
            if len(words) <= 1:
                meridiem = time_start[time_count:][:2].lower()
                if not (meridiem == 'am' or meridiem == 'pm'):
                    return 'Missing meridiem.'
            else:
                meridiem = words[1]

            if not len(meridiem) == 2:
                return 'Unexpected meridiem.'

        # Get the time without the meridiem or the rest of the message.
        time_start = time_start[:time_count]

        # Prepend leading zero if it is missing.
        if time_count == 3 or (time_count == 4 and ':' in time_start):
            time_start = '0' + time_start

        # Get the hours.
        hour = time_start[:2]
        if int(hour) > 12 and requires_meridiem:
            return 'Invalid military time.'

        # Get the minutes.
        minutes = time_start[-2:]
        if int(minutes) >= 60:
            return 'Minutes must be less than 60.'

        # Check if the hours and minutes are numeric values and then calculate the quarter time.
        if is_integer(hour) and is_integer(minutes):
            return self.__calc_quarter_time__(hour, minutes, meridiem)
        return "Unable to calculate the clock's time."

    def __calc_quarter_time__(self, hour, minutes, meridiem):
        if meridiem.lower() == '' or meridiem.lower() == 'am':
            return self.__quarter_hour__(hour, minutes)
        else:
            hour = int(hour)
            if not hour == 12:
                hour += 12
            return self.__quarter_hour__(hour, minutes)

    def __quarter_hour__(self, hour, minutes):
        hour = float(hour)
        minutes = int(minutes)
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

        return hour + self.__convert_minutes_to_quarter__(minutes)

    @staticmethod
    def __convert_minutes_to_quarter__(minutes):
        if minutes == 0:
            return 0
        if minutes == 15:
            return 0.25
        if minutes == 30:
            return 0.5
        if minutes == 45:
            return 0.75
        return 0


# ----- Events -----


@BOT.event
async def on_ready():
    print('Successfully logged in as:', BOT.user.name)
    print('Add me to a server via: https://discordapp.com/api/oauth2/authorize?client_id={}&scope=bot&permissions=8'
          .format(BOT.user.id))

    # Make sure the bot has admin privileges on all servers it is attached to.
    # Overarching permissions error protection.
    for server in BOT.servers:
        bot_member = server.get_member(BOT.user.id)
        if bot_member is not None:
            if not bot_member.server_permissions.administrator:
                # Kills the bot for all servers if the bot does not have admin permissions on one of them. (Lazy)
                exception_log_write('CRITICAL',
                                    'The bot needs administrator privileges to run on: {}'.format(server.name))

    # Adjust local UTC for daylight savings.
    if DAYLIGHT_SAVINGS:
        global LOCAL_UTC
        LOCAL_UTC -= 1


@BOT.event
async def on_message(message):
    if message.author.bot:  # Ignore bots trying to run commands.
        return

    if valid_help_command(message)['valid']:  # Check if the help command was entered.
        if message.channel.type is not discord.ChannelType.private:
            await BOT.delete_message(message)  # Keep channel clean.
        await help_info(message.author)  # Send bot info and commands to the user.
        return

    # Needed for any @BOT.command() methods to work.
    await BOT.process_commands(message)

    if message.channel.type is not discord.ChannelType.private:
        if message.content.startswith(CMD_PREFIX):
            try:
                await BOT.delete_message(message)  # Keep channel clean.
            except discord.NotFound:
                pass
        else:
            await flag_invalid_clock(message)  # Add a reaction to invalid clocks.


@BOT.event
async def on_message_edit(before, after):
    if before.author.bot or after.author.bot:  # Ignore message changes by bots.
        return

    if after.channel.type is not discord.ChannelType.private:
        await flag_invalid_clock(after)  # Add a reaction to invalid clocks; or remove reaction on fixed clock.


# ----- Commands -----


@BOT.command(pass_context=True)
async def clocks(ctx):
    command = valid_clocks_command(ctx.message)
    if command['valid']:
        # Wipe previous missing and invalid clocks.
        global SINGLE_CLOCKS, INVALID_CLOCKS
        SINGLE_CLOCKS = {}
        INVALID_CLOCKS = {}

        # Get values needed before message deletion.
        author = ctx.message.author
        member = ctx.message.mentions[0]
        channel = ctx.message.channel
        cmd_args = ctx.message.content.split(' ')
        start_date = cmd_args[2]  # 'MM/dd/yy'

        # Keep channel clean.
        await BOT.delete_message(ctx.message)

        # Clear the clock logs.
        with open(CLOCK_LOG, 'w') as log_file:
            log_file.write('')

        clock_data = await get_clocks_and_hours(member, channel, start_date)

        message_content = get_message_content(channel, member, clock_data)
        if len(message_content) == 0:
            await BOT.send_message(author, 'Unable to get message content.')
        else:
            for message in message_content:
                await BOT.send_message(author, message)
    else:
        await BOT.send_message(ctx.message.author, 'An error occurred when trying to run the command:\n{}'
                               .format(command['error']))
        await BOT.delete_message(ctx.message)


@BOT.command(pass_context=True)
async def times(ctx):
    command = valid_times_command(ctx.message)
    if command['valid']:
        # Wipe previous missing and invalid clocks.
        global SINGLE_CLOCKS, INVALID_CLOCKS
        SINGLE_CLOCKS = {}
        INVALID_CLOCKS = {}

        # Get values to needed before message deletion.
        author = ctx.message.author
        channel = ctx.message.channel
        cmd_args = ctx.message.content.split(' ')
        start_date = cmd_args[1]  # 'MM/dd/yy'

        # Keep channel clean.
        await BOT.delete_message(ctx.message)

        # Clear the clock logs.
        with open(CLOCK_LOG, 'w') as log_file:
            log_file.write('')

        # Get the members in alphabetical order based on Discord name.
        members_alpha = []
        for member in channel.server.members:
            if member.nick is not None:
                members_alpha.append(' '.join(reversed(member.nick.split(' '))))
            else:
                members_alpha.append(' '.join(reversed(member.name.split(' '))))
        members_alpha.sort()

        # Get the members in alphabetical order based on Discord member.
        members = []
        for am in members_alpha:
            am = ' '.join(reversed(am.split(' ')))
            for member in channel.server.members:
                if member.nick is not None:
                    if member.nick.lower() == am.lower():
                        members.append(member)
                else:
                    if member.name.lower() == am.lower():
                        members.append(member)

        # Get clocks for each member.
        for member in members:
            clock_data = await get_clocks_and_hours(member, channel, start_date)

            first_week_clocks = clock_data['clocks']['first-week']
            second_week_clocks = clock_data['clocks']['second-week']
            # Only do the following if the member had clocks.
            if (len(first_week_clocks) + len(second_week_clocks)) > 0:
                message_content = get_message_content(channel, member, clock_data)
                if len(message_content) == 0:
                    await BOT.send_message(author, 'Unable to get message content.')
                else:
                    for message in message_content:
                        await BOT.send_message(author, message)
    else:
        await BOT.send_message(ctx.message.author, 'An error occurred when trying to run the command:\n{}'
                               .format(command['error']))
        await BOT.delete_message(ctx.message)


@BOT.command(pass_context=True)
async def clear(ctx):
    command = valid_clear_command(ctx.message)
    if command['valid']:
        message = ctx.message
        channel = message.channel

        # Keep channel clean.
        if message.channel.type is not discord.ChannelType.private:
            await BOT.delete_message(message)

        # Get the bot's message history.
        history = []
        async for log in BOT.logs_from(channel):
            if log.author.name == BOT.user.name:
                history.append(log)

        # Get the amount of messages and notify the user.
        received = len(history)
        notification = await BOT.send_message(channel, 'Deleting {} message(s) . . .'.format(received))

        # While there are still messages to delete; delete them and update message count.
        while received > 0:
            received = len(history)
            for log in reversed(history):
                try:
                    await BOT.delete_message(log)
                    history.remove(log)
                    await BOT.edit_message(notification, 'Deleting {} message(s) . . .'.format(len(history)))
                except discord.NotFound:
                    pass

        # Delete the notification message when finished.
        await BOT.delete_message(notification)
    else:
        await BOT.send_message(ctx.message.author, 'An error occurred when trying to run the command:\n{}'
                               .format(command['error']))
        await BOT.delete_message(ctx.message)


# ----- Main Logic -----


# Returns a dictionary of discord clocks and hours of the weeks.
async def get_clocks_and_hours(member, channel, start_date):
    set_dates(start_date)

    # Get the messages that mentions the given member in the given channel.
    history = await get_member_history(member, channel)

    # Get the Clocks from the message history.
    discord_clocks = convert_history_to_clocks(history)

    # Get the hours of each week.
    week_hours = hours_of_weeks(discord_clocks)

    # Return clock data.
    return {'clocks': discord_clocks, 'hours': week_hours}


# Gets the member's history.
async def get_member_history(member, channel):
    history = []
    async for message in BOT.logs_from(
            channel, limit=RETRIEVABLE_MESSAGE_AMOUNT, after=FIRST_WEEK_START,
            reverse=True
    ):
        if message.mentions is not None and len(message.mentions) > 0 and message.mentions[0] == member:
            history.append(message)

    # This while loop is needed to make sure
    # all messages are tested after async above.
    temp = len(history)
    while not temp == 0:
        test = temp
        for message in history:
            if not within_pay_period(message.timestamp):
                history.remove(message)
        temp = len(history)
        if temp == test:
            temp = 0

    return history


# Converts the list of messages to a dictionary of first and second week Clocks.
def convert_history_to_clocks(history):
    first_week_clocks = []
    second_week_clocks = []
    for message in history:
        clock = Clock(message)
        if within_first_week(clock.timestamp):
            first_week_clocks.append(clock)
        else:
            second_week_clocks.append(clock)
    return {'first-week': first_week_clocks, 'second-week': second_week_clocks}


# Returns a dictionary that contains the hours worked for each week.
def hours_of_weeks(discord_clocks):
    first_week_clocks = associate_clocks(discord_clocks['first-week'])
    second_week_clocks = associate_clocks(discord_clocks['second-week'])

    first_week_hours = calc_week_hours(first_week_clocks)
    second_week_hours = calc_week_hours(second_week_clocks)

    return {'first-week': first_week_hours, 'second-week': second_week_hours}


# Helps calculate the hours by associating a clock-in with a clock-out. Also populates SINGLE/INVALID_CLOCKS.
def associate_clocks(discord_clocks):
    global SINGLE_CLOCKS, INVALID_CLOCKS
    if len(discord_clocks) == 0:
        return []
    member = discord_clocks[0].member
    associated_clocks = []
    try:
        for dc in discord_clocks:
            if dc.type == 'Out':
                if len(associated_clocks) > 0:
                    if associated_clocks[-1] is not None and associated_clocks[-1]['Out'] is None:
                        associated_clocks[-1]['Out'] = dc
                    else:
                        # Single clock-out
                        if member not in SINGLE_CLOCKS:
                            SINGLE_CLOCKS[member] = []
                        SINGLE_CLOCKS[member].append(dc)
                else:
                    # Single clock-out
                    if member not in SINGLE_CLOCKS:
                        SINGLE_CLOCKS[member] = []
                    SINGLE_CLOCKS[member].append(dc)
            elif dc.type == 'In':
                associated_clocks.append({'In': dc, 'Out': None})
            else:
                # Invalid clock
                if member not in INVALID_CLOCKS:
                    INVALID_CLOCKS[member] = []
                INVALID_CLOCKS[member].append(dc)
    except IndexError as ie:
        exception_log_write('WARNING', 'An exception occurred when trying to associate clocks: {}'.format(ie))
        pass
    except KeyError as ke:
        exception_log_write('WARNING', 'An exception occurred when trying to associate clocks: {}'.format(ke))
        pass

    valid_clocks = []
    try:
        for ac in associated_clocks:
            if ac['Out'] is not None:
                valid_clocks.append(ac)
            else:
                # Single clock-in
                if member not in SINGLE_CLOCKS:
                    SINGLE_CLOCKS[member] = []
                SINGLE_CLOCKS[member].append(ac['In'])
    except KeyError as ke:
        exception_log_write('WARNING', 'An exception occurred when trying to associate clocks: {}'.format(ke))
        pass

    return valid_clocks


# Calculates the difference between an out and in time for each clock of the week; then it totals them.
def calc_week_hours(week_clocks):
    total = 0.0
    try:
        for dc in week_clocks:
            total += (dc['Out'].value - dc['In'].value)
    except KeyError as ke:
        exception_log_write('WARNING', "An exception occurred when trying to calculate the week's hours: {}".format(ke))
        pass
    return total


# Converts the clock_data into a string to send as a message.
def get_message_content(channel, member, clock_data):
    member_name = member.name
    if member.nick is not None:
        member_name = member.nick

    # Check if the member had invalid or single clocks.
    errors = ''
    if member in INVALID_CLOCKS.keys():
        errors += 'Hours calculated may be invalid due to invalid clocks.\n'
        log_invalids(member_name, member)
    if member in SINGLE_CLOCKS.keys():
        errors += 'Hours calculated may be invalid due to single clocks.\n'
        log_singles(member_name, member)

    # Create the pay period string and include errors above.
    main_info = 'Pay Period: **{} to {}**\nTotal Hours: **{}**\n{}'.format(
        format_week_timestamp(FIRST_WEEK_START),
        format_week_timestamp(SECOND_WEEK_END),
        (clock_data['hours']['first-week'] + clock_data['hours']['second-week']),
        errors
    )

    # Get the clocks of the weeks as strings.
    first_week_clocks = clocks_as_string(clock_data['clocks']['first-week'])
    second_week_clocks = clocks_as_string(clock_data['clocks']['second-week'])

    # Get member's name for use in message content string.
    if member.nick is not None:
        member = member.nick
    else:
        member = member.name

    # Build the message content string.
    message_content = (
            '__**' + member + '** (' + channel.name + '):__\n\n'
            + main_info + '\n'
            + format_week_timestamp(FIRST_WEEK_START) + ' to ' + format_week_timestamp(FIRST_WEEK_END)
            + ': ' + str(clock_data['hours']['first-week']) + ' hours\n'
            + '```\n' + first_week_clocks + '\n```\n'
            + format_week_timestamp(SECOND_WEEK_START) + ' to ' + format_week_timestamp(SECOND_WEEK_END)
            + ': ' + str(clock_data['hours']['second-week']) + ' hours\n'
            + '```\n' + second_week_clocks + '\n```'
    )

    # Split the message if it is greater than 2000 characters.
    if len(message_content) > 2000:  # Message length limit from Discord API.
        message_content = split_message_content(message_content, first_week_clocks, second_week_clocks)
    else:
        message_content = [message_content]

    return message_content


# Converts a week's clocks into a string.
def clocks_as_string(clocks_of_week):
    week = ''
    for clock in clocks_of_week:
        # Get the name of the clock's sender.
        author = clock.author
        if author is None:
            author = 'Unknown'
        elif author.nick is not None:
            author = author.nick
        else:
            author = author.name

        # Get the name of the member the clock pertains to.
        member = clock.member
        if member is None:
            member = 'Unknown'
        elif member.nick is not None:
            member = member.nick
        else:
            member = member.name

        # Index after mention.
        replace_len = len(clock.message.split('>')[0]) + 1

        # Create the message string with the formatted message timestamp.
        week += (
                format_message_timestamp(clock.timestamp)
                + ' | ' + author + ': @' + member
                + clock.message[replace_len:] + '\n'
        )

    if len(week) == 0:
        return ' '  # Needed for empty code block.
    return week


# Splits the message into two.
def split_message_content(message_content, first_week_clocks, second_week_clocks):
    # Remove the week clocks to split easier.
    message_content = message_content.replace(first_week_clocks, '')
    message_content = message_content.replace(second_week_clocks, '')

    # Build the two message strings from split.
    parts = message_content.split('\n')
    parts[:] = [x for x in parts if x != '']
    parts[:] = [x for x in parts if x != '```']
    try:
        section_heading = ''
        section_one = ''
        section_two = ''
        if len(parts) == 5:
            section_heading = '{}\n\n{}\n{}\n'.format(parts[0], parts[1], parts[2])
            section_one = (parts[3] + '```' + first_week_clocks + '```')
            section_two = (parts[4] + '```' + second_week_clocks + '```')
        if len(parts) == 6:
            section_heading = '{}\n\n{}\n{}\n{}\n'.format(parts[0], parts[1], parts[2], parts[3])
            section_one = (parts[4] + '```' + first_week_clocks + '```')
            section_two = (parts[5] + '```' + second_week_clocks + '```')
        if len(parts) == 7:
            section_heading = '{}\n\n{}\n{}\n{}\n{}\n'.format(parts[0], parts[1], parts[2], parts[3], parts[4])
            section_one = (parts[5] + '```' + first_week_clocks + '```')
            section_two = (parts[6] + '```' + second_week_clocks + '```')
        return [section_heading, section_one, section_two]
    except IndexError:
        exception_log_write('WARNING', 'Unable to split message content. Did the original message change?')

    return []


# ----- Date and Timestamp Functions -----


# Sets the pay period dates.
def set_dates(str_date):
    global FIRST_WEEK_START, FIRST_WEEK_END, SECOND_WEEK_START, SECOND_WEEK_END
    FIRST_WEEK_START = start_of_first_week(str_date)
    FIRST_WEEK_END = end_of_first_week()
    SECOND_WEEK_START = start_of_second_week()
    SECOND_WEEK_END = end_of_second_week()


# Returns the first day of the first week as a datetime.
def start_of_first_week(str_date):
    return datetime.strptime(str_date, '%m/%d/%y')


# Returns the last day of the first week as a datetime.
def end_of_first_week():
    return FIRST_WEEK_START + timedelta(days=6, hours=23, minutes=59)


# Returns the first day of the second week as a datetime.
def start_of_second_week():
    return FIRST_WEEK_START + timedelta(days=7)


# Returns the last day of the second week as a datetime.
def end_of_second_week():
    return FIRST_WEEK_START + timedelta(days=13, hours=23, minutes=59)


def within_pay_period(dt):
    return FIRST_WEEK_START <= dt <= SECOND_WEEK_END


def within_first_week(timestamp):
    return FIRST_WEEK_START < timestamp < FIRST_WEEK_END


def format_message_timestamp(timestamp):
    return (timestamp + timedelta(hours=LOCAL_UTC)).strftime(MESSAGE_TIMESTAMP_FORMAT)


def format_week_timestamp(timestamp):
    return timestamp.strftime(WEEK_TIMESTAMP_FORMAT)


# ----- Valid Command Checks -----


def valid_help_command(message):
    if message.content.lower() == ('?' + BOT.user.name.lower()):
        return {'valid': True, 'error': None}
    if message.content.lower() == (CMD_PREFIX + BOT.user.name.lower()):
        return {'valid': True, 'error': None}
    if message.content.lower() == (CMD_PREFIX + 'help'):
        return {'valid': True, 'error': None}
    return {'valid': False, 'error': 'Not a valid help command.'}


def valid_clocks_command(message):
    if message.channel.is_private:
        return {'valid': False, 'error': 'Command cannot be run from a private channel.'}
    if len(message.mentions) == 0:
        return {'valid': False, 'error': 'Command is missing a mention.'}
    args = message.content.split(' ')
    if len(args) < 3:
        return {'valid': False, 'error': 'Command is missing one or more of its arguments.'}
    elif len(args) > 3:
        return {'valid': False, 'error': 'Command has too many arguments.'}
    elif '@' not in args[1]:
        return {'valid': False, 'error': 'Command is missing a valid mention.'}
    elif '/' not in args[2]:
        return {'valid': False, 'error': 'Command is missing a valid date.'}
    else:
        date_parts = args[-1].split('/')
        for part in date_parts:
            if not is_integer(part):
                return {'valid': False, 'error': 'Invalid date format.'}
        try:
            datetime.strptime(args[-1], '%m/%d/%y')
        except ValueError:
            return {'valid': False, 'error': 'Invalid date format.'}
    return {'valid': True, 'error': None}


def valid_times_command(message):
    if message.channel.is_private:
        return {'valid': False, 'error': 'Command cannot be run from a private channel.'}

    args = message.content.split(' ')
    if len(args) < 2:
        return {'valid': False, 'error': 'Command is missing one or more of its arguments.'}
    elif len(args) > 2:
        return {'valid': False, 'error': 'Command has too many arguments.'}
    elif '/' not in args[1]:
        return {'valid': False, 'error': 'Command is missing a valid date.'}
    else:
        date_parts = args[1].split('/')
        for part in date_parts:
            if not is_integer(part):
                return {'valid': False, 'error': 'Invalid date format.'}
        try:
            datetime.strptime(args[-1], '%m/%d/%y')
        except ValueError:
            return {'valid': False, 'error': 'Invalid date format.'}

    valid = False
    error = 'The user does not have permission to use this command.'
    for role in message.author.roles:
        if PROTECTED_ROLE in role.name:
            valid = True
            error = None

    return {'valid': valid, 'error': error}


def valid_clear_command(message):
    if message.channel.type is discord.ChannelType.private:
        return {'valid': True, 'error': None}
    else:
        valid = False
        error = 'The user does not have permission to use this command in this channel.'
        for role in message.author.roles:
            if PROTECTED_ROLE in role.name:
                valid = True
                error = None
        return {'valid': valid, 'error': error}


# ----- Misc -----


def log_invalids(member_name, member):
    with open(CLOCK_LOG, 'a') as log_file:
        log_file.write('Invalid Clocks for {}:\n\n'.format(member_name))
        for clock in INVALID_CLOCKS[member]:
            replace_len = len(clock.message.split('>')[0]) + 1
            author_name = clock.author.name
            if clock.author.nick is not None:
                author_name = clock.author.nick
            log_file.write(
                format_message_timestamp(clock.timestamp)
                + ' | ' + author_name + ': @' + member_name
                + clock.message[replace_len:] + '\n'
                + '    Reason: {}\n'.format(clock.error)
            )
        log_file.write('\n\n')


def log_singles(member_name, member):
    with open(CLOCK_LOG, 'a') as log_file:
        log_file.write('Single Clocks for {}:\n\n'.format(member_name))
        for clock in SINGLE_CLOCKS[member]:
            replace_len = len(clock.message.split('>')[0]) + 1
            author_name = clock.author.name
            if clock.author.nick is not None:
                author_name = clock.author.nick
            if clock.type == 'In':
                error = 'Missing clock-out.'
            else:
                error = 'Missing clock-in.'
            log_file.write(
                format_message_timestamp(clock.timestamp)
                + ' | ' + author_name + ': @' + member_name
                + clock.message[replace_len:] + '\n'
                + '    Reason: {}\n'.format(error)
            )
        log_file.write('\n\n')


# New and edited messages are flagged with a reaction if they are invalid.
# New messages are not flagged if they are valid.
# Edited messages have their flag removed if they are now valid.
async def flag_invalid_clock(message):
    try:
        # Make sure the message is in a channel that starts with a year.
        re.search("\d\d\d\d", message.channel.name).start()

        if Clock(message).error is not None:
            # If the message was an invalid Discord Clock, add an exclamation reaction to show it.
            await BOT.add_reaction(message, '\u2757')  # :exclamation:
            await BOT.send_message(message.author, 'Invalid clock due to: {}'.format(Clock(message).error))
        else:
            # The message is now a valid Discord Clock, so remove the exclamation reaction.
            if len(message.reactions) > 0:
                await BOT.remove_reaction(message, '\u2757', message.server.me)
    except AttributeError:
        # Don't add reactions if the message isn't a Discord Clock.
        pass


# Checks if a string is numeric.
def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# Sends info about the bot and its commands.
async def help_info(channel):
    about = 'A bot that helps track and calculate times.'
    em = discord.Embed(title='__' + BOT.user.name + ' Commands__', description=about, colour=0x0000ff)
    em.add_field(
        name='/clocks @user mm/dd/yy',
        value="- This command gets the clock-ins and clock-outs for the specified user.\n"
              "- Arguments:\n"
              "      @user - This is the specified user as a mention.\n"
              "      mm/dd/yy - This is the start of the two week pay period (SAT).\n"
              "- Who can use: @everyone",
        inline=False)
    em.add_field(
        name='/times mm/dd/yy',
        value='- This command gets all the clock-ins and clock-outs for each user in the channel the '
              'command was run in. It also displays the total hours of the clocks per week.\n'
              '- Arguments:\n'
              '      mm/dd/yy - This is the start of the two week pay period (SAT).\n'
              '- Who can use: @' + PROTECTED_ROLE,
        inline=False)
    em.add_field(
        name='?' + BOT.user.name + ' or /' + BOT.user.name + ' or /help',
        value='Sends this message.',
        inline=False)

    discord_clock_message = (
        "All Discord Clocks must include all three of the following: a mention, a clock-in/out word, and a time in/out."
        " A mention is a person's name with an '@' in front of it."
        " All mentions should light up with a color if they were properly added. Besides mentions, all other"
        " text within the Discord Clock is case insensitive. You can add any extra text anywhere in the message except"
        " at the end of it.\n\n"
        " The TimeTracker bot will check if your clock is valid or not after you send it. If the clock is invalid, it"
        " will add an :exclamation: reaction to it and send you a message with details explaining why it's invalid. If"
        " your message is a valid clock, nothing will happen. It also checks edited messages. This means if you enter"
        " an invalid clock and then edit it to be correct, it will remove the :exclamation:, otherwise it will send you"
        " another message on what is wrong while keeping the :exclamation:. __**Main Point:**__ Make sure there isn't"
        " an :exclamation: attached to your clock in/out message."
    )
    valid_clock_message_one = (
        "**@name in 08:00 AM**\n"
        "   - Has the three requirements: @name, clock-in/out word, and time.\n"
        "   - Includes a leading zero.\n"
        "   - Has a space between the time and the meridiem.\n"
        "   - Includes a capitalized meridiem.\n"
        "**@name OUT 1:00pm**\n"
        "   - Has the three requirements: @name, clock-in/out word, and time.\n"
        "   - Clock-out word is all uppercase.\n"
        "   - Does not include a leading zero.\n"
        "   - Does not have a space between the time and the meridiem.\n"
        "   - Includes a lower-cased meridiem.\n"
        "**@name is iN 0730**\n"
        "   - Has the three requirements: @name, clock-in/out word, and time.\n"
        "   - Clock-in word is a mix of uppercase and lowercase.\n"
        "   - Includes a leading zero.\n"
        "   - Does not include a meridiem; causes it to be read in military time.\n"
        "   - More grammatically correct with 'is' between @name and clock-in word.\n"
    )
    valid_clock_message_two = (
        "**@name is out at 900**\n"
        "   - Has the three requirements: @name, clock-in/out word, and time.\n"
        "   - Does not include a leading zero.\n"
        "   - Does not include a meridiem; causes it to be read in military time.\n"
        "   - More grammatically correct with 'is' between @name and clock-in word.\n"
        "   - Even more grammatically correct with 'at' between clock-in word and time.\n"
        "**Your boy @name is in at 1600**\n"
        "   - Has the three requirements: @name, clock-in/out word, and time.\n"
        "   - Does not include a meridiem; causes it to be read in military time.\n"
        "   - More grammatically correct with 'is' between @name and clock-in word.\n"
        "   - Even more grammatically correct with 'at' between clock-in word and time.\n"
        "   - Less professional with the text before @name, but does not make it invalid.\n"
    )
    invalid_clock_message = (
        "**in 8:00**\n"
        "   - Missing the @name\n"
        "**@name 800**\n"
        "   - Missing a clock-in/out word.\n"
        "**@name is in**\n"
        "   - Missing a time.\n"
        "**@name in 08:00.**\n"
        "   - Includes a period at the end; message must end with a time (with or without meridiem).\n"
    )

    em_one = discord.Embed(colour=0x0000ff)
    em_one.add_field(name='__Discord Clocks__', value=discord_clock_message)

    em_two = discord.Embed(colour=0x0000ff)
    em_two.add_field(name='__Valid Clocks__', value=valid_clock_message_one)

    em_three = discord.Embed(colour=0x0000ff)
    em_three.add_field(name='__Valid Clocks (Continued)__', value=valid_clock_message_two)

    em_four = discord.Embed(colour=0x0000ff)
    em_four.add_field(name='__Invalid Clocks__', value=invalid_clock_message)

    await BOT.send_message(channel, embed=em)
    await BOT.send_message(channel, embed=em_one)
    await BOT.send_message(channel, embed=em_two)
    await BOT.send_message(channel, embed=em_three)
    await BOT.send_message(channel, embed=em_four)


# Try to start the bot. Log and exit if there was an error.
try:
    BOT.run(BOT_TOKEN)
except Exception as e:
    exception_log_write('CRITICAL', 'An exception occurred when trying to run the bot: {}'.format(e))
