package dev.wknd.demo.weather;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.NoSuchFileException;
import javax.servlet.Servlet;

import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.api.SlingHttpServletResponse;
import org.apache.sling.api.resource.Resource;
import org.apache.sling.api.servlets.SlingSafeMethodsServlet;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

@Component(service = Servlet.class, property = {
    "sling.servlet.resourceTypes=wknd-demo/components/weather",
    "sling.servlet.selectors=weatherdocs",
    "sling.servlet.extensions=json",
    "sling.servlet.methods=GET"
})
public final class WeatherDiagnosticsServlet extends SlingSafeMethodsServlet {
    private final SystemLogsService logs;

    @Activate
    public WeatherDiagnosticsServlet(@Reference SystemLogsService logs) {
        this.logs = logs;
    }

    @Override
    protected void doGet(SlingHttpServletRequest request, SlingHttpServletResponse response) throws IOException {
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("X-Content-Type-Options", "nosniff");
        if (!"admin".equals(request.getResourceResolver().getUserID())) {
            response.sendError(403);
            return;
        }
        if ("log".equals(request.getParameter("view"))) {
            try (BufferedReader reader = logs.openWeatherLog()) {
                response.setContentType("text/plain;charset=UTF-8");
                SystemLogsService.writeLog(reader, response.getWriter());
            } catch (NoSuchFileException missing) {
                response.sendError(404);
            }
            return;
        }
        Resource snapshot = request.getResourceResolver()
            .getResource("/apps/wknd-demo/components/weather/weather-sources.json");
        try (InputStream input = snapshot == null ? null : snapshot.adaptTo(InputStream.class)) {
            if (input == null) {
                response.sendError(404);
                return;
            }
            response.setContentType("application/json;charset=UTF-8");
            input.transferTo(response.getOutputStream());
        }
    }
}
