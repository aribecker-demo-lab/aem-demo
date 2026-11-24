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
import org.osgi.service.component.annotations.Component;
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

    public synchronized Weather currentWeather() {
        if (clock.instant().isBefore(refreshAfter)) {
            LOG.info("WKND_WEATHER CACHE_HIT trace={}", trace);
            return cachedWeather;
        }
        trace = UUID.randomUUID().toString();
        LOG.info("WKND_WEATHER CACHE_MISS trace={}", trace);
        cachedWeather = firstAvailable(primary, backup, trace);
        refreshAfter = clock.instant().plusSeconds(cachedWeather == null ? 30 : 300);
        LOG.info("WKND_WEATHER CACHE_UPDATED trace={}", trace);
        return cachedWeather;
    }

    private static Weather firstAvailable(Provider primary, Provider backup, String trace) {
        Weather weather = tryProvider(primary, "PRIMARY", trace);
        if (weather == null && !Thread.currentThread().isInterrupted()) {
            return tryProvider(backup, "BACKUP", trace);
        }
        return weather;
    }

    private static Weather tryProvider(Provider provider, String name, String trace) {
        long started = System.nanoTime();
        Weather reading = null;
        try {
            reading = provider.get();
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
        } catch (IOException | RuntimeException failure) {
            // Provider response bodies and exception details stay out of the diagnostic feed.
        }
        LOG.info("WKND_WEATHER {} trace={} durationMs={}",
            name + (reading == null ? "_FAILED" : "_SUCCESS"), trace,
            (System.nanoTime() - started) / 1_000_000);
        return reading;
    }

    private JsonObject fetch(String url) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
            .timeout(TIMEOUT)
            .header("Accept", "application/json")
            .header("User-Agent", "WKND-Weather-Demo/1.0 https://github.com/aribecker-demo-lab/aem-demo")
            .build();
        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) {
            throw new IOException("Weather provider returned HTTP " + response.statusCode());
        }
        return JsonParser.parseString(response.body()).getAsJsonObject();
    }

    private Weather metNorway() throws IOException, InterruptedException {
        JsonObject forecast = fetch(MET_URL).getAsJsonObject("properties")
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
        JsonObject current = fetch(OPEN_METEO_URL).getAsJsonObject("current");
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
