package net.grasinga.discord.bots;

import net.dv8tion.jda.JDABuilder;
import net.dv8tion.jda.entities.Guild;
import net.dv8tion.jda.entities.Message;
import net.dv8tion.jda.entities.TextChannel;
import net.dv8tion.jda.entities.User;
import net.dv8tion.jda.events.message.guild.GuildMessageReceivedEvent;
import net.dv8tion.jda.hooks.ListenerAdapter;
import net.grasinga.discord.MessageLogger;

import javax.security.auth.login.LoginException;
import java.io.*;
import java.text.SimpleDateFormat;
import java.time.DayOfWeek;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.Temporal;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Discord bot that Tracks and Logs user messages.
 */
public class TimeTracker extends ListenerAdapter {
    private static String BOT_NAME = "TimeTracker";
    private static String TIMEZONE = "America/Denver";
    private ZoneId timeZone = TimeZone.getTimeZone(TIMEZONE).toZoneId();
    private static String TIMESTAMP = "MM/dd/yy (E) @ hh:mm a <|> "; // Formatter for the time stamp on messages.

    private static ArrayList<String> clockInWords = new ArrayList<>();
    private static ArrayList<String> clockOutWords = new ArrayList<>();

    private List<User> guildUsers = new ArrayList<>();
    private HashMap<User, List<Message>> userTimeLogs = new HashMap<>();

    private Guild currentGuild;

    /**
     * Starts the bot with the given arguments (from command line or bot.properties).
     *
     * @param args Given arguments from command line.
     */
    public static void main(String[] args) {
        String token = "";
        try {
            if (args.length >= 1){
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
                Collections.addAll(clockInWords, inWords);
            }

            properties = br.readLine();
            if(properties != null) {
                String[] outWords = properties.split(", ");
                Collections.addAll(clockOutWords, outWords);
            }

            br.close();

            new JDABuilder()
                    .setBulkDeleteSplittingEnabled(false)
                    .setBotToken(token)
                    .addListener(new TimeTracker())
            .buildBlocking();
        }
        catch (IllegalArgumentException e){
            System.out.println("The config was not populated. Please make sure all arguments were given.");
        }
        catch (LoginException e){
            System.out.println("The provided bot token was incorrect. Please provide a valid token.");
        }
        catch (InterruptedException e){
            e.printStackTrace();
        }
        catch (FileNotFoundException e){
            System.out.println("Could not find Bot Token file!");
        }
        catch (IOException e){
            System.out.println("Could not read Bot Token file!");
        }
    }

    public void onGuildMessageReceived(GuildMessageReceivedEvent event) {
        currentGuild = event.getGuild();
        guildUsers = event.getGuild().getUsers();
        String commandline = event.getMessage().getContent();
        String[] parts = commandline.split(" ");
        String date = "";
        if(parts.length > 1)
            date = parts[1];
        String command = parts[0];

        switch (command.toLowerCase()){
            case "/times":
                if(parts.length < 2) {
                    event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy");
                    event.getMessage().deleteMessage();
                    return;
                }
                else if(!parts[1].contains("/")){
                    event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy");
                    event.getMessage().deleteMessage();
                    return;
                }
                else if(parts[1].contains("/")){
                    String[] numbers = parts[1].split("/");
                    for(String s : numbers) {
                        if (!s.matches("[0-9]+")) {
                            event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy");
                            event.getMessage().deleteMessage();
                            return;
                        } else if(numbers.length < 2){
                            event.getAuthor().getPrivateChannel().sendMessage("Usage: /times mm/dd/yy");
                            event.getMessage().deleteMessage();
                            return;
                        }
                    }
                }
                event.getMessage().deleteMessage();
                getTimes(event.getGuild(), event.getAuthor(), event.getChannel(), date);
                break;
            case "/clear":
                event.getMessage().deleteMessage();
                clearMessages(event.getAuthor());
                break;
        }
    }

    private void clearMessages(User cmdUser) {
        cmdUser.getPrivateChannel().getHistory().retrieveAll().stream().filter(m -> m.getAuthor() != cmdUser).forEach(m -> {
            m.deleteMessage();
            pause(2);
        });
    }

    private void getTimes(Guild guild, User cmdUser, TextChannel channel, String date) {
        MessageLogger messagelogger = new MessageLogger();

        List<User> users = new ArrayList<>(); // Get and set all mentioned users in the specified channel.
        messagelogger.getChannelLog(channel).stream().filter(m -> !m.getMentionedUsers().isEmpty()).forEach(m -> {
            m.getMentionedUsers().stream().filter(u -> !users.contains(u)).forEach(users::add);
        });

        for(User u : users) // For every user, add their mentioned messages to their HashMap value.
            setUserMessages(u,channel);

        List<String> appendedTimeMessages;

        int index = 0;
        String[] logs = new String[userTimeLogs.size()];
        for(Map.Entry<User, List<Message>> entry : userTimeLogs.entrySet()) {
            if(guild.getNicknameForUser(entry.getKey()) != null && !guild.getNicknameForUser(entry.getKey()).isEmpty())
                logs[index] = "__**" + guild.getNicknameForUser(entry.getKey()) + "**__ (" + channel.getName() + "):\n";
            else
                logs[index] = "__**" + entry.getKey().getUsername() + "**__ (" + channel.getName() + "):\n";

            appendedTimeMessages = appendTime(entry.getValue(), date);

            logs[index] += convertListToString(calculateTimes(appendedTimeMessages, date));
            index++;
        }

        sendMessages(cmdUser, logs);
    }

    private List<String> calculateTimes(List<String> appendedTimeMessages, String date) {
        String[] weeks = new String[2];
        int firstHours = 0;
        int firstMinutes = 0;
        int hoursTotal = 0;
        int minutesTotal = 0;
        int hoursIn = 0;
        int minutesIn = 0;
        int hoursOut = 0;
        int minutesOut = 0;
        for(int i=0; i < appendedTimeMessages.size(); i++) {
            String[] parts = appendedTimeMessages.get(i).split("<|>");
            if(appendedTimeMessages.get(i).length() > 2) {
                try {
                    if (appendedTimeMessages.get(i).endsWith("I")) {
                        String hours = parts[2].substring(parts[2].length() - 7, parts[2].length() - 5);
                        if(hours.startsWith(" "))
                            hours = hours.substring(1);
                        hoursIn += Integer.parseInt(hours);
                        minutesIn += Integer.parseInt(parts[2].substring(parts[2].length() - 4, parts[2].length() - 2));
                        minutesTotal += calculateMinutes(minutesIn);
                        if (minutesTotal > 60) {
                            hoursOut += minutesTotal / 60;
                            minutesTotal %= 60;
                        }

                        hoursTotal += Math.abs(hoursIn);
                        hoursIn = 0;
                        minutesIn = 0;
                    }
                    if (appendedTimeMessages.get(i).endsWith("O")) {
                        String hours = parts[2].substring(parts[2].length() - 7, parts[2].length() - 5);
                        if(hours.startsWith(" "))
                            hours = hours.substring(1);
                        hoursOut += Integer.parseInt(hours);
                        minutesOut += Integer.parseInt(parts[2].substring(parts[2].length() - 4, parts[2].length() - 2));
                        minutesTotal -= calculateMinutes(minutesOut);
                        if (minutesTotal > 60) {
                            hoursOut += minutesTotal / 60;
                            minutesTotal %= 60;
                        }

                        hoursTotal -= hoursOut;
                        hoursOut = 0;
                        minutesOut = 0;
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                if(parts.length > 1) {
                    String extra = appendedTimeMessages.get(i)
                            .substring(appendedTimeMessages.get(i).length() - parts[2].length() + 1);

                    String[] extras = extra.split("/");
                    String extraDate = "";
                    if(extras.length >= 3){
                        extraDate = extras[0].substring(extras[0].length() - 2) + "/" // Month
                                + extras[1] + "/" // Day
                                + extras[2].substring(0, 2); // Year
                    }

                    if (getWeeks(date, extraDate) == 1) { // Week 1
                        firstHours = Math.abs(hoursTotal);
                        firstMinutes = minutesTotal;
                        weeks = getTimeMessages(
                                weeks, 0, date, firstHours, convertMinutes(Math.abs(firstMinutes))
                        );
                    }
                    else // Week 2
                        weeks = getTimeMessages(
                                weeks, 1, date, Math.abs(hoursTotal) - firstHours,
                                convertMinutes(Math.abs(minutesTotal)) - firstMinutes
                        );


                    appendedTimeMessages.add(i, appendedTimeMessages.get(i)
                            .substring(0, appendedTimeMessages.get(i).length() - parts[2].length() - 4));
                    appendedTimeMessages.remove(appendedTimeMessages.get(i + 1));
                }
            }
            else
                appendedTimeMessages.remove(i);
        }
        if(weeks[0] != null)
            appendedTimeMessages.add(weeks[0]);
        if(weeks[1] != null)
            appendedTimeMessages.add(weeks[1]);
        minutesTotal = convertMinutes(Math.abs(minutesTotal));
        appendedTimeMessages.add("\nTotal: " + Math.abs(hoursTotal) + "." + minutesTotal + " hours");
        return appendedTimeMessages;
    }

    private String[] getTimeMessages(String[] weeks, int week, String date, int hoursTotal, int minutesTotal) {
        Calendar cal = Calendar.getInstance();
        Date convertedDate = new Date();
        try{
            SimpleDateFormat sdf = new SimpleDateFormat("MM/dd");

            // Add year
            int year = cal.get(Calendar.YEAR);
            convertedDate = sdf.parse(date);
            cal.setTime(convertedDate);
            cal.set(Calendar.YEAR, year);

            convertedDate = cal.getTime();
        } catch (Exception e){e.printStackTrace();}

        cal.setTime(convertedDate);
        cal.add(Calendar.DAY_OF_YEAR, 1);
        Date startFirstWeekDate = cal.getTime();
        cal.add(Calendar.DAY_OF_YEAR, 6);
        Date endFirstWeekDate = cal.getTime();
        cal.add(Calendar.DAY_OF_YEAR, 1);
        Date startSecondWeekDate = cal.getTime();
        cal.add(Calendar.DAY_OF_YEAR, 6);
        Date endSecondWeekDate = cal.getTime();

        String startFirstWeek = new SimpleDateFormat("MM/dd/yy (E)").format(startFirstWeekDate);
        String endFirstWeek = new SimpleDateFormat("MM/dd/yy (E)").format(endFirstWeekDate);
        String startSecondWeek = new SimpleDateFormat("MM/dd/yy (E)").format(startSecondWeekDate);
        String endSecondWeek = new SimpleDateFormat("MM/dd/yy (E)").format(endSecondWeekDate);

        if (week == 0) { // Week 1
                weeks[0] = "\n" + startFirstWeek + " - " + endFirstWeek + ": "
                        + hoursTotal + "." + minutesTotal + " hours";
        }
        else { // Week 2
                weeks[1] = "\n" + startSecondWeek + " - " + endSecondWeek + ": "
                        + hoursTotal + "." + minutesTotal + " hours";
        }

        return weeks;
    }

    private int getWeeks(String commandDate, String messageDate){
        SimpleDateFormat sdf1 = new SimpleDateFormat("MM/dd");
        Date cmdDate = new Date();
        Date mDate = new Date();
        try {
            cmdDate = sdf1.parse(commandDate);
            mDate = sdf1.parse(messageDate);

            // Add the current year to the date.
            Calendar c = Calendar.getInstance();
            int year = c.get(Calendar.YEAR);
            c.setTime(cmdDate);
            c.set(Calendar.YEAR, year);
            cmdDate = c.getTime();
            c.setTime(mDate);
            c.set(Calendar.YEAR, year);
            mDate = c.getTime();
        } catch (Exception e){e.printStackTrace();}

        Calendar cal = Calendar.getInstance();
        cal.setTime(cmdDate);
        int cmdDay = cal.get(Calendar.DAY_OF_MONTH);
        cal.setTime(mDate);
        int mDay = cal.get(Calendar.DAY_OF_MONTH);

        if(mDay - cmdDay >= 7)
            return 2; // Week 2
        else
            return 1; // Week 1
    }

    private int convertMinutes(int minutes) {
        if(minutes == 15)
            return 25;
        else if(minutes == 30)
            return 5;
        else if(minutes == 45)
            return 75;
        else
            return 0;
    }

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
    }

    private List<String> appendTime(List<Message> list, String date) {
        List<String> stringList = new ArrayList<>();
        for(Message m : list) { // Generate the list message with timestamp.

            SimpleDateFormat sdf1 = new SimpleDateFormat("MM/dd/yy");
            SimpleDateFormat sdf2 = new SimpleDateFormat("MM/dd");
            Date messageDate = new Date();
            Date endDate = new Date();
            long dateDiff = 0;
            try {
                messageDate = sdf1.parse(getTimeStamp(m.getTime().atZoneSameInstant(timeZone).toLocalDateTime()));
                try {
                    if(date.length() > 5)
                        endDate = sdf1.parse(date);
                    else {
                        endDate = sdf2.parse(date);

                        // Add the current year to the date.
                        Calendar c = Calendar.getInstance();
                        int year = c.get(Calendar.YEAR);
                        c.setTime(endDate);
                        c.set(Calendar.YEAR, year);
                        endDate = c.getTime();
                    }
                } catch (Exception e){System.out.println("Bad date: " + date); return null;}
                dateDiff = messageDate.getTime() - endDate.getTime();
            } catch (Exception e){e.printStackTrace();}

            String message = "";
            if(m.getAuthor() != null)
                message +=
                        getTimeStamp(m.getTime().atZoneSameInstant(timeZone).toLocalDateTime()) + " "
                                + m.getAuthor().getUsername() + ": " + m.getContent();
            else
                message +=
                        getTimeStamp(m.getTime().atZoneSameInstant(timeZone).toLocalDateTime()) + " "
                                + m.getContent();

            // After date given and only two weeks after.
            if (messageDate.after(endDate) && TimeUnit.DAYS.convert(dateDiff, TimeUnit.MILLISECONDS) < 15) {
                String mentionedUser = "";
                if (!m.getMentionedUsers().isEmpty()) {
                    User user = m.getMentionedUsers().get(0);
                    if (currentGuild.getNicknameForUser(user) != null && !currentGuild.getNicknameForUser(user).isEmpty())
                        mentionedUser = currentGuild.getNicknameForUser(user);
                    else
                        mentionedUser = m.getMentionedUsers().get(0).getUsername();
                }

                // Substring start to skip the mentioned user and just get the message.
                int substringSearch = TIMESTAMP.length() + m.getAuthor().getUsername().length() + mentionedUser.length() + 8;

                String appendedTimeMsg = "";
                DateTimeFormatter fmt = DateTimeFormatter.ofPattern("MM/dd/yy");
                String appendDate = fmt.format(m.getTime().atZoneSameInstant(timeZone));

                // Message's time variables.
                ZonedDateTime zoneInstant = m.getTime().atZoneSameInstant(timeZone);
                DayOfWeek zoneDayOfWeek = zoneInstant.getDayOfWeek();
                int zoneHour = zoneInstant.getHour();
                int zoneMinute = zoneInstant.getMinute();

                for (int i =0; i < clockInWords.size(); i++) { // Appends clock in time
                    if (message.substring(substringSearch).equalsIgnoreCase(clockInWords.get(i))) {
                        if(zoneHour < 10 && zoneMinute < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " 0" + zoneHour + ":0" + zoneMinute);
                        else if(zoneHour < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " 0" + zoneHour + ":" + zoneMinute);
                        else if(zoneMinute < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":0" + zoneMinute);
                        else
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":" + zoneMinute);
                        appendedTimeMsg += " I";
                    }
                    else if (message.toLowerCase().contains(" " + clockInWords.get(i).toLowerCase() + " ")
                            && !message.toLowerCase().contains(" " + clockOutWords.get(i).toLowerCase() + " ")) {
                        if (message.substring(substringSearch).equalsIgnoreCase(clockInWords.get(i))) {
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":" + zoneMinute);
                            if (zoneHour < 10)
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " 0" + zoneHour + ":" + zoneMinute);
                            appendedTimeMsg += " I";
                            break;
                        } else if (checkForMeridiem(message.substring(substringSearch))) {
                            if (message.toUpperCase().endsWith("AM")) {
                                int amHours = 0;
                                try {
                                    String number = message.substring(message.length() - 8, message.length() - 6);
                                    if (number.contains(" "))
                                        number = number.substring(1);
                                    amHours = Integer.parseInt(number);
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " "
                                        + amHours + (message.substring(message.length() - 6, message.length() - 3)));
                            }
                            else if (message.toUpperCase().endsWith("PM")) {
                                int pmHours = 0;
                                try {
                                    String number = message.substring(message.length() - 8, message.length() - 6);
                                    if(number.contains(" "))
                                        number = number.substring(1);
                                    pmHours = Integer.parseInt(number);
                                    if (pmHours != 12)
                                        pmHours += 12;
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " "
                                        + pmHours + (message.substring(message.length() - 6, message.length() - 3)));
                            }
                            appendedTimeMsg += " I";
                            break;
                        } else
                            appendedTimeMsg = "";
                        appendedTimeMsg += " I";
                    }
                }
                for (int i = 0; i < clockOutWords.size(); i++) {// Appends clock out time
                    if (message.substring(substringSearch).equalsIgnoreCase(clockOutWords.get(i))) {
                        if(zoneHour < 10 && zoneMinute < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " 0" + zoneHour + ":0" + zoneMinute);
                        else if(zoneHour < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " 0" + zoneHour + ":" + zoneMinute);
                        else if(zoneMinute < 10)
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":0" + zoneMinute);
                        else
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":" + zoneMinute);
                        appendedTimeMsg += " O";
                    }
                    else if (message.toLowerCase().contains(" " + clockOutWords.get(i).toLowerCase() + " ")
                            && !message.toLowerCase().contains(" " + clockInWords.get(i).toLowerCase() + " ")) {
                        if (message.substring(substringSearch).equalsIgnoreCase(clockOutWords.get(i))) {
                            appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                    + " " + zoneDayOfWeek + " " + zoneHour + ":" + zoneMinute);
                            if (m.getTime().atZoneSameInstant(timeZone).getHour() < 10)
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " 0" + zoneHour + ":" + zoneMinute);
                            appendedTimeMsg += " O";
                            break;
                        } else if (checkForMeridiem(message.substring(substringSearch))) {
                            if (message.toUpperCase().endsWith("AM")) {
                                int amHours = 0;
                                try {
                                    String number = message.substring(message.length() - 8, message.length() - 6);
                                    if (number.contains(" "))
                                        number = number.substring(1);
                                    amHours = Integer.parseInt(number);
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " "
                                        + amHours + (message.substring(message.length() - 6, message.length() - 3)));
                            }
                            else if (message.toUpperCase().endsWith("PM")) {
                                int pmHours = 0;
                                try {
                                    String number = message.substring(message.length() - 8, message.length() - 6);
                                    if(number.contains(" "))
                                        number = number.substring(1);
                                    pmHours = Integer.parseInt(number);
                                    if (pmHours != 12)
                                        pmHours += 12;
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                                appendedTimeMsg = (message + " <|> " + mentionedUser + " " + appendDate
                                        + " " + zoneDayOfWeek + " "
                                        + pmHours + (message.substring(message.length() - 6, message.length() - 3)));
                            }
                            appendedTimeMsg += " O";
                            break;
                        } else
                            appendedTimeMsg = "";
                        appendedTimeMsg += " O";
                    }
                }
                if(appendedTimeMsg.length() > 2){
                    stringList.add(appendedTimeMsg);
                }
            }
        }

        return stringList;
    }

    private boolean checkForMeridiem(String s){
        if(s.toUpperCase().endsWith("AM"))
            return true;
        else if(s.toUpperCase().endsWith("PM"))
            return true;

        return false;
    }

    private void sendMessages(User receiver, String[] logs){
        String separator = "";
        for(int i = 0; i < TIMESTAMP.length(); i++)
            separator += "-";
        for (String s : logs) {
            receiver.getPrivateChannel().sendMessage(s + "\n" + separator);
            pause(2);
        }
    }

    private void setUserMessages(User user, TextChannel channel){
        List<Message> messages = new ArrayList<>();

        MessageLogger messagelogger = new MessageLogger();
        List<Message> channelMessages = messagelogger.getChannelLog(channel);
        messages.addAll(channelMessages.stream().filter(m -> m.isMentioned(user)).collect(Collectors.toList()));

        userTimeLogs.put(user, messages);
    }

    private String convertListToString(List<String> list){
        String message = "";
        for(String m : list)
            message += m + "\n";
        return message;
    }

    private String getTimeStamp(Temporal co){
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern(TIMESTAMP);
        String str = fmt.format(co);
        return str;
    }

    private void pause(int seconds){
        try {
            TimeUnit.SECONDS.sleep(seconds);
        }catch (Exception e){e.printStackTrace();}
    }

}