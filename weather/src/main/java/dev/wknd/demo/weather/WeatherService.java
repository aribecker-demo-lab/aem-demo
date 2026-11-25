package dev.wknd.demo.weather;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Deactivate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component(service = WeatherService.class)
public final class WeatherService {
    private static final Logger LOG = LoggerFactory.getLogger(WeatherService.class);
    private static final String LOCATION = "Bali, Indonesia";
    private static final String MET_URL =
        "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=-8.65&lon=115.22";
    private static final String OPEN_METEO_URL =
        "https://api.open-meteo.com/v1/forecast?latitude=-8.65&longitude=115.22"
        + "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code";
    private static final Duration TIMEOUT = Duration.ofSeconds(4);

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(TIMEOUT).build();
    private final Clock clock;
    private final Provider primary;
    private final Provider backup;
    private Weather cachedWeather;
    private String trace;
    private Instant refreshAfter = Instant.EPOCH;

    public WeatherService() {
        clock = Clock.systemUTC();
        primary = this::metNorway;
        backup = this::openMeteo;
    }

    WeatherService(Clock clock, Provider primary, Provider backup) {
        this.clock = clock;
        this.primary = primary;
        this.backup = backup;
    }

    @Activate
    void activate() {
        LOG.info("WKND_WEATHER SERVICE_ACTIVATED location={}", LOCATION);
    }

    @Deactivate
    void deactivate() {
        LOG.info("WKND_WEATHER SERVICE_DEACTIVATED location={}", LOCATION);
    }

    void requestStage(String stage, int status, long durationMs) {
        LOG.info("WKND_WEATHER {} status={} durationMs={}", stage, status, durationMs);
    }

    public synchronized Weather currentWeather() {
        Instant now = clock.instant();
        if (now.isBefore(refreshAfter)) {
            LOG.info("WKND_WEATHER CACHE_HIT trace={}", trace);
            LOG.info("WKND_WEATHER CACHE_STATE trace={} available={} remainingMs={}",
                trace, cachedWeather != null, Duration.between(now, refreshAfter).toMillis());
            return cachedWeather;
        }
        trace = UUID.randomUUID().toString();
        LOG.info("WKND_WEATHER CACHE_MISS trace={}", trace);
        LOG.info("WKND_WEATHER REFRESH_START trace={} location={} checkedAt={}", trace, LOCATION, now);
        cachedWeather = firstAvailable(primary, backup, trace);
        refreshAfter = clock.instant().plusSeconds(cachedWeather == null ? 30 : 300);
        LOG.info("WKND_WEATHER CACHE_UPDATED trace={}", trace);
        LOG.info("WKND_WEATHER REFRESH_RESULT trace={} available={} nextRefreshAt={}",
            trace, cachedWeather != null, refreshAfter);
        return cachedWeather;
    }

    private static Weather firstAvailable(Provider primary, Provider backup, String trace) {
        Weather weather = tryProvider(primary, "PRIMARY", trace);
        if (weather == null && !Thread.currentThread().isInterrupted()) {
            LOG.info("WKND_WEATHER FALLBACK trace={} reason=primary_unavailable", trace);
            return tryProvider(backup, "BACKUP", trace);
        }
        return weather;
    }

    private static Weather tryProvider(Provider provider, String name, String trace) {
        long started = System.nanoTime();
        Weather reading = null;
        LOG.info("WKND_WEATHER PROVIDER_START trace={} role={}", trace, name);
        try {
            reading = provider.get();
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            LOG.info("WKND_WEATHER PROVIDER_ERROR trace={} role={} type=InterruptedException", trace, name);
        } catch (IOException | RuntimeException failure) {
            LOG.info("WKND_WEATHER PROVIDER_ERROR trace={} role={} type={}",
                trace, name, failure.getClass().getSimpleName());
        }
        LOG.info("WKND_WEATHER {} trace={} durationMs={}",
            name + (reading == null ? "_FAILED" : "_SUCCESS"), trace,
            (System.nanoTime() - started) / 1_000_000);
        if (reading != null) {
            LOG.info("WKND_WEATHER READING trace={} role={} temperatureC={} humidityPct={} windKmh={}",
                trace, name, reading.temperature(), reading.humidity(), reading.wind());
        }
        return reading;
    }

    private JsonObject fetch(String provider, String url) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
            .timeout(TIMEOUT)
            .header("Accept", "application/json")
            .header("User-Agent", "WKND-Weather-Demo/1.0 https://github.com/aribecker-demo-lab/aem-demo")
            .build();
        LOG.info("WKND_WEATHER HTTP_START trace={} provider={} method=GET url={} timeoutMs={}",
            trace, provider, url, TIMEOUT.toMillis());
        long started = System.nanoTime();
        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        LOG.info("WKND_WEATHER HTTP_RESULT trace={} provider={} status={} durationMs={} responseChars={}",
            trace, provider, response.statusCode(),
            (System.nanoTime() - started) / 1_000_000, response.body().length());
        if (response.statusCode() != 200) {
            throw new IOException("Weather provider returned HTTP " + response.statusCode());
        }
        JsonObject payload = JsonParser.parseString(response.body()).getAsJsonObject();
        LOG.info("WKND_WEATHER JSON_PARSED trace={} provider={}", trace, provider);
        return payload;
    }

    private Weather metNorway() throws IOException, InterruptedException {
        JsonObject forecast = fetch("MET_NORWAY", MET_URL).getAsJsonObject("properties")
            .getAsJsonArray("timeseries").get(0).getAsJsonObject();
        JsonObject data = forecast.getAsJsonObject("data");
        JsonObject details = data.getAsJsonObject("instant").getAsJsonObject("details");
        String condition = data.getAsJsonObject("next_1_hours").getAsJsonObject("summary")
            .get("symbol_code").getAsString()
            .replaceFirst("_(day|night|polartwilight)$", "").replace('_', ' ');
        return new Weather(LOCATION, details.get("air_temperature").getAsDouble(),
            details.get("relative_humidity").getAsDouble(),
            details.get("wind_speed").getAsDouble() * 3.6, condition, "MET Norway",
            forecast.get("time").getAsString());
    }

    private Weather openMeteo() throws IOException, InterruptedException {
        JsonObject current = fetch("OPEN_METEO", OPEN_METEO_URL).getAsJsonObject("current");
        int code = current.get("weather_code").getAsInt();
        String condition = switch (code) {
            case 0 -> "clear sky";
            case 1, 2 -> "partly cloudy";
            case 3 -> "overcast";
            case 45, 48 -> "fog";
            case 51, 53, 55, 56, 57 -> "drizzle";
            case 61, 63, 65, 66, 67, 80, 81, 82 -> "rain";
            case 71, 73, 75, 77, 85, 86 -> "snow";
            case 95, 96, 99 -> "thunderstorm";
            default -> "unknown conditions";
        };
        return new Weather(LOCATION, current.get("temperature_2m").getAsDouble(),
            current.get("relative_humidity_2m").getAsDouble(),
            current.get("wind_speed_10m").getAsDouble(), condition, "Open-Meteo",
            current.get("time").getAsString() + "Z");
    }

    @FunctionalInterface
    interface Provider {
        Weather get() throws IOException, InterruptedException;
    }

}
