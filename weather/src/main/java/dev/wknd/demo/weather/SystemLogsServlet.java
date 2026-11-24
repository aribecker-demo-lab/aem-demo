package dev.wknd.demo.weather;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.NoSuchFileException;
import javax.servlet.Servlet;
import javax.servlet.http.HttpServletResponse;

import com.google.gson.Gson;
import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.api.SlingHttpServletResponse;
import org.apache.sling.api.servlets.SlingSafeMethodsServlet;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

@Component(service = Servlet.class, property = {
    "service.ranking:Integer=100",
    "sling.servlet.resourceTypes=wknd-demo/components/system-logs",
    "sling.servlet.selectors=diagnostics",
    "sling.servlet.extensions=json",
    "sling.servlet.methods=GET"
})
public final class SystemLogsServlet extends SlingSafeMethodsServlet {
    private static final Gson JSON = new Gson();
    private final SystemLogsService logs;

    @Activate
    public SystemLogsServlet(@Reference SystemLogsService logs) {
        this.logs = logs;
    }

    @Override
    protected void doGet(SlingHttpServletRequest request, SlingHttpServletResponse response)
            throws IOException {
        response.setHeader("Cache-Control", "no-store");
        if (!"admin".equals(request.getResourceResolver().getUserID())) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }
        String path = request.getParameter("log");
        if (path != null) {
            try (BufferedReader reader = logs.openLog(path)) {
                response.setHeader("X-Content-Type-Options", "nosniff");
                response.setContentType("text/plain;charset=UTF-8");
                SystemLogsService.writeLog(reader, response.getWriter());
            } catch (NoSuchFileException failure) {
                response.sendError(HttpServletResponse.SC_NOT_FOUND);
            }
            return;
        }
        response.setContentType("application/json;charset=UTF-8");
        JSON.toJson(logs.read(request.getResourceResolver()), response.getWriter());
    }
}
