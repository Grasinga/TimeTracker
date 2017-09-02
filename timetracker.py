import discord
from discord.ext import commands

import os
import re
import sys
import yaml
import time
from datetime import datetime, timedelta

# ----- Global properties defined by yaml file -----


BOT_NAME = 'TimeTracker'
BOT_APP_ID = ''
BOT_TOKEN = ''
PREFIX = '/'
SPEC_ROLE = 'Tracker'
LOCAL_UTC = -7
MESSAGE_TIMESTAMP_FORMAT = '%m/%d/%y (%A) @ %I:%M %p'
WEEK_TIMESTAMP_FORMAT = '%m/%d/%y (%A)'
CLOCK_IN_WORDS = ['In', 'Back']
CLOCK_OUT_WORDS = ['Out', 'Off']
RETRIEVABLE_MESSAGE_AMOUNT = 300


# ----- Global properties not defined by yaml file -----


BOT = None
FIRST_WEEK_START = None
FIRST_WEEK_END = None
SECOND_WEEK_START = None
SECOND_WEEK_END = None
MISSING_CLOCKS = {}
INVALID_CLOCKS = {}


# Read in global properties from properties.yml file.
def populate_global_properties():
    if os.path.isfile('properties.yml'):
        properties = yaml.load(open('properties.yml'))

        global BOT_NAME, BOT_APP_ID, BOT_TOKEN, PREFIX, SPEC_ROLE, LOCAL_UTC, MESSAGE_TIMESTAMP_FORMAT, \
            WEEK_TIMESTAMP_FORMAT, CLOCK_IN_WORDS, CLOCK_OUT_WORDS, RETRIEVABLE_MESSAGE_AMOUNT

        if len(properties) < 11:
            print('Some properties are missing in the properties.yml file! Please add them and try again. Exiting.')
            sys.exit()

        BOT_NAME = properties['name']
        BOT_APP_ID = properties['id']
        BOT_TOKEN = properties['token']
        PREFIX = properties['prefix']
        SPEC_ROLE = properties['role']
        LOCAL_UTC = int(properties['local-utc'])
        MESSAGE_TIMESTAMP_FORMAT = properties['message-timestamp-format']
        WEEK_TIMESTAMP_FORMAT = properties['week-timestamp-format']
        CLOCK_IN_WORDS = properties['in-words']
        CLOCK_OUT_WORDS = properties['out-words']
        RETRIEVABLE_MESSAGE_AMOUNT = int(properties['id'])

        # Updates the bot to use the properties.yml prefix and creates the client.
        global BOT
        BOT = commands.Bot(command_prefix=PREFIX, help_attrs={'disabled': True})
    else:
        print('properties.yml file is missing! Exiting.')
        sys.exit()


populate_global_properties()


# ----- Discord Clock Class -----


class DiscordClock:
    def __init__(self, message):
        self.is_valid = [True, None]
        self.message = message
        self.author = message.author
        self.channel = message.channel
        self.content = message.content
        if len(message.mentions) == 1:
            self.member = message.mentions[0]
        elif len(message.mentions) > 1:
            self.member = None
            self.is_valid = [False, "Too many mentions."]
        else:
            self.member = None
            self.is_valid = [False, "Missing a mention."]
        self.type = self.get_clock_type()
        self.timestamp = message.timestamp
        self.clock_time = ''
        self.quarter_time = self.get_quarter_time()

    def get_clock_type(self):
        content = self.message.content
        words = content.split(' ')
        for word in words:
            if word.title() in CLOCK_IN_WORDS:
                return 'In'
            elif word.title() in CLOCK_OUT_WORDS:
                return 'Out'
        self.is_valid = [False, "Missing an 'in' or 'out' word."]
        return 'Invalid'

    def get_quarter_time(self):
        content = self.content

        clock_time = ''
        meridiem = ''
        try:
            # Check for the time in the message.
            time_spot = re.search(" \d\d\d\d", content)
            if time_spot is None:
                time_spot = re.search(" \d\d\d", content)
                if time_spot is None:
                    time_spot = re.search(" \d\d:\d\d", content)
                    if time_spot is None:
                        time_spot = re.search(" \d:\d\d", content)
                        if time_spot is None:
                            self.is_valid = [False, "Unable to find the time in/out."]
                            raise ValueError
                        else:
                            time_spot = time_spot.start()
                    else:
                        time_spot = time_spot.start()
                else:
                    time_spot = time_spot.start()
            else:
                time_spot = time_spot.start()

            # Get the message's clock time.
            time_start = content[time_spot + 1:]

            # Check for meridiem.
            meridiem = ''
            if time_start.lower().endswith('am'):
                meridiem = 'am'
            if time_start.lower().endswith('pm'):
                meridiem = 'pm'

            if meridiem is not '':
                if time_start.lower().endswith(' ' + meridiem):
                    time_start = time_start[:-3]
                else:
                    time_start = time_start[:-2]

            if len(time_start) == 3:
                time_start = '0' + time_start
            hour = time_start[:2]
            minutes = time_start[2:]
            if ':' not in hour and ':' not in minutes:
                clock_time = hour + ':' + minutes
            else:
                clock_time = hour + minutes

            self.clock_time = clock_time
        except ValueError:
            global INVALID_CLOCKS
            member = self.member
            if member.nick is not None:
                member = member.nick
            else:
                member = member.name
            if member not in INVALID_CLOCKS:
                INVALID_CLOCKS[member] = []
            INVALID_CLOCKS[member].append(self.message)

        hour = clock_time[:2]
        if hour.endswith(':'):
            hour = hour[:-1]
        minutes = clock_time[-2:]

        if is_integer(hour) and is_integer(minutes):
            return self.calc_quarter_time(hour, minutes, meridiem)
        self.is_valid = [False, "Unable to calculate the time in/out."]
        return 0

    # ----- Times are reported in quarter-hour segments -----

    # Handles the meridiem then continues on to calculate the quarter time.
    def calc_quarter_time(self, hour, minutes, meridiem):
        if meridiem == '' or meridiem == 'am':
            return self.quarter_hour(hour, minutes)
        else:
            hour = int(hour)
            if not hour == 12:
                hour += 12
            return self.quarter_hour(hour, minutes)

    # Calculate the hour of the quarter time.
    def quarter_hour(self, hour, minutes):
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

        return hour + self.convert_minutes_to_quarter(minutes)

    # Calculates the minutes of the quarter time.
    def convert_minutes_to_quarter(self, minutes):
        if minutes == 0:
            return 0
        if minutes == 15:
            return 0.25
        if minutes == 30:
            return 0.5
        if minutes == 45:
            return 0.75
        return 0

    # For debugging purposes.
    def print_info(self):
        print('Message: {}\nAuthor: {}\nChannel: {}\nMentions: {}\nType: {}\nTime: {}\nQuarter Time: {}'.format(
            self.content, self.author.name, self.channel.name, self.member.name, self.type, self.clock_time,
            self.quarter_time
        ))


# ----- Events -----


@BOT.event
async def on_ready():
    print('Successfully logged in as:', str(BOT.user)[:-5])
    print('Using ' + BOT_NAME + ' as bot name.')
    print('Current time: ' + time.strftime('%x %X %Z'))


@BOT.event
async def on_message(message):
    if message.author.bot:
        return
    elif valid_help_command(message):
        if not str(message.channel.type) == 'private':
            await BOT.delete_message(message)
        await help_info(message.author)
        return

    if not str(message.channel.type) == 'private':
        try:
            # Make sure the message is in a channel that starts with the current year.
            re.search("\d\d\d\d", message.channel.name).start()

            valid = DiscordClock(message).is_valid
            if not valid[0]:
                # If the message was an invalid Discord Clock, add an exclamation reaction to show it.
                await BOT.add_reaction(message, '\u2757')  # :exclamation:
                await BOT.send_message(message.author, 'Invalid clock due to: {}'.format(valid[1]))
        except AttributeError:
            # Don't add reactions if the message isn't a Discord Clock.
            pass

    global MISSING_CLOCKS, INVALID_CLOCKS
    MISSING_CLOCKS = {}
    INVALID_CLOCKS = {}

    # Needed for any @BOT.command() methods to work.
    await BOT.process_commands(message)

    # Help keep channels clean from bot commands.
    if message.content.startswith(PREFIX):
        await BOT.delete_message(message)


@BOT.event
async def on_message_edit(before, after):
    if before.author.bot or after.author.bot:
        return

    if not str(after.channel.type) == 'private':
        try:
            # Make sure the message is in a channel that starts with the current year.
            re.search("\d\d\d\d", after.channel.name).start()

            valid = DiscordClock(after).is_valid
            if not valid[0]:
                # If the message was an invalid Discord Clock, add an exclamation reaction to show it.
                await BOT.add_reaction(after, '\u2757')  # :exclamation:
                await BOT.send_message(after.author, 'Invalid clock due to: {}'.format(valid[1]))
            else:
                # The message is now a valid Discord Clock, so remove the exclamation reaction.
                if len(after.reactions) > 0:
                    await BOT.remove_reaction(after, '\u2757', after.server.me)
        except AttributeError:
            # Don't add reactions if the message isn't a Discord Clock.
            pass


# ----- Commands -----


@BOT.command(pass_context=True)
async def clocks(ctx):
    command = ctx.message
    command_user = command.author
    if valid_clocks_command(command):
        # Get the member the command pertains to.
        member = command.mentions[0]  # @name

        # Get the channel based on the command arguments.
        channel = command.channel

        # Get the command arguments.
        cmd_args = command.content.split(' ')

        # Set the dates based on command argument.
        start_date = cmd_args[2]  # 'MM/dd/yy'
        set_dates(start_date)

        # Delete the command from the channel to keep the channel clean.
        await BOT.delete_message(command)

        # Get the messages that mentions the given member in the given channel.
        history = await get_member_history(member, channel)

        # Get the DiscordClocks from the message history.
        discord_clocks = convert_history_to_clocks(history)

        # Get hours of each week.
        week_hours = hours_of_weeks(discord_clocks)

        # Get the message string.
        content = get_member_clocks_string(discord_clocks, week_hours)

        if not len(content) > 2000:  # Character limit for Discord.
            await BOT.send_message(command_user, content)
        else:
            await split_big_message(command_user, content)
    else:
        await BOT.delete_message(command)
        await BOT.send_message(command_user, 'Usage: /clocks @name mm/dd/yy\nOnly usable in a server.')


@BOT.command(pass_context=True)
async def emclocks(ctx):
    command = ctx.message
    command_user = command.author
    if valid_clocks_command(command):
        # Get the member the command pertains to.
        member = command.mentions[0]  # @name

        # Get the channel based on the command arguments.
        channel = command.channel

        # Get the command arguments.
        cmd_args = command.content.split(' ')

        # Set the dates based on command argument.
        start_date = cmd_args[2]  # 'MM/dd/yy'
        set_dates(start_date)

        # Delete the command from the channel to keep the channel clean.
        await BOT.delete_message(command)

        # Get the messages that mentions the given member in the given channel.
        history = await get_member_history(member, channel)

        # Get the DiscordClocks from the message history.
        discord_clocks = convert_history_to_clocks(history)

        # Get hours of each week.
        week_hours = hours_of_weeks(discord_clocks)

        # Get the message string.
        content = get_member_clocks_string(discord_clocks, week_hours)

        # Get the message embed.
        em = get_member_clocks_embed(discord_clocks, week_hours)

        if not len(content) > 2000:  # Character limit for Discord.
            await BOT.send_message(command_user, embed=em)
        else:
            await split_big_message(command_user, content)
    else:
        await BOT.delete_message(command)
        await BOT.send_message(command_user, 'Usage: /emclocks @name mm/dd/yy\nOnly usable in a server.')


@BOT.command(pass_context=True)
async def times(ctx):
    command = ctx.message
    command_user = command.author
    if valid_times_command(command):
        # Get the channel based on the command arguments.
        channel = command.channel

        # Get the command arguments.
        cmd_args = command.content.split(' ')

        # Set the dates based on command argument.
        start_date = cmd_args[1]  # 'MM/dd/yy'
        set_dates(start_date)

        # Delete the command from the channel to keep the channel clean.
        await BOT.delete_message(command)

        # Creates a list of the server members in alphabetically by last name.
        members_alpha = []
        for member in command.server.members:
            if member.nick is not None:
                members_alpha.append(' '.join(reversed(member.nick.split(' '))))
            else:
                members_alpha.append(' '.join(reversed(member.name.split(' '))))
        members_alpha.sort()

        # The above list was just names, this list is the actual member objects.
        members = []
        for am in members_alpha:
            am = ' '.join(reversed(am.split(' ')))
            for member in command.server.members:
                if member.nick is not None:
                    if member.nick.lower() == am.lower():
                        members.append(member)
                else:
                    if member.name.lower() == am.lower():
                        members.append(member)

        for member in members:
            # Get the messages that mentions the given member in the given channel.
            history = await get_member_history(member, channel)

            # No clocks for that member, so go to the next member.
            if len(history) == 0:
                continue

            # Get the DiscordClocks from the message history.
            discord_clocks = convert_history_to_clocks(history)

            # Get hours of each week.
            week_hours = hours_of_weeks(discord_clocks)

            # Get the message string.
            content = get_member_clocks_string(discord_clocks, week_hours)

            if not len(content) > 2000:  # Character limit for Discord.
                await BOT.send_message(command_user, content)
            else:
                await split_big_message(command_user, content)
    else:
        await BOT.delete_message(command)
        await BOT.send_message(command_user, 'Usage: /times mm/dd/yy\nOnly usable in a server.')


@BOT.command(pass_context=True)
async def emtimes(ctx):
    command = ctx.message
    command_user = command.author
    if valid_times_command(command):
        # Get the channel based on the command arguments.
        channel = command.channel

        # Get the command arguments.
        cmd_args = command.content.split(' ')

        # Set the dates based on command argument.
        start_date = cmd_args[1]  # 'MM/dd/yy'
        set_dates(start_date)

        # Delete the command from the channel to keep the channel clean.
        await BOT.delete_message(command)

        # Creates a list of the server members in alphabetically by last name.
        members_alpha = []
        for member in command.server.members:
            if member.nick is not None:
                members_alpha.append(' '.join(reversed(member.nick.split(' '))))
            else:
                members_alpha.append(' '.join(reversed(member.name.split(' '))))
        members_alpha.sort()

        # The above list was just names, this list is the actual member objects.
        members = []
        for am in members_alpha:
            am = ' '.join(reversed(am.split(' ')))
            for member in command.server.members:
                if member.nick is not None:
                    if member.nick.lower() == am.lower():
                        members.append(member)
                else:
                    if member.name.lower() == am.lower():
                        members.append(member)

        for member in members:
            # Get the messages that mentions the given member in the given channel.
            history = await get_member_history(member, channel)

            # No clocks for that member, so go to the next member.
            if len(history) == 0:
                continue

            # Get the DiscordClocks from the message history.
            discord_clocks = convert_history_to_clocks(history)

            # Get hours of each week.
            week_hours = hours_of_weeks(discord_clocks)

            # Get the message string.
            content = get_member_clocks_string(discord_clocks, week_hours)

            # Get the message embed.
            em = get_member_clocks_embed(discord_clocks, week_hours)

            if not len(content) > 2000:  # Character limit for Discord.
                await BOT.send_message(command_user, embed=em)
            else:
                await split_big_message(command_user, content)
    else:
        await BOT.delete_message(command)
        await BOT.send_message(command_user, 'Usage: /emtimes mm/dd/yy\nOnly usable in a server.')


@BOT.command(pass_context=True)
async def clear(ctx):
    message = ctx.message
    channel = message.channel
    if not str(channel.type) == 'private':
        await BOT.delete_message(message)
    await BOT.send_message(channel, 'Deleting messages . . .')
    logs = []
    async for log in BOT.logs_from(channel):
        if log.author.name == BOT_NAME:
            logs.append(log)
    received = len(logs)
    while received > 0:
        tmp = []
        async for log in BOT.logs_from(channel):
            if log.author.name == BOT_NAME:
                tmp.append(log)
                logs.append(log)
        received = len(tmp)
        for log in reversed(logs):
            try:
                await BOT.delete_message(log)
                logs.remove(log)
            except discord.NotFound:
                pass


# ----- Core Tracker Functions -----


# Gets the member's history before SECOND_WEEK_END.
async def get_member_history(member, channel):
    history = []
    async for message in BOT.logs_from(
            channel, limit=RETRIEVABLE_MESSAGE_AMOUNT, after=FIRST_WEEK_START,
            reverse=True
    ):
        if message.mentions is not None and message.mentions[0] == member:
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


# Converts the list of messages to a list of DiscordClocks.
def convert_history_to_clocks(history):
    discord_clocks = []
    for message in history:
        discord_clocks.append(DiscordClock(message))
    return discord_clocks


# Gets the string to be sent as a message for a member's clocks.
def get_member_clocks_string(discord_clocks, week_hours):
    dc = discord_clocks[0]
    member = dc.member
    if member.nick is not None:
        member = member.nick
    else:
        member = member.name
    channel = dc.channel

    str_clocks = convert_clocks_to_string_by_week(discord_clocks)
    error = ''
    if member in MISSING_CLOCKS or member in INVALID_CLOCKS:
        error += 'Hours calculated may be invalid due to having single or incorrectly formatted clocks.'
    main_info = 'Pay Period: **{} to {}**\nTotal Hours: **{}**\n{}'.format(
        format_week_timestamp(FIRST_WEEK_START),
        format_week_timestamp(SECOND_WEEK_END),
        (week_hours[0] + week_hours[1]),
        error
    )
    str_clocks = (
        '__**' + member + '** (' + channel.name + '):__\n\n'
        + main_info + '\n\n'
        + format_week_timestamp(FIRST_WEEK_START)
        + ' to ' + format_week_timestamp(FIRST_WEEK_END)
        + ': ' + str(week_hours[0]) + ' hours\n\n' + str_clocks[0] + '\n'
        + format_week_timestamp(SECOND_WEEK_START)
        + ' to ' + format_week_timestamp(SECOND_WEEK_END)
        + ': ' + str(week_hours[1]) + ' hours\n\n' + str_clocks[1]
    )
    return str_clocks


# Gets the embed to be sent as a message for a member's clocks.
def get_member_clocks_embed(discord_clocks, week_hours):
    dc = discord_clocks[0]
    member = dc.member
    if member.nick is not None:
        member = member.nick
    else:
        member = member.name
    channel = dc.channel

    str_clocks = convert_clocks_to_string_by_week(discord_clocks)
    error = ''
    if member in MISSING_CLOCKS or member in INVALID_CLOCKS:
        error += 'Hours calculated may be invalid due to having single or incorrectly formatted clocks.'
    main_info = 'Pay Period: **{} to {}**\nTotal Hours: **{}**\n{}'.format(
        format_week_timestamp(FIRST_WEEK_START),
        format_week_timestamp(SECOND_WEEK_END),
        (week_hours[0] + week_hours[1]),
        error
    )
    em = discord.Embed(
        title=member + ' (' + channel.name + '):',
        description=main_info,
        colour=0x0000ff
    )
    week_one = '{} to {}: {} hours'.format(
        format_week_timestamp(FIRST_WEEK_START),
        format_week_timestamp(FIRST_WEEK_END),
        str(week_hours[0])
    )
    week_two = '{} to {}: {} hours'.format(
        format_week_timestamp(SECOND_WEEK_START),
        format_week_timestamp(SECOND_WEEK_END),
        str(week_hours[1])
    )
    if len(str_clocks[0]) == 0:
        str_clocks[0] = 'None'
    em.add_field(name=week_one, value=str_clocks[0], inline=False)
    if len(str_clocks[1]) == 0:
        str_clocks[1] = 'None'
    em.add_field(name=week_two, value=str_clocks[1], inline=False)
    return em


# Converts the list of DiscordClocks into a string.
def convert_clocks_to_string_by_week(discord_clocks):
    first_week = ''
    second_week = ''
    for dc in discord_clocks:
        author = dc.author
        if author.nick is not None:
            author = author.nick
        else:
            author = author.name

        member = dc.member
        if member.nick is not None:
            member = member.nick
        else:
            member = member.name

        content = dc.content
        replace_len = len(content.split('>')[0]) + 1
        if within_first_week(dc.timestamp):
            first_week += (
                format_message_timestamp(dc.timestamp)
                + ' | ' + author + ': @' + member
                + content[replace_len:] + '\n'
            )
        else:
            second_week += (
                format_message_timestamp(dc.timestamp)
                + ' | ' + author + ': @' + member
                + content[replace_len:] + '\n'
            )

    return [first_week, second_week]


# Sends more than one message for when the content is over 2000 characters.
async def split_big_message(channel, str_message):
    parts = str_message.split("):")
    await BOT.send_message(channel, parts[0] + '):' + parts[1] + '):')
    if len(parts) > 3:
        await BOT.send_message(channel, (parts[2] + '):'))
        await BOT.send_message(channel, parts[3])
    else:
        await BOT.send_message(channel, parts[2] + '):')


# Returns a list of two elements that contains the hours worked for each week.
def hours_of_weeks(discord_clocks):
    first_week_clocks = []
    second_week_clocks = []
    for dc in discord_clocks:
        if within_first_week(dc.timestamp):
            first_week_clocks.append(dc)
        else:
            second_week_clocks.append(dc)

    first_week_clocks = associate_clocks(first_week_clocks)
    second_week_clocks = associate_clocks(second_week_clocks)

    first_week_hours = calc_week_hours(first_week_clocks)
    second_week_hours = calc_week_hours(second_week_clocks)

    return [first_week_hours, second_week_hours]


# Helps calculate the hours by associating a clock-in with a clock-out.
def associate_clocks(discord_clocks):
    global MISSING_CLOCKS, INVALID_CLOCKS
    if len(discord_clocks) == 0:
        return []
    member = discord_clocks[0].member
    if member.nick is not None:
        member = member.nick
    else:
        member = member.name
    associated_clocks = []
    for dc in discord_clocks:
        if dc.type == 'Out':
            if associated_clocks[-1] is not None and associated_clocks[-1]['Out'] is None:
                associated_clocks[-1]['Out'] = dc
            else:
                # Missing clock
                if member not in MISSING_CLOCKS:
                    MISSING_CLOCKS[member] = []
                MISSING_CLOCKS[member].append(dc)
        elif dc.type == 'In':
            associated_clocks.append({'In': dc, 'Out': None})
        else:
            # Invalid clock
            if member not in INVALID_CLOCKS:
                INVALID_CLOCKS[member] = []
            INVALID_CLOCKS[member].append(dc)

    valid_clocks = []
    for ac in associated_clocks:
        if ac['Out'] is not None:
            valid_clocks.append(ac)
        else:
            # Missing clock
            if member not in MISSING_CLOCKS:
                MISSING_CLOCKS[member] = []
            MISSING_CLOCKS[member].append(ac)

    return valid_clocks


def calc_week_hours(week_clocks):
    total = 0.0
    for dc in week_clocks:
        total += (dc['Out'].quarter_time - dc['In'].quarter_time)
    return total


# ----- Week/Timestamp Functions -----


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
    return FIRST_WEEK_START < dt < SECOND_WEEK_END


def within_first_week(timestamp):
    return FIRST_WEEK_START < timestamp < FIRST_WEEK_END


def format_message_timestamp(timestamp):
    return (timestamp + timedelta(hours=LOCAL_UTC)).strftime(MESSAGE_TIMESTAMP_FORMAT)


def format_week_timestamp(timestamp):
    return timestamp.strftime(WEEK_TIMESTAMP_FORMAT)


# ----- Helper Functions -----


def valid_help_command(message):
    if message.content.lower() == ('?' + BOT_NAME.lower()):
        return True
    if message.content.lower() == ('/' + BOT_NAME.lower()):
        return True
    if message.content.lower() == '/help':
        return True
    return False


def valid_clocks_command(command):
    if command.channel.is_private:
        return False
    if len(command.mentions) == 0:
        return False
    args = command.content.split(' ')
    if len(args) < 3:
        return False
    elif '@' not in args[1] or '/' not in args[2]:
        return False
    else:
        date_parts = args[-1].split('/')
        for part in date_parts:
            if not is_integer(part):
                return False
    return True


def valid_times_command(command):
    if command.channel.is_private:
        return False
    args = command.content.split(' ')
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


# ----- Misc Functions -----


# Sends info about the bot.
async def help_info(channel):
    about = 'A bot that helps track and calculate times.'
    em = discord.Embed(title='__' + BOT_NAME + ' Commands__', description=about, colour=0x0000ff)
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
              '- Who can use: @' + SPEC_ROLE,
        inline=False)
    em.add_field(
        name='/emclocks @user mm/dd/yy',
        value='Same as the above command except messages are embeds if they are under 2000 characters.',
        inline=False)
    em.add_field(
        name='/emtimes mm/dd/yy',
        value='Same as the above command except messages are embeds if they are under 2000 characters.',
        inline=False)
    em.add_field(
        name='?' + BOT_NAME + ' or /' + BOT_NAME + ' or /help',
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


try:
    # Bot start
    BOT.run(BOT_TOKEN)
except ValueError as ve:
    print(ve)
    pass
