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
    @Test
    public void keepsUnrelatedMessagesAndStackFramesInOrder() {
        String packageLine = "24.11.2026 22:00:00.001 *INFO* Installing aem-guides-wknd";
        String bundleLine = "24.11.2026 22:00:00.003 *WARN* Could not resolve dev.wknd.demo.weather bundle";
        List<String> lines = List.of(packageLine, "Installing an unrelated bundle", bundleLine,
            "\tat org.apache.felix.Framework.start(Framework.java:42)");
        assertEquals(lines, SystemLogsService.recentAemLog(lines));
    }

    @Test
    public void withholdsEntriesThatContainSensitiveFields() {
        assertEquals(List.of("[Log entry withheld: potentially sensitive data]"),
            SystemLogsService.recentAemLog(List.of("Installing wknd-demo-adventure token=secret-value")));
    }
}
