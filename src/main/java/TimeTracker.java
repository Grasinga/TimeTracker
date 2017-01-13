import net.dv8tion.jda.core.AccountType;
import net.dv8tion.jda.core.JDABuilder;
import net.dv8tion.jda.core.MessageHistory;
import net.dv8tion.jda.core.entities.*;
import net.dv8tion.jda.core.events.message.guild.GuildMessageReceivedEvent;
import net.dv8tion.jda.core.events.message.priv.PrivateMessageReceivedEvent;
import net.dv8tion.jda.core.exceptions.RateLimitedException;
import net.dv8tion.jda.core.hooks.ListenerAdapter;

import javax.security.auth.login.LoginException;
import java.io.*;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.Temporal;
import java.util.*;

/**
 * Discord bot that tracks and logs user messages and their times based on a two week period.
 */
public class TimeTracker extends ListenerAdapter {

    /**
     * Variable that hold's the Bot's name on Discord; initialized via the bot.properties file.
     * Has a default value of "TimeTracker".
     */
    private static String BOT_NAME = "TimeTracker";

    /**
     * The current timezone the bot is running in; initialized via the bot.properties file.
     * Default value is "America/Denver".
     */
    private static String TIMEZONE = "America/Denver";

    /**
     * {@link ZoneId} used for converting {@link LocalDateTime} into the bot's timezone. Is initialized via the
     * {@link #TIMEZONE} variable.
     */
    private ZoneId timeZone = TimeZone.getTimeZone(TIMEZONE).toZoneId();

    /**
     * Variable that is used to format the timestamp on messages; initialized by the bot.properties file.
     * Has a default value of "MM/dd/yy (E) @ hh:mm a | ".
     */
    private static String TIMESTAMP = "MM/dd/yy (E) @ hh:mm a | "; // Formatter for the time stamp on messages.

    /**
     * Variable that contains the list of clock in key words; is populated by the bot.properties file.
     * Has the default values of "In" and "On".
     */
    private static ArrayList<String> CLOCK_IN_WORDS = new ArrayList<>(Arrays.asList("In","On"));

    /**
     * Variable that contains the list of clock out key words; is populated by the bot.properties file.
     * Has the default values of "Out" and "Off".
     */
    private static ArrayList<String> CLOCK_OUT_WORDS = new ArrayList<>(Arrays.asList("Out","Off"));

    /**
     * Variable that holds the amount of messages to retrieve from a {@link TextChannel}'s history * 100;
     * initialized by the bot.properties file. Has a default value of 3.
     */
    private static int RETRIEVABLE_MESSAGE_AMOUNT = 3;

    /**
     * The main HashMap that contains the {@link Member}s and their {@link Message}'s when the
     * '/times MM/dd/yy' command is used.
     */
    private HashMap<Member, List<Message>> tracker = new HashMap<>();

    private Date twoWeekStartDate = new Date();
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
            if (properties != null)
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
     * Handles the command input via a guild {@link TextChannel} that the bot is a part of.
     *
     * @param event Event that holds the {@link User}, {@link TextChannel}, and command info.
     */
    @Override
    public void onGuildMessageReceived(GuildMessageReceivedEvent event) {
        if(event.getAuthor().isBot() || !event.getMessage().getContent().startsWith("/"))
            return;

        // Split the message into command and parameters.
        String commandline = event.getMessage().getContent();
        String[] parts = commandline.split(" ");
        String dateAsString = "";
        if(parts.length > 1)
            dateAsString = parts[1];
        String command = parts[0];

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
                getTimes(event.getAuthor(), event.getChannel(), dateAsString);
        }
    } // End of onGuildMessageReceived()

    /**
     * Method that is called when the command '/times MM/dd/yy' is used.
     * Gets the {@link TextChannel}'s members and their messages from
     * the channel the command was entered from and adds them to {@link #tracker}.
     * Also produces the twoWeekStartDate and twoWeekEndDate from the 'MM/dd/yy' parameter.
     * Finally, it calls {@link #sendMemberInfo(User, TextChannel, Member, List)} to send the user
     * of the command the requested info.
     *
     * @param cmdUser User of the '/times MM/dd/yy' command.
     * @param channel The {@link TextChannel} the '/times MM/dd/yy' command was used in.
     * @param dateAsString The 'MM/dd/yy' parameter given from the '/times MM/dd/yy' command.
     */
    private void getTimes(User cmdUser, TextChannel channel, String dateAsString) {
        List<Message> channelMessages = getChannelMessageHistory(channel);

        for(Member m : channel.getMembers())
            addMemberInfoToTracker(m, channelMessages);

        // Get dates to check clock in and out messages.
        twoWeekStartDate = getStartDate(dateAsString);
        twoWeekEndDate = getEndDate(twoWeekStartDate);

        // Get messages only from within the two weeks.
        trimTrackerMessagesFromDates(twoWeekStartDate, twoWeekEndDate);

        // Send messages and times to cmdUser.
        for(Map.Entry<Member, List<Message>> entry : tracker.entrySet()) {
            sendMemberInfo(cmdUser, channel, entry.getKey(), entry.getValue());
        }
    } // End of getTimes()

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
     * words from {@link #CLOCK_IN_WORDS} & {@link #CLOCK_OUT_WORDS}.
     *
     * @param member The member who's messages will be pulled and stored with in {@link #tracker}.
     * @param channelMessages The {@link TextChannel} that contains the member's messages.
     */
    private void addMemberInfoToTracker(Member member, List<Message> channelMessages) {
        List<Message> userMessages = new ArrayList<>();

        for(Message m : channelMessages) {
            if(m.getAuthor() == member.getUser() || m.isMentioned(member.getUser())) {
                if(containsClockWords(m.getContent()))
                    userMessages.add(m);
            }
        }

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
     * Gets the two week start date based on the dateToStart given.
     *
     * @param dateToStart Start date as a String.
     * @return The twoWeekStartDate.
     */
    private Date getStartDate(String dateToStart) {
        Date twoWeekStartDate = new Date();
        try {
            twoWeekStartDate = new SimpleDateFormat("MM/dd/yy").parse(dateToStart);
        } catch (Exception e) {System.out.println("Failed to parse date.");}

        return twoWeekStartDate;
    } // End of getStartDate()

    /**
     * Gets the two week end date based on the two week start date.
     *
     * @param twoWeekStartDate The date that the end date is two weeks from.
     * @return The twoWeekEndDate.
     */
    private Date getEndDate(Date twoWeekStartDate) {
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

            for(Message m : entry.getValue())
                if(!isBetweenDates(startDate, endDate, convertLocalDate(m.getCreationTime().toLocalDate())))
                    removableMessages.add(m);

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

    private boolean isWeekOne(Date toCheck) {
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(twoWeekStartDate);
        calendar.add(Calendar.DAY_OF_YEAR, 6); // Saturday to Friday (First week).

        return isBetweenDates(twoWeekStartDate, calendar.getTime(), toCheck);
    } // End of isWeekOne()

    /**
     * Converts a {@link LocalDate} to a {@link Date}.
     *
     * @param localDate The {@link LocalDate} to be converted.
     * @return The localDate as {@link Date}.
     */
    private Date convertLocalDate(LocalDate localDate) {
        return Date.from(localDate.atStartOfDay(ZoneId.systemDefault()).toInstant());
    } // End of convertLocalDate()

    /**
     * Sends the private message containing the clock in and out messages of the {@link Member} with the calculated
     * hours to the '/times MM/dd/yy' command {@link User}.
     *
     * @param cmdUser The '/times MM/dd/yy' command {@link User}.
     * @param channel The {@link TextChannel} the command was run in.
     * @param member The {@link Member} who's messages and times are being sent.
     * @param listOfClocks The {@link Message}s of the member that contain the clock in and out times.
     */
    private void sendMemberInfo(User cmdUser, TextChannel channel, Member member, List<Message> listOfClocks) {
        // TODO: Figure out how to calculate times individually for each of the two weeks.
        HashMap<Integer, List<Message>> clocks = splitWeeks(hashClocks(listOfClocks));

        PrivateChannel pm = cmdUser.getPrivateChannel();
        pm.sendMessage("__**" + member.getEffectiveName() + "** (" + channel.getName() + "):__").queue();
        pm.sendMessage(messageListToString(listOfClocks)).queue();
    } // End of sendMemberInfo()

    private HashMap<Integer, List<Message>> splitWeeks(HashMap<Date, Message> clocks) {
        HashMap<Integer, List<Message>> sortedClocks = new HashMap<>();
        List<Message> weekOneMessages = new ArrayList<>();
        List<Message> weekTwoMessages = new ArrayList<>();

        for(Map.Entry<Date, Message> entry : clocks.entrySet()) {
            if(isWeekOne(entry.getKey()))
                weekOneMessages.add(entry.getValue());
            else
                weekTwoMessages.add(entry.getValue());
        }

        sortedClocks.put(1, weekOneMessages);
        sortedClocks.put(2, weekTwoMessages);

        return sortedClocks;
    }

    /**
     * Adds the messages to a HashMap that contains the message's Date as the key.
     *
     * @param list List of messages that contains clock in and out times.
     */
    private HashMap<Date, Message> hashClocks(List<Message> list) {
        HashMap<Date, Message> clocks = new HashMap<>();
        for(Message m : list)
            clocks.put(convertLocalDate(m.getCreationTime().toLocalDate()), m);
        return clocks;
    } // End of hashClocks()

    /**
     * Checks if a {@link Message} has a clock in key word.
     *
     * @param message {@link Message} to be checked.
     * @return Whether the message passed in contains a clock in key word.
     */
    private boolean containsClockIn(Message message) {
        for(String clockInWord : CLOCK_IN_WORDS)
            if(message.getContent().toLowerCase().contains(" " + clockInWord.toLowerCase() + " "))
                return true;
        return false;
    } // End of containsClockIn()

    /**
     * Checks if a {@link Message} has a clock out key word.
     *
     * @param message {@link Message} to be checked.
     * @return Whether the message passed in contains a clock out key word.
     */
    private boolean containsClockOut(Message message) {
        for(String clockOutWord : CLOCK_OUT_WORDS)
            if(message.getContent().toLowerCase().contains(" " + clockOutWord.toLowerCase() + " "))
                return true;
        return false;
    } // End of containsClockOut()

    /**
     * Converts a list of {@link Message}s into a single String.
     *
     * @param list The list of {@link Message}s.
     * @return The list of {@link Message}s as a String. ("N/A" if there were no messages.)
     */
    private String messageListToString(List<Message> list) {
        Collections.reverse(list); // Reverse the order of messages -> oldest to newest.

        String str = "";
        for(Message m : list) {
            str += getTimeStamp(m.getCreationTime().atZoneSameInstant(timeZone).toLocalDateTime())
                    + " " + getEffectiveNameOfUser(m.getGuild(), m.getAuthor()) + ": " + m.getContent() + "\n";
        }

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
     * Logic needs working on. TODO
     * @param in
     * @param out
     * @return
     */
    private double getHoursBetweenClocks(LocalDateTime in, LocalDateTime out) {
        int hours = Math.abs(in.getHour() - out.getHour());
        double minutes = convertMinutes(calculateMinutes(in.getMinute()) - calculateMinutes(out.getMinute()));
        return Math.abs(minutes / 100) + hours;
    } // End of getHoursBetweenClocks()

    /**
     * Formats {@link LocalDateTime}s using {@link #TIMESTAMP} as the pattern. {@link #TIMESTAMP} is initialized via the
     * bot.properties file.
     *
     * @param ldt {@link LocalDateTime} being passed in.
     * @return A string value of the ldt in the format of {@link #TIMESTAMP}.
     */
    private String getTimeStamp(Temporal ldt) {
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern(TIMESTAMP);
        return fmt.format(ldt);
    } // End of getTimeStamp()

    /**
     * Used to convert minutes into quarter hours in decimal format.
     * Typically used after {@link #calculateMinutes(int)}.
     *
     * @param minutes Minutes to be converted into a quarter hour as a decimal.
     * @return Minutes in the form of a quarter hour as a decimal amount. (0, 25, 5, 75)
     */
    private int convertMinutes(int minutes) {
        if(minutes == 15)
            return 25;
        else if(minutes == 30)
            return 5;
        else if(minutes == 45)
            return 75;
        else
            return 0;
    } // End of convertMinutes()

    /**
     * Calculates the quarter hour based on the minutes given.
     *
     * @param minutes Minutes to be converted into a quarter hour amount.
     * @return Minutes in the form of a quarter hour. (0, 15, 30, 45)
     */
    private int calculateMinutes(int minutes) {
        int tens = minutes / 10;
        int ones = minutes % 10;

        switch (tens){
            case 0:
                if (ones <= 7) {
                    ones = 0;
                } else {
                    tens++;
                    ones = 5;
                }
                break;
            case 1:
                ones = 5;
                break;
            case 2:
                if (ones <= 3) {
                    tens--;
                    ones = 5;
                } else {
                    tens++;
                    ones = 0;
                }
                break;
            case 3:
                if (ones <= 7) {
                    ones = 0;
                } else {
                    tens++;
                    ones = 5;
                }
                break;
            case 4:
                ones = 5;
                break;
            case 5:
                if (ones <= 3) {
                    tens--;
                    ones = 5;
                } else {
                    tens = 0;
                    ones = 0;
                }
                break;
        }

        return (tens * 10) + ones;
    } // End of calculateMinutes()
}
