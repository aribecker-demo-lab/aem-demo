package dev.wknd.demo.weather;

import java.util.List;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class SystemLogsServiceTest {
    @Test
    public void keepsBuildStepsAndOmitsArbitraryOutput() {
        assertEquals(List.of("BUILD DEMO: Generated FileVault content package", "[INFO] BUILD SUCCESS"),
            SystemLogsService.buildEvents(List.of("private environment value",
                "BUILD DEMO: Generated FileVault content package", "[INFO] BUILD SUCCESS")));
    }

    @Test
    public void summarizesInstallationFailuresWithoutRawDetails() {
        assertEquals(List.of("ERROR · wknd-demo-adventure · failure reported"),
            SystemLogsService.runtimeEvents(List.of(
                "*ERROR* Failed to install wknd-demo-adventure: private exception detail")));
    }

    @Test
    public void keepsOnlyStructuredWeatherEvents() {
        String event = "WKND_WEATHER BACKUP_SUCCESS trace=abc01234-1234-1234-1234-123456789abc durationMs=12";
        assertEquals(List.of(event), SystemLogsService.runtimeEvents(List.of(
            "dev.wknd.demo.weather.WeatherService " + event,
            "dev.wknd.demo.weather.WeatherService " + event + " unexpected payload")));
    }
}
