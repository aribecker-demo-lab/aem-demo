package dev.wknd.demo.weather;

import java.io.PrintWriter;
import java.io.StringWriter;
import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.api.SlingHttpServletResponse;
import org.apache.sling.api.resource.ResourceResolver;
import org.junit.Test;

import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class SystemLogsServletTest {
    private final SlingHttpServletRequest request = mock(SlingHttpServletRequest.class);
    private final SlingHttpServletResponse response = mock(SlingHttpServletResponse.class);
    private final ResourceResolver resolver = mock(ResourceResolver.class);
    private final SystemLogsServlet servlet = new SystemLogsServlet(new SystemLogsService());

    @Test
    public void deniesNonAdminWithoutOpeningResponseWriter() throws Exception {
        when(request.getResourceResolver()).thenReturn(resolver);
        when(resolver.getUserID()).thenReturn("author");
        servlet.doGet(request, response);
        verify(response).sendError(403);
        verify(response, never()).getWriter();
    }

    @Test
    public void returnsDiagnosticsToAdminWithNoStore() throws Exception {
        when(request.getResourceResolver()).thenReturn(resolver);
        when(resolver.getUserID()).thenReturn("admin");
        StringWriter body = new StringWriter();
        when(response.getWriter()).thenReturn(new PrintWriter(body));
        servlet.doGet(request, response);
        verify(response).setHeader("Cache-Control", "no-store");
        assertTrue(body.toString().contains("\"status\""));
        assertTrue(body.toString().contains("\"runtime\""));
        assertTrue(body.toString().contains("\"systemSettings\""));
    }
}
