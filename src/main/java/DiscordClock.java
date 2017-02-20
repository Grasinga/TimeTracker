import net.dv8tion.jda.core.entities.Message;

import java.util.Calendar;
import java.util.Date;

/**
 * DiscordClock contains values for a clock in/out message. Values are as follows:<br>
 * {@link #type} = "In" or "Out".<br>
 * {@link #message} = The clock in/out message from Discord.<br>
 * {@link #calendar} instance needed for the {@link Calendar#HOUR_OF_DAY} and {@link Calendar#MINUTE} of the clock.<br>
 * {@link #time} = The time of the clock in quarter hours.
 */
class DiscordClock {

    /**
     * "In" or "Out" value of the clock.
     */
    private String type;

    /**
     * The clock in/out message from Discord.
     */
    private Message message;

    /**
     * {@link Calendar} instance needed for the {@link Calendar#HOUR_OF_DAY} and {@link Calendar#MINUTE} of the clock.
     */
    private Calendar calendar;

    /**
     * The time of the clock in quarter hours.
     */
    private double time;

    /**
     * Creates a {@link DiscordClock} with the passed in type, message, and timestamp.
     *
     * @param type "In" or "Out" value of the clock.
     * @param message The clock in/out message from Discord.
     * @param timestamp Date used to set the time for {@link #calendar}.
     */
    DiscordClock(String type, Message message, Date timestamp) {
        this.type = type;
        this.message = message;
        calendar = Calendar.getInstance();
        calendar.setTime(timestamp);
        setTime();
    }

    /**
     * Sets the {@link #time} of the {@link DiscordClock} using the {@link #calendar} instance.
     */
    private void setTime() {
        double hour = calendar.get(Calendar.HOUR_OF_DAY);
        double minutes = (calculateQuarterMinutes(calendar.get(Calendar.MINUTE)) / 60.0);

        // Set minutes to 0 instead of 1 and then increase the hour by one.
        if(calculateQuarterMinutes(calendar.get(Calendar.MINUTE)) == 60) {
            minutes = 0.0;
            hour++;
        }

        time =  hour + minutes;
    }

    /**
     * Calculates the quarter hour based on the minutes given. Used in {@link #setTime()}.
     *
     * @param minutes Minutes to be converted into a quarter hour amount (divide by 60).
     * @return Minutes in the form of a quarter hour. (0, 15, 30, 45)
     */
    private int calculateQuarterMinutes(int minutes) {
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
                    return 60; // Hour needs to increase.
                }
                break;
        }

        return (tens * 10) + ones;
    } // End of calculateQuarterMinutes()

    /**
     * @return The {@link #type} of the {@link DiscordClock}.
     */
    String getType() { return type; }

    /**
     * @return The {@link #message} of the {@link DiscordClock}.
     */
    Message getMessage() { return message; }

    /**
     * @return The {@link #time} of the {@link DiscordClock}.
     */
    double getTime() { return time; }
}
