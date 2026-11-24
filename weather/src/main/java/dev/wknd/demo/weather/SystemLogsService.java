package dev.wknd.demo.weather;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

import org.apache.sling.api.resource.ResourceResolver;
import org.osgi.framework.Bundle;
import org.osgi.framework.FrameworkUtil;
import org.osgi.service.component.annotations.Component;

@Component(service = SystemLogsService.class)
public final class SystemLogsService {
    private static final int MAX_BYTES = 512 * 1024;
    private static final Path AEM_LOG = Path.of("/aem/crx-quickstart/logs/error.log");
    private static final Path BUILD_LOG = Path.of("/opt/wknd-diagnostics/build.log");
    private static final List<String> PACKAGE_NAMES = List.of(
        "aem-guides-wknd", "wknd-demo-adventure", "dev.wknd.demo.weather");
    private static final Pattern LIFECYCLE = Pattern.compile("install|bundle|start|activat|resolv|deploy");
    private static final Pattern SENSITIVE = Pattern.compile(
        "(?i)\\b(?:authorization|proxy-authorization|cookie|set-cookie|password|passwd|"
        + "secret|token|api[_-]?key|credential|session[_-]?id)\\s*[:=]|\\b(?:basic|bearer)\\s+"
        + "|://[^\\s/@]+:[^\\s/@]+@");
    private static final String WKND = "/content/wknd/us/en";
    private static final String TEMPLATE = "/conf/wknd/settings/wcm/templates/adventure-page-template-demo";

    Snapshot read(ResourceResolver resolver) {
        Bundle bundle = FrameworkUtil.getBundle(getClass());
        List<String> aemLines = tail(AEM_LOG);
        return new Snapshot(System.getenv("RENDER_GIT_COMMIT"), System.getenv("RENDER_SERVICE_ID"),
            List.of(
                status("WKND Sites sample content", resolver, WKND + "/adventures"),
                status("WKND Demo content package", resolver, WKND + "/aem-demo/system-logs"),
                status("Adventure Page Template - Demo", resolver, TEMPLATE),
                status("Weather component definition", resolver, "/apps/wknd-demo/components/weather"),
                new Status("Weather / System Logs bundle", bundle != null
                    && bundle.getState() == Bundle.ACTIVE ? "Active" : "Inactive")
            ), buildEvents(tail(BUILD_LOG)), runtimeEvents(aemLines), packageEvents(aemLines));
    }

    private static Status status(String name, ResourceResolver resolver, String path) {
        return new Status(name, resolver.getResource(path) == null
            ? "Content missing" : "Content present");
    }

    private static List<String> tail(Path path) {
        if (!Files.isRegularFile(path)) {
            return List.of();
        }
        try (RandomAccessFile file = new RandomAccessFile(path.toFile(), "r")) {
            long size = file.length();
            int count = (int) Math.min(size, MAX_BYTES);
            byte[] bytes = new byte[count];
            file.seek(size - count);
            file.readFully(bytes);
            return new String(bytes, StandardCharsets.UTF_8).lines().skip(size > count ? 1 : 0).toList();
        } catch (IOException failure) {
            return List.of();
        }
    }

    static List<String> buildEvents(List<String> lines) {
        return lines.stream()
            .map(line -> line.replaceAll("\\x1B\\[[0-9;]*m", ""))
            .filter(line -> line.matches("BUILD (WKND|DEMO|IMAGE): [A-Za-z0-9 ./:_-]+")
                || line.matches("\\[INFO\\] (?:Running dev\\.wknd\\.demo\\.weather\\.[A-Za-z]+"
                    + "|Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+, Skipped: [0-9]+.*"
                    + "|BUILD SUCCESS|--- (?:compiler|surefire|bundle):[A-Za-z0-9 .:@()-]+)"))
            .limit(80).toList();
    }

    static List<String> runtimeEvents(List<String> lines) {
        List<String> events = lines.stream().map(SystemLogsService::summarize)
            .filter(event -> !event.isEmpty()).toList();
        return events.subList(Math.max(0, events.size() - 100), events.size());
    }

    static List<String> packageEvents(List<String> lines) {
        List<String> matches = lines.stream().filter(line -> {
            String lower = line.toLowerCase(Locale.ROOT);
            return !lower.contains("wknd_weather ")
                && PACKAGE_NAMES.stream().anyMatch(lower::contains)
                && LIFECYCLE.matcher(lower).find();
        }).map(line -> {
            String clean = line.replaceAll("\\p{Cntrl}", " ").strip();
            if (SENSITIVE.matcher(clean).find()) {
                return "[Log entry withheld: potentially sensitive data]";
            }
            return clean.length() > 1200 ? clean.substring(0, 1200) + "…" : clean;
        }).toList();
        return matches.subList(Math.max(0, matches.size() - 100), matches.size());
    }

    private static String summarize(String line) {
        String timestamp = line.length() >= 23 && line.substring(0, 23)
            .matches("[0-9. :]{23}") ? line.substring(0, 23) + " · " : "";
        int traceAt = line.indexOf("WKND_WEATHER ");
        if (traceAt >= 0 && line.contains("dev.wknd.demo.weather.WeatherService")) {
            String event = line.substring(traceAt).trim();
            if (event.matches("WKND_WEATHER (?:CACHE_HIT|CACHE_MISS|CACHE_UPDATED|"
                + "PRIMARY_SUCCESS|PRIMARY_FAILED|BACKUP_SUCCESS|BACKUP_FAILED)"
                + "(?: trace=[0-9a-f-]{36})?(?: durationMs=[0-9]+)?")) {
                return timestamp + event;
            }
        }
        String lower = line.toLowerCase(Locale.ROOT);
        if (lower.contains("startup completed")) {
            return timestamp + "AEM launcher reported startup complete";
        }
        for (String name : PACKAGE_NAMES) {
            if (lower.contains(name) && (lower.contains("install") || lower.contains("bundle")
                || lower.contains("start") || lower.contains("activat"))) {
                String level = lower.contains("*error*") ? "ERROR"
                    : lower.contains("*warn*") ? "WARN" : "INFO";
                String action = lower.contains("fail") || lower.contains("exception") ? "failure reported"
                    : lower.contains("start") || lower.contains("activat") ? "startup or activation event"
                    : "installation event";
                return timestamp + level + " · " + name + " · " + action;
            }
        }
        return "";
    }

    record Status(String name, String state) {}
    record Snapshot(String commit, String renderService, List<Status> status,
                    List<String> build, List<String> runtime, List<String> packageLogs) {}
}
