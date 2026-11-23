package dev.wknd.demo.weather;

import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.Test;

import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class WeatherServiceTest {
    private static final Instant START = Instant.parse("2026-11-23T12:00:00Z");
    private static final Clock FIXED_CLOCK = Clock.fixed(START, ZoneOffset.UTC);
    private static final Weather READING = new Weather(
        "Bali", 27, 80, 9, "rain", "Open-Meteo", START.toString());

    @Test
    public void usesBackupWhenPrimaryFails() {
        WeatherService service = new WeatherService(FIXED_CLOCK,
            () -> { throw new IOException("Primary offline"); },
            () -> READING);

        assertSame(READING, service.currentWeather());
    }

    @Test
    public void skipsBackupWhenPrimarySucceeds() {
        WeatherService service = new WeatherService(FIXED_CLOCK, () -> READING, () -> {
            fail("Backup should only run when primary fails");
            return null;
        });

        assertSame(READING, service.currentWeather());
    }

    @Test
    public void reportsUnavailableWhenBothProvidersFail() {
        WeatherService service = new WeatherService(FIXED_CLOCK,
            () -> { throw new IOException("Primary offline"); },
            () -> { throw new IOException("Backup offline"); });

        assertNull(service.currentWeather());
    }

    @Test
    public void refreshesSuccessfulReadingAfterFiveMinutes() throws Exception {
        Clock clock = mock(Clock.class);
        WeatherService.Provider primary = mock(WeatherService.Provider.class);
        when(primary.get()).thenReturn(READING);
        when(clock.instant()).thenReturn(START);
        WeatherService service = new WeatherService(clock, primary, () -> null);

        assertSame(READING, service.currentWeather());
        when(clock.instant()).thenReturn(START.plusSeconds(299));
        assertSame(READING, service.currentWeather());
        verify(primary, times(1)).get();

        when(clock.instant()).thenReturn(START.plusSeconds(300));
        assertSame(READING, service.currentWeather());
        verify(primary, times(2)).get();
    }

    @Test
    public void retriesUnavailableReadingAfterThirtySeconds() throws Exception {
        Clock clock = mock(Clock.class);
        WeatherService.Provider primary = mock(WeatherService.Provider.class);
        when(primary.get()).thenReturn(null, READING);
        when(clock.instant()).thenReturn(START);
        WeatherService service = new WeatherService(clock, primary, () -> null);

        assertNull(service.currentWeather());
        when(clock.instant()).thenReturn(START.plusSeconds(29));
        assertNull(service.currentWeather());
        verify(primary, times(1)).get();

        when(clock.instant()).thenReturn(START.plusSeconds(30));
        assertSame(READING, service.currentWeather());
        verify(primary, times(2)).get();
    }
}
