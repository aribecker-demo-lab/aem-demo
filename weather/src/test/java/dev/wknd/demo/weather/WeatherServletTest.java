package dev.wknd.demo.weather;

import java.io.IOException;
import org.junit.Test;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.fail;

public class WeatherServletTest {
    private static final WeatherServlet.Weather READING = new WeatherServlet.Weather(
        "Bali", 27, 80, 9, "rain", "Open-Meteo", "2026-11-23T12:00:00Z");

    @Test
    public void usesBackupWhenPrimaryFails() {
        assertSame(READING, WeatherServlet.firstAvailable(
            () -> { throw new IOException("Primary offline"); },
            () -> READING));
    }

    @Test
    public void skipsBackupWhenPrimarySucceeds() {
        assertSame(READING, WeatherServlet.firstAvailable(() -> READING, () -> {
            fail("Backup should only run when primary fails");
            return null;
        }));
    }

    @Test
    public void reportsUnavailableWhenBothProvidersFail() {
        assertNull(WeatherServlet.firstAvailable(
            () -> { throw new IOException("Primary offline"); },
            () -> { throw new IOException("Backup offline"); }));
    }
}
