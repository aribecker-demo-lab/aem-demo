package dev.wknd.demo.weather;

import java.io.IOException;
import javax.servlet.Servlet;
import javax.servlet.http.HttpServletResponse;

import com.google.gson.Gson;
import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.api.SlingHttpServletResponse;
import org.apache.sling.api.servlets.SlingSafeMethodsServlet;
import org.osgi.framework.Bundle;
import org.osgi.framework.FrameworkUtil;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

@Component(service = Servlet.class, property = {
    "service.ranking:Integer=100",
    "sling.servlet.resourceTypes=wknd-demo/components/weather",
    "sling.servlet.selectors=current",
    "sling.servlet.extensions=json",
    "sling.servlet.methods=GET"
})
public final class WeatherServlet extends SlingSafeMethodsServlet {
    private static final Gson JSON = new Gson();
    private final WeatherService weatherService;

    @Activate
    public WeatherServlet(@Reference WeatherService weatherService) {
        this.weatherService = weatherService;
    }

    @Override
    protected void doGet(SlingHttpServletRequest request, SlingHttpServletResponse response)
            throws IOException {
        response.setContentType("application/json;charset=UTF-8");
        response.setHeader("Cache-Control", "no-store");
        Bundle bundle = FrameworkUtil.getBundle(WeatherServlet.class);
        if (bundle != null) {
            response.setHeader("X-WKND-Weather-Bundle", bundle.getVersion().toString());
        }
        Weather current = weatherService.currentWeather();
        if (current == null) {
            response.setStatus(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
            response.getWriter().write("{\"error\":\"Weather is temporarily unavailable.\"}");
            return;
        }
        JSON.toJson(current, response.getWriter());
    }

}
