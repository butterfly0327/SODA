package ssafy.E105.global.common.util;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

public final class KstDateTimeFormatter {

    private static final ZoneOffset KST_OFFSET = ZoneOffset.ofHours(9);
    private static final DateTimeFormatter ISO_OFFSET_DATE_TIME = DateTimeFormatter.ISO_OFFSET_DATE_TIME;
    private static final DateTimeFormatter ISO_LOCAL_DATE = DateTimeFormatter.ISO_LOCAL_DATE;

    private KstDateTimeFormatter() {
    }

    public static String format(LocalDateTime value) {
        if (value == null) {
            return null;
        }
        return value.atOffset(KST_OFFSET).format(ISO_OFFSET_DATE_TIME);
    }

    public static String formatDate(LocalDateTime value) {
        if (value == null) {
            return null;
        }
        return value.toLocalDate().format(ISO_LOCAL_DATE);
    }
}
