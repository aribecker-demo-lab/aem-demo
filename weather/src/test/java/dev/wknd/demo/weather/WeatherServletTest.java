package dev.wknd.demo.weather;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.time.Clock;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.apache.sling.api.SlingHttpServletResponse;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class WeatherServletTest {
    private final StringWriter body = new StringWriter();
    private final SlingHttpServletResponse response = mock(SlingHttpServletResponse.class);

    @Before
    public void captureResponse() throws Exception {
        when(response.getWriter()).thenReturn(new PrintWriter(body));
    }

    @Test
    public void writesWeatherAsJson() throws Exception {
        Weather reading = new Weather("Bali", 27, 80, 9, "rain", "MET Norway",
            "2026-11-23T12:00:00Z");
        WeatherService service = new WeatherService(Clock.systemUTC(), () -> reading, () -> null);

        new WeatherServlet(service).doGet(null, response);

        verify(response).setContentType("application/json;charset=UTF-8");
        verify(response).setHeader("Cache-Control", "no-store");
        verify(response, never()).setStatus(503);
        JsonObject json = JsonParser.parseString(body.toString()).getAsJsonObject();
        assertEquals("Bali", json.get("location").getAsString());
        assertEquals(27, json.get("temperature").getAsDouble(), 0);
        assertEquals("MET Norway", json.get("source").getAsString());
    }

    @Test
    public void returns503WithJsonWhenWeatherIsUnavailable() throws Exception {
        WeatherService service = new WeatherService(Clock.systemUTC(), () -> null, () -> null);

        new WeatherServlet(service).doGet(null, response);

        verify(response).setStatus(503);
        assertEquals("Weather is temporarily unavailable.",
            JsonParser.parseString(body.toString()).getAsJsonObject().get("error").getAsString());
    }
}
