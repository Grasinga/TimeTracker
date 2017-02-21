import net.dv8tion.jda.core.AccountType;
import net.dv8tion.jda.core.JDABuilder;
import net.dv8tion.jda.core.MessageHistory;
import net.dv8tion.jda.core.Permission;
import net.dv8tion.jda.core.entities.*;
import net.dv8tion.jda.core.events.message.guild.GuildMessageReceivedEvent;
import net.dv8tion.jda.core.events.message.priv.PrivateMessageReceivedEvent;
import net.dv8tion.jda.core.exceptions.RateLimitedException;
import net.dv8tion.jda.core.hooks.ListenerAdapter;

import javax.security.auth.login.LoginException;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.Temporal;
import java.util.*;

/**
 * A Discord bot that tracks and logs user messages if they contain clock in/out key words; it then calculates the time
 * differences between those messages, and finally sends the command user the list of messages that contained the clock
 * in/out key words and their calculated times.
 */
public class TimeTracker extends ListenerAdapter {

    /**
     * Variable that holds the URL where the log is displayed.
     */
    private static String LOG_URL = "";

    /**
     * Variable that hold's the Bot's name on Discord; initialized via the bot.properties file. Has a default value of
     * "TimeTracker".
     */
    private static String BOT_NAME = "TimeTracker";

    /**
     * The current timezone the bot is running in; initialized via the bot.properties file. Has a default value of
     * "America/Denver".
     */
    private static String TIMEZONE = "America/Denver";

    /**
     * {@link ZoneId} used for converting {@link LocalDateTime} into the bot's timezone. Is initialized via the
     * {@link #TIMEZONE} variable.
     */
    private ZoneId timeZone = TimeZone.getTimeZone(TIMEZONE).toZoneId();

    /**
     * Variable that is used to format the timestamp on messages; initialized by the bot.properties file. Has a default
     * value of "MM/dd/yy (E) @ hh:mm a | ".
     */
    private static String TIMESTAMP = "MM/dd/yy (E) @ hh:mm a | "; // Formatter for the time stamp on messages.

    /**
     * Variable that contains the {@link List} of clock in key words; is populated by the bot.properties file. Has the
     * default values of "In" and "On".
     */
    private static List<String> CLOCK_IN_WORDS = new ArrayList<>(Arrays.asList("In", "On", "Back"));

    /**
     * Variable that contains the {@link List} of clock out key words; is populated by the bot.properties file. Has the
     * default values of "Out" and "Off".
     */
    private static List<String> CLOCK_OUT_WORDS = new ArrayList<>(Arrays.asList("Out", "Off"));

    /**
     * Variable that holds the amount of {@link Message}s to retrieve from a {@link TextChannel}'s history * 100;
     * initialized by the bot.properties file. Has a default value of 3.
     */
    private static int RETRIEVABLE_MESSAGE_AMOUNT = 3;

    /**
     * A {@link HashMap} that contains the {@link Member}s and their respective {@link Message}'s when the
     * '/times MM/dd/yy' command is used.
     */
    private HashMap<Member, List<Message>> tracker = new HashMap<>();

    /**
     * A {@link HashMap} that contains the {@link Member}'s invalid clock ins/outs. Used in
     * {@link #logInvalidsToFile(Member)}.
     */
    private HashMap<Member, List<Message>> invalidClocks = new HashMap<>();

    /**
     * A {@link HashMap} that contains the {@link Member}'s single clock ins/outs. Used in
     * {@link #logSinglesToFile(Member)}.
     */
    private HashMap<Member, List<Message>> singleClocks = new HashMap<>();

    /**
     * Global variable for the start date of the two week pay period. Gets set with {@link #setStartDate(String)}.
     */
    private Date twoWeekStartDate = new Date();

    /**
     * Global variable for the end date of the two week pay period. Gets set with {@link #setEndDate(Date)}.
     */
    private Date twoWeekEndDate = new Date();

    /**
     * Starts the bot with the given arguments (from command line or bot.properties).
     *
     * @param args Given arguments from command line.
     */
    public static void main(String[] args) {
        String token = "";
        try {
            if (args.length >= 1) {
                token = args[0];
            }
            BufferedReader br = new BufferedReader(new FileReader(new File("./bot.properties")));

            String properties = br.readLine();
            if (properties != null && token.equalsIgnoreCase(""))
                token = properties;

            properties = br.readLine();
            if(properties != null)
                LOG_URL = properties;

            properties = br.readLine();
            if(properties != null)
                BOT_NAME = properties;

            properties = br.readLine();
            if(properties != null)
                TIMEZONE = properties;

            properties = br.readLine();
            if(properties != null)
                TIMESTAMP = properties;

            properties = br.readLine();
            if(properties != null) {
                String[] inWords = properties.split(", ");
                CLOCK_IN_WORDS.clear(); // Clear defaults.
                Collections.addAll(CLOCK_IN_WORDS, inWords);
            }

            properties = br.readLine();
            if(properties != null) {
                String[] outWords = properties.split(", ");
                CLOCK_OUT_WORDS.clear(); // Clear defaults.
                Collections.addAll(CLOCK_OUT_WORDS, outWords);
            }

            properties = br.readLine();
            if(properties != null)
                RETRIEVABLE_MESSAGE_AMOUNT = Integer.parseInt(properties);

            br.close();

            new JDABuilder(AccountType.BOT)
                    .setBulkDeleteSplittingEnabled(false)
                    .setToken(token)
                    .addListener(new TimeTracker())
                    .buildBlocking();
        }
        catch (IllegalArgumentException e) {
            System.out.println("The config was not populated. Please make sure all arguments were given.");
        }
        catch (LoginException e) {
            System.out.println("The provided bot token was incorrect. Please provide a valid token.");
        }
        catch (InterruptedException | RateLimitedException e) {
            System.out.println("A thread interruption occurred. Check Stack Trace below for source.");
            e.printStackTrace();
        }
        catch (FileNotFoundException e) {
            System.out.println("Could not find Bot Token file!");
        }
        catch (IOException e) {
            System.out.println("Could not read Bot Token file!");
        }
        catch (Exception e) {
            System.out.println("A general exception was caught. Exception: " + e.getCause());
        }
    } // End of main()

    /**
     * Contains /clear command to delete all private messages received from the bot.
     *
     * @param event Event that holds the {@link User}, {@link TextChannel}, and command info.
     */
    @Override
    public void onPrivateMessageReceived(PrivateMessageReceivedEvent event) {
        if(!event.getMessage().getContent().startsWith("/"))
            return;

        if(event.getMessage().getContent().equalsIgnoreCase("/clear")) {
            MessageHistory channelHistory = event.getChannel().getHistory();
            int amount = 1;
            while(amount > 0) {
                amount = channelHistory.retrievePast(100).complete().size();
            }
            List<Message> channelMessages = channelHistory.getCachedHistory();
            for(Message m : channelMessages) {
                if(m.getAuthor().getName().equalsIgnoreCase(BOT_NAME)) {
                    m.deleteMessage().complete();
                }
            }
        }
    } // End of onPrivateMessageReceived()

    /**
     * Handles the command input via a guild {@link TextChannel} that the bot is a part of. Commands:<br>
     * /times MM/dd/yy (Gets clock ins/outs and the total hours for each member. Admin use only.)<br>
     * /clocks @{@link User} MM/dd/yy (Gets the clock ins/outs for the specified {@link User}. Open use.)<br>
     *
     * @param event Event that holds the {@link User}, {@link TextChannel}, and command info.
     */
    @Override
    public void onGuildMessageReceived(GuildMessageReceivedEvent event) {
        checkForCorrectClock(event);

        if(event.getAuthor().isBot() || !event.getMessage().getContent().startsWith("/"))
            return;

        // Split the message into command and parameters.
        String commandline = event.getMessage().getContent();
        String[] parts = commandline.split(" ");
        String command = parts[0];

        // Handles commands.
        switch (command.toLowerCase()) {
            case "/times":
                if(parts.length < 2 || !parts[1].contains("/")){
                    event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy").queue();
                    event.getMessage().deleteMessage().queue();
                    return;
                }
                else if(parts[1].contains("/")){
                    String[] numbers = parts[1].split("/");
                    for(String s : numbers) {
                        if (numbers.length < 3 || !s.matches("[0-9]+")) {
                            event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy").queue();
                            event.getMessage().deleteMessage().queue();
                            return;
                        }
                    }
                }
                event.getMessage().deleteMessage().queue();
                if(event.getGuild().getMember(event.getAuthor()).hasPermission(Permission.ADMINISTRATOR))
                    getTimes(event.getAuthor(), event.getChannel(), parts[1]);
                else
                    try {
                        PrivateChannel pm = event.getAuthor().openPrivateChannel().complete();
                        pm.sendMessage("You don't have permission to use that command!").queue();
                    } catch (Exception e) {System.out.println("Bot may have been blocked! Cause: " + e.getMessage());}
                break;
            case "/clocks":
                if(parts.length < 3){
                    event.getAuthor().getPrivateChannel().sendMessage("Usage: /clocks @Name mm/dd/yy").queue();
                    event.getMessage().deleteMessage().queue();
                    return;
                }
                else if(parts[1].contains("/")){
                    String[] numbers = parts[parts.length - 1].split("/");
                    for(String s : numbers) {
                        System.out.println(s);
                        if (numbers.length < 3 || !s.matches("[0-9]+")) {
                            event.getAuthor().getPrivateChannel().sendMessage("Usage: /clocks @Name mm/dd/yy").queue();
                            event.getMessage().deleteMessage().queue();
                            return;
                        }
                    }
                }
                event.getMessage().deleteMessage().queue();
                getClocks(
                        event.getAuthor(),
                        event.getChannel(),
                        event.getMessage().getMentionedUsers().get(0), parts[parts.length - 1]
                );
        }
    } // End of onGuildMessageReceived()

    /**
     * Notifies the user typing a clock in/out if they have typed the clock wrong.
     *
     * @param event The user typing a message, and the bot receiving it.
     */
    private void checkForCorrectClock(GuildMessageReceivedEvent event) {
        boolean sendMessage = false;
        Message message = event.getMessage();
        String content = message.getContent();
        switch(message.getMentionedUsers().size()) {
            case 0:
                return;
            case 1:
                if(content.contains(":")) {
                    String firsTimeNum = content.substring(content.indexOf(":") - 2, content.indexOf(":") - 1);
                    String beforeMeridian = "";
                    if(content.toLowerCase().contains("am"))
                        beforeMeridian = content.substring(
                                content.toLowerCase().indexOf("am") - 1,
                                content.toLowerCase().indexOf("am")
                        );
                    else if(content.toLowerCase().contains("pm"))
                        beforeMeridian = content.substring(
                                content.toLowerCase().indexOf("pm") - 1,
                                content.toLowerCase().indexOf("pm")
                        );

                    if(!firsTimeNum.matches("[0-9]+"))
                        sendMessage = true;
                    if(!beforeMeridian.equals(" "))
                        sendMessage = true;
                }
        }
        if(sendMessage){
            PrivateChannel pm = event.getAuthor().openPrivateChannel().complete();
            pm.sendMessage(
                    "That clock in/out may be incorrect! Please check that it is in the format:\n"
                    + "@Name is in/out at XX:XX AM/PM"
            ).queue();
        }
    } // End of checkForCorrectClock()

    /**
     * Method that is called when the command '/times MM/dd/yy' is used. Gets the {@link TextChannel}'s members and
     * their messages from the channel the command was entered from and adds them to {@link #tracker}.
     * Also produces the twoWeekStartDate and twoWeekEndDate from the 'MM/dd/yy' parameter.
     * Finally, it calls {@link #sendMemberInfo(User, TextChannel, Member, List)} to send the user
     * of the command the requested info.
     *
     * @param cmdUser The {@link User} that entered the command.
     * @param channel The {@link TextChannel} from which the messages are being pulled from.
     * @param dateAsString The 'MM/dd/yy' parameter given from the '/times MM/dd/yy' command.
     */
    private void getTimes(User cmdUser, TextChannel channel, String dateAsString) {
        invalidClocks = new HashMap<>();
        singleClocks = new HashMap<>();

        List<Message> channelMessages = getChannelMessageHistory(channel);

        for(Member m : channel.getMembers())
            if(!m.getUser().isBot())
                addMemberInfoToTracker(m, channelMessages);

        // Get dates to check clock in and out messages.
        twoWeekStartDate = setStartDate(dateAsString);
        twoWeekEndDate = setEndDate(twoWeekStartDate);

        // Get messages only from within the two weeks.
        trimTrackerMessagesFromDates(twoWeekStartDate, twoWeekEndDate);

        // Wipe the log file for fresh command.
        try {
            Files.write(Paths.get("./log.txt"), "".getBytes());
        } catch (Exception e) {e.printStackTrace();}

        // Send messages and times to cmdUser.
        PrivateChannel cmdUserPvt = cmdUser.openPrivateChannel().complete();
        for(Map.Entry<Member, List<Message>> entry : tracker.entrySet()) {
            sendMemberInfo(cmdUser, channel, entry.getKey(), entry.getValue());
            cmdUserPvt.sendMessage("--------------------").queue();
        }
    } // End of getTimes()

    /**
     * Method that is called when the command '/clocks @{@link User} MM/dd/yy' is used. Gets the {@link User}'s
     * {@link Message}}s up to two weeks from the entered date. {@link Message}s are then sent to the command user.
     *
     * @param cmdUser The {@link User} that entered the command.
     * @param channel The {@link TextChannel} from which the messages are being pulled from.
     * @param user The {@link User} who's messages are being pulled.
     * @param dateAsString The 'MM/dd/yy' parameter given from the '/clocks @{@link User} MM/dd/yy' command.
     */
    private void getClocks(User cmdUser, TextChannel channel, User user, String dateAsString) {
        List<Message> channelMessages = getChannelMessageHistory(channel);
        List<Message> userClocks = new ArrayList<>();

        // Get all messages that correspond to the passed in user.
        for(Message m : channelMessages)
            if(m.getMentionedUsers().contains(user))
                userClocks.add(m);

        // Get dates to check clock in and out messages.
        twoWeekStartDate = setStartDate(dateAsString);
        twoWeekEndDate = setEndDate(twoWeekStartDate);

        // Remove messages not between the given dates.
        List<Message> toRemove = new ArrayList<>();
        for(Message m : userClocks)
            if(!isBetweenDates(twoWeekStartDate, twoWeekEndDate, getDateFromMessage(m)))
                toRemove.add(m);
        userClocks.removeAll(toRemove);

        // Send the command user the messages.
        try {
            PrivateChannel pm = cmdUser.openPrivateChannel().complete();
            pm.sendMessage(
                    "__**" + getEffectiveNameOfUser(channel.getGuild(), user) + "** (" + channel.getName() + "):__\n\n"
                            + messageListToString(userClocks) + "\n"
            ).queue();
        } catch (Exception e) {System.out.println("Bot may have been blocked! Cause: " + e.getMessage());}
    } // End of getClocks()

    /**
     * Gets the channel's message history up to the number of messages specified by the
     * {@link #RETRIEVABLE_MESSAGE_AMOUNT} times 100. Default value is 3 for a total of 300 messages.
     *
     * @param channel The {@link TextChannel} to get message history from.
     * @return List of past messages up to the {@link #RETRIEVABLE_MESSAGE_AMOUNT} * 100.
     */
    private List<Message> getChannelMessageHistory(TextChannel channel) {
        MessageHistory channelHistory = channel.getHistory();
        for(int i = RETRIEVABLE_MESSAGE_AMOUNT; i > 0; i--) // Default value of 3
            channelHistory.retrievePast(100).complete();
        return channelHistory.getCachedHistory();
    } // End of getChannelMessageHistory()

    /**
     * Adds all members and their respective messages to {@link #tracker}. Messages added are ones that only contain
     * words from {@link #CLOCK_IN_WORDS} and {@link #CLOCK_OUT_WORDS}.
     *
     * @param member The member who's messages will be pulled and stored with in {@link #tracker}.
     * @param channelMessages The {@link TextChannel} that contains the member's messages.
     */
    private void addMemberInfoToTracker(Member member, List<Message> channelMessages) {
        List<Message> userMessages = new ArrayList<>();

        for(Message m : channelMessages) {
            if(m.isMentioned(member.getUser())) {
                if(containsClockWords(m.getContent()))
                    userMessages.add(m);
            }
        }

        if(userMessages.size() > 0)
            tracker.put(member, userMessages);
    } // End of addMemberInfoToTracker()

    /**
     * Checks if a clocked in or out keyword is contained in the message. Key words are populated from the
     * bot.properties file.
     *
     * @param message The message to check.
     * @return True if a clocked in or out word is contained in the message.
     */
    private boolean containsClockWords(String message) {
        ArrayList<String> clockWords = new ArrayList<>();
        clockWords.addAll(CLOCK_IN_WORDS);
        clockWords.addAll(CLOCK_OUT_WORDS);

        for(String clockWord : clockWords)
            if(message.contains(clockWord.toLowerCase()))
                return true;

        return false;
    } // End of containsClockWords()

    /**
     * Sets the two week start date based on the dateToStart given.
     *
     * @param dateToStart Start date as a String.
     * @return The twoWeekStartDate.
     */
    private Date setStartDate(String dateToStart) {
        Date twoWeekStartDate = new Date();
        try {
            twoWeekStartDate = new SimpleDateFormat("MM/dd/yy").parse(dateToStart);
        } catch (Exception e) {System.out.println("Failed to parse date.");}

        return twoWeekStartDate;
    } // End of getStartDate()

    /**
     * Sets the two week end date based on the two week start date.
     *
     * @param twoWeekStartDate The date that the end date is two weeks from.
     * @return The twoWeekEndDate.
     */
    private Date setEndDate(Date twoWeekStartDate) {
        Calendar calendar = Calendar.getInstance();

        calendar.setTime(twoWeekStartDate);
        // 2 Week pay period. Example: Saturday (01/07) -> Friday (01/20) | Sat (01/21) would be a new pay period.
        calendar.add(Calendar.DAY_OF_YEAR, 13); // That's why 13 instead of 14.

        return calendar.getTime();
    } // End of getEndDate()

    /**
     * Utilizes {@link #isBetweenDates(Date, Date, Date)} in order to trim down {@link #tracker}'s messages to ones
     * only from the two weeks between the dates given.
     *
     * @param startDate Start of the two weeks. (Messages start here and go to endDate.)
     * @param endDate End of the two weeks. (Messages start from the startDate and end here.)
     */
    private void trimTrackerMessagesFromDates(Date startDate, Date endDate) {
        for(Map.Entry<Member, List<Message>> entry : tracker.entrySet()) {
            List<Message> removableMessages = new ArrayList<>();

            for(Message m : entry.getValue()) {
                int mDay = 0;
                try {
                    // This value is gotten from the given TIMESTAMP value.
                    // Default TIMESTAMP given starts with MM/dd/yy.
                    // This substring value will change based on where the DAY_OF_MONTH value is in TIMESTAMP.
                    mDay = Integer.parseInt(getTimeStamp(m).substring(3,5));
                } catch (Exception e) {System.out.println("Error getting month value!");}

                Calendar calendar = Calendar.getInstance();
                calendar.setTime(startDate);

                int day = calendar.get(Calendar.DAY_OF_MONTH);

                if (mDay < day || !isBetweenDates(startDate, endDate, getDateFromMessage(m)))
                    removableMessages.add(m);
            }

            entry.getValue().removeAll(removableMessages);
        }
    } // End of trimTackerMessagesFromDates()

    /**
     * Checks if the toCheck date is between the startDate and endDate (inclusive).
     *
     * @param startDate The date 1 day ahead of the min.
     * @param endDate The date 1 day behind the max.
     * @param toCheck The date to be checked.
     * @return Whether the toCheck date is between the startDate and endDate inclusively.
     */
    private boolean isBetweenDates(Date startDate, Date endDate, Date toCheck) {
        Calendar calendar = Calendar.getInstance();

        calendar.setTime(startDate);
        calendar.add(Calendar.DAY_OF_YEAR, -1);
        Date min = calendar.getTime();

        calendar.setTime(endDate);
        calendar.add(Calendar.DAY_OF_YEAR, 1);
        Date max = calendar.getTime();

        return toCheck.after(min) && toCheck.before(max);
    } // End of isBetweenDates()

    /**
     * Converts a {@link LocalDate} to a {@link Date}.
     *
     * @param message The {@link Message} used to get the Date.
     * @return The localDate as {@link Date}.
     */
    private Date getDateFromMessage(Message message) {
        LocalDate localDate = message.getCreationTime().toLocalDate();
        return Date.from(localDate.atStartOfDay(timeZone).toInstant());
    } // End of getDateFromMessage()

    /**
     * Sends the private message containing the clock in and out messages of the {@link Member} with the calculated
     * hours to the '/times MM/dd/yy' command {@link User}. It also calls {@link #logInvalidsToFile(Member)} and
     * {@link #logSinglesToFile(Member)} for the {@link Member}.
     *
     * @param cmdUser The '/times MM/dd/yy' command {@link User}.
     * @param channel The {@link TextChannel} the command was run in.
     * @param member The {@link Member} who's messages and times are being sent.
     * @param listOfClocks The {@link Message}s of the member that contain the clock in and out times.
     */
    private void sendMemberInfo(User cmdUser, TextChannel channel, Member member, List<Message> listOfClocks) {
        HashMap<Integer, List<Message>> clocks = splitWeeks(listOfClocks);
        Collections.reverse(clocks.get(1));
        Collections.reverse(clocks.get(2));

        try {
            PrivateChannel pm = cmdUser.openPrivateChannel().complete();
            SimpleDateFormat sdf = new SimpleDateFormat("MM/dd/yy (E)");
            pm.sendMessage("__**" + member.getEffectiveName() + "** (" + channel.getName() + "):__\n\n"
                    + messageListToString(listOfClocks) + "\n"
                    + sdf.format((twoWeekStartDate)) + " - "
                    + sdf.format(getEndOfWeekOne()) + ": "
                    + getTimeDifferences(clocks.get(1)) + " hours"
                    + "\n\n"
                    + sdf.format(getStartOfWeekTwo()) + " - "
                    + sdf.format(twoWeekEndDate) + ": "
                    + getTimeDifferences(clocks.get(2)) + " hours"
                    + "\n\n"
                    + "Total: " + (getTimeDifferences(clocks.get(1)) + getTimeDifferences(clocks.get(2)))
                    + " hours"
            ).queue();
            if (invalidClocks.containsKey(member) && invalidClocks.get(member).size() > 0) {
                pm.sendMessage(
                        "Hours calculated may be invalid due to invalid clocks. Check " + LOG_URL + " for more info."
                ).queue();
                logInvalidsToFile(member);
            }
            if (singleClocks.containsKey(member) && singleClocks.get(member).size() > 0) {
                pm.sendMessage(
                        "Hours calculated may be invalid due to missing clocks. Check " + LOG_URL + " for more info."
                ).queue();
                logSinglesToFile(member);
            }
            if(invalidClocks.containsKey(member) || singleClocks.containsKey(member))
                if(invalidClocks.get(member).size() > 0 || singleClocks.get(member).size() > 0)
                    try {
                        Files.write(Paths.get("./log.txt"), "\n\n--------------------\n\n".getBytes(), StandardOpenOption.APPEND);
                    } catch (Exception e) {e.printStackTrace();}
        } catch (Exception e) {System.out.println("Bot may have been blocked! Cause: " + e.getMessage());}
    } // End of sendMemberInfo()

    /**
     * Logs the {@link #invalidClocks} to "./log.txt".
     *
     * @param member The {@link Member} to which the invalid clocks belong to.
     */
    private void logInvalidsToFile(Member member) {
        String content = "<h3>Invalid clocks for " + member.getEffectiveName() + ":</h3>";
        for (Message m : invalidClocks.get(member))
            content +=
                    "   " + getTimeStamp(m)
                    + getEffectiveNameOfUser(m.getGuild(), m.getAuthor()) + ": " + m.getContent() + "\n"
            ;
        try {
            Files.write(Paths.get("./log.txt"), content.getBytes(), StandardOpenOption.APPEND);
        } catch (Exception e) {e.printStackTrace();}
    } // End of logInvalidsToFile()

    /**
     * Logs the {@link #singleClocks} to the "./log.txt".
     *
     * @param member The {@link Member} to which the single clocks belong to.
     */
    private void logSinglesToFile(Member member) {
        String content =
                "<h3>Single clocks for " + member.getEffectiveName()
                + " (each corresponding in/out could be an invalid clock):</h3>"
        ;
        for (Message m : singleClocks.get(member))
            content +=
                    "   " + getTimeStamp(m)
                    + getEffectiveNameOfUser(m.getGuild(), m.getAuthor()) + ": " + m.getContent() + "\n"
            ;
        try {
            Files.write(Paths.get("./log.txt"), content.getBytes(), StandardOpenOption.APPEND);
        } catch (Exception e) {e.printStackTrace();}
    } // End of logSinglesToFile()

    /**
     * Splits up the passed in {@link List} of {@link Message}s into two weeks based on the message's timestamp.
     * HashMap's Integer = Week Number
     *
     * @param clocks {@link List} of passed in {@link Message}s.
     * @return HashMap of {@link Message}s with the key being the week.
     */
    private HashMap<Integer, List<Message>> splitWeeks(List<Message> clocks) {
        HashMap<Integer, List<Message>> sortedClocks = new HashMap<>();
        List<Message> weekOneMessages = new ArrayList<>();
        List<Message> weekTwoMessages = new ArrayList<>();

        for(Message m : clocks) {
            if(isWeekOne(getDateFromMessage(m)))
                weekOneMessages.add(m);
            else
                weekTwoMessages.add(m);
        }

        sortedClocks.put(1, weekOneMessages);
        sortedClocks.put(2, weekTwoMessages);

        return sortedClocks;
    } // End of splitWeeks()

    /**
     * Gets the time differences between in and out clocks from the {@link List} of {@link DiscordClock}s received
     * from {@link #createDiscordClocks(List)} after passing in the {@link List} of {@link Message}s (param clocks).
     * Also adds single clocks to {@link #singleClocks} (a clock-in missing a clock-out) for future logging with
     * {@link #logSinglesToFile(Member)}.
     *
     * @param clocks {@link List} of {@link Message}s that contains the clock ins/outs from Discord.
     * @return The calculated hours between the passed in clocks.
     */
    private double getTimeDifferences(List<Message> clocks) {
        Member authorOfClocks = null;
        if(clocks.size() > 0)
            authorOfClocks = clocks.get(0).getGuild().getMember(clocks.get(0).getMentionedUsers().get(0));
        List<Message> singles = new ArrayList<>();

        List<DiscordClock> dClocks = createDiscordClocks(clocks);
        double total = 0;

        for(int i = 0; i < dClocks.size() - 1; i++) {
            DiscordClock in, out;
            if(dClocks.get(i).getType().equalsIgnoreCase("In")) {
                if (dClocks.get(i + 1).getType().equalsIgnoreCase("Out")) {
                    in = dClocks.get(i);
                    out = dClocks.get(i + 1);
                    total += out.getTime() - in.getTime();
                }
                else
                    singles.add(dClocks.get(i).getMessage());
            }
            else if(dClocks.get(i).getType().equalsIgnoreCase("Out"))
                if(!dClocks.get(i + 1).getType().equalsIgnoreCase("In"))
                    singles.add(dClocks.get(i + 1).getMessage());
        }

        // Last message is not checked in loop above.
        if(dClocks.size() > 0 && containsClockIn(dClocks.get(dClocks.size() - 1).getMessage()))
            singles.add(dClocks.get(dClocks.size() - 1).getMessage());

        // If the first message is an out, that means it is missing the in for it. Also not checked in loop above.
        if(dClocks.size() > 0 && dClocks.get(0).getType().equalsIgnoreCase("Out"))
            singles.add(dClocks.get(0).getMessage());

        if(authorOfClocks != null) {
            if(singleClocks.containsKey(authorOfClocks)) {
                List<Message> adds = singleClocks.get(authorOfClocks);
                List<Message> newSingles = new ArrayList<>();

                for(Message m : singles)
                    if(!adds.contains(m))
                        newSingles.add(m);
                adds.addAll(newSingles);

                singleClocks.put(authorOfClocks, adds);
            }
            else
                singleClocks.put(authorOfClocks, singles);
        }

        return total;
    } // End of getTimeDifferences()

    /**
     * Creates a {@link List} of {@link DiscordClock}s from the {@link List} of {@link Message}s passed in. It also adds
     * invalid clock ins/outs to {@link #invalidClocks} for future logging with {@link #logInvalidsToFile(Member)}.
     *
     * @param clocks {@link List} of {@link Message}s that contains the clock ins/outs from Discord.
     * @return A {@link List} of {@link DiscordClock}s to be used for time calculations in {@link #getTimeDifferences(List)}.
     */
    private List<DiscordClock> createDiscordClocks(List<Message> clocks) {
        Member authorOfClocks = null;
        if(clocks.size() > 0)
            authorOfClocks = clocks.get(0).getGuild().getMember(clocks.get(0).getMentionedUsers().get(0));
        List<Message> invalidClockMessages = new ArrayList<>();
        List<DiscordClock> dClocks = new ArrayList<>();
        SimpleDateFormat sdf = new SimpleDateFormat("MM/dd/yy hh:mm a");

        for(Message message : clocks) {
            int month = message.getCreationTime().getMonthValue();
            int day = message.getCreationTime().getDayOfMonth();
            int year = message.getCreationTime().getYear();
            // Based on the clock message have "XX:XX XM" at the end.
            String time = message.getContent().substring(message.getContent().length()-8);

            if(!endsWithMeridiem(message))
                invalidClockMessages.add(message);
            else {
                try {
                    String type;
                    if (containsClockIn(message))
                        type = "In";
                    else
                        type = "Out";

                    Date timestamp = sdf.parse(month + "/" + day + "/" + year + " " + time);

                    dClocks.add(new DiscordClock(type, message, timestamp));

                } catch (Exception e) {
                    invalidClockMessages.add(message);
                }
            }
        }

        if(authorOfClocks != null) {
            if(invalidClocks.containsKey(authorOfClocks)) {
                List<Message> adds = invalidClocks.get(authorOfClocks);
                List<Message> newInvalids = new ArrayList<>();

                for (Message m : invalidClockMessages)
                    if (!adds.contains(m))
                        newInvalids.add(m);
                adds.addAll(newInvalids);

                invalidClocks.put(authorOfClocks, adds);
            }
            else
                invalidClocks.put(authorOfClocks, invalidClockMessages);
        }

        return dClocks;
    } // End of createDiscordClocks()

    /**
     * Check if the date passed in is from the first week based on the {@link #twoWeekStartDate}.
     *
     * @param toCheck Date to be checked.
     * @return Whether toCheck date falls within the first week based on the {@link #twoWeekStartDate}.
     */
    private boolean isWeekOne(Date toCheck) {
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(twoWeekStartDate);
        calendar.add(Calendar.DAY_OF_YEAR, 6); // Saturday to Friday (First week).

        return isBetweenDates(twoWeekStartDate, calendar.getTime(), toCheck);
    } // End of isWeekOne()

    /**
     * Gets the end {@link Date} of week one of the pay period.
     *
     * @return The end {@link Date} of week one.
     */
    private Date getEndOfWeekOne() {
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(twoWeekStartDate);
        calendar.add(Calendar.DAY_OF_YEAR, 6); // Saturday to Friday (First week).

        return calendar.getTime();
    } // End of getEndOfWeekOne()

    /**
     * Gets the start date of week two of the pay period for message formatting.
     *
     * @return The start {@link Date} of week two.
     */
    private Date getStartOfWeekTwo() {
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(twoWeekStartDate);
        calendar.add(Calendar.DAY_OF_YEAR, 7); // Saturday of week 2 (start).

        return calendar.getTime();
    } // End of getStartOfWeekTwo()

    /**
     * Checks if a {@link Message} has a clock in key word. It also checks for clock outs via the return
     * value of false. (There are only clock in and out messages being passed into this method; extraneous messages
     * are non-existent.)
     *
     * @param message {@link Message} to be checked.
     * @return Whether the message passed in contains a clock in (true) or clock out (false) key word.
     */
    private boolean containsClockIn(Message message) {
        for(String clockInWord : CLOCK_IN_WORDS)
            if(message.getContent().toLowerCase().contains(" " + clockInWord.toLowerCase() + " "))
                return true;
        return false;
    } // End of containsClockIn()

    /**
     * Converts a {@link List} of {@link Message}s into a single String.
     *
     * @param list The {@link List} of {@link Message}s.
     * @return The {@link List} of {@link Message}s as a String. ("N/A" if there were no messages.)
     */
    private String messageListToString(List<Message> list) {
        Collections.reverse(list); // Reverse the order of messages -> oldest to newest.

        String str = "";
        for(Message m : list)
            str += getTimeStamp(m) + getEffectiveNameOfUser(m.getGuild(), m.getAuthor()) + ": " + m.getContent() + "\n";

        if(str.length() < 1) // No messages between the start and end date.
            return "N/A";

        return str;
    } // End of messageListToString()

    /**
     * Gets the effective name of the passed in {@link User} from the passed in {@link Guild}. This is needed when
     * only the {@link User} is available and not the {@link Member}.
     *
     * @param guild Guild that the {@link User}'s effective name is on.
     * @param user {@link User} the method gets the effective name for.
     * @return The effective name of the passed in {@link User} of the passed in {@link Guild} or "Unknown".
     */
    private String getEffectiveNameOfUser(Guild guild, User user) {
        for (Member m : guild.getMembers())
            if(m.getUser() == user)
                return m.getEffectiveName();
        return "Unknown"; // The passed in user was not found in the passed in guild.
    } // end of getEffectiveNameOfUser()

    /**
     * Formats the {@link Message}'s timestamp using {@link #TIMESTAMP} as the pattern. {@link #TIMESTAMP} is
     * initialized via the bot.properties file.
     *
     * @param message {@link Message} being passed in.
     * @return A string value of the ldt in the format of {@link #TIMESTAMP}.
     */
    private String getTimeStamp(Message message) {
        Temporal ldt = message.getCreationTime().atZoneSameInstant(timeZone).toLocalDateTime();
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern(TIMESTAMP);
        return fmt.format(ldt);
    } // End of getTimeStamp()

    /**
     * Helps validate clocks by checking if the last 3 digits contains a space followed by a meridiem.
     *
     * @param message {@link Message} to check.
     * @return Whether the message contains a meridiem at the end.
     */
    private boolean endsWithMeridiem(Message message) {
        String meridiemCheck = message.getContent().substring(message.getContent().length() - 3);
        return (meridiemCheck.equalsIgnoreCase(" am") || meridiemCheck.equalsIgnoreCase(" pm"));
    } // End of endsWithMeridiem()
}
