package dev.wknd.demo.weather;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryUsage;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Pattern;

import org.apache.sling.settings.SlingSettingsService;
import org.osgi.framework.Bundle;
import org.osgi.framework.BundleContext;
import org.osgi.framework.Constants;

final class SystemSettings {
    private static final Pattern SDK = Pattern.compile(
        "aem-sdk-quickstart-(\\d{4}\\.\\d+\\.\\d+(?:\\.\\d+)?)(?:-[^/ ]*)?\\.jar");

    private SystemSettings() {}

    static List<Group> read(SlingSettingsService sling, Bundle current) {
        var runtime = ManagementFactory.getRuntimeMXBean();
        var memory = ManagementFactory.getMemoryMXBean();
        var threads = ManagementFactory.getThreadMXBean();
        var os = ManagementFactory.getOperatingSystemMXBean();
        BundleContext context = current == null ? null : current.getBundleContext();
        Bundle[] bundles = context == null ? new Bundle[0] : context.getBundles();
        return List.of(
            new Group("AEM and Sling", List.of(
                new Value("AEM SDK version", sdkVersion()),
                new Value("Run modes", sling == null ? "Unavailable" :
                    String.join(", ", sling.getRunModes().stream().sorted().toList())),
                new Value("Sling instance", sling == null ? "Unavailable" : sling.getSlingName()),
                new Value("Sling ID", sling == null ? "Unavailable" : sling.getSlingId()),
                new Value("Sling home", sling == null ? "Unavailable" : sling.getSlingHomePath()),
                new Value("Core Components", bundleVersion(bundles, "com.adobe.cq.core.wcm.components.core")),
                new Value("Oak JCR", bundleVersion(bundles, "org.apache.jackrabbit.oak-jcr")),
                new Value("Weather and diagnostics", current == null ? "Unavailable" : current.getVersion().toString())
            )),
            new Group("Java and JVM", List.of(
                new Value("Java version", System.getProperty("java.runtime.version", "Unavailable")),
                new Value("Java vendor", runtime.getVmVendor()),
                new Value("Virtual machine", runtime.getVmName()),
                new Value("Virtual machine version", runtime.getVmVersion()),
                new Value("Started at (UTC)", Instant.ofEpochMilli(runtime.getStartTime()).toString()),
                new Value("Uptime", Duration.ofMillis(runtime.getUptime()).toSeconds() + " s"),
                new Value("Heap used / committed / max", memory(memory.getHeapMemoryUsage())),
                new Value("Non-heap used / committed / max", memory(memory.getNonHeapMemoryUsage())),
                new Value("Threads current / peak", threads.getThreadCount() + " / " + threads.getPeakThreadCount()),
                new Value("Garbage collectors", String.join(", ", ManagementFactory.getGarbageCollectorMXBeans()
                    .stream().map(gc -> gc.getName()).toList()))
            )),
            new Group("Operating system", List.of(
                new Value("Name", os.getName()),
                new Value("Version", os.getVersion()),
                new Value("Architecture", os.getArch()),
                new Value("Available processors", Integer.toString(os.getAvailableProcessors()))
            )),
            new Group("OSGi framework", List.of(
                new Value("Vendor", frameworkProperty(context, Constants.FRAMEWORK_VENDOR)),
                new Value("Version", frameworkProperty(context, Constants.FRAMEWORK_VERSION)),
                new Value("Installed bundles", Integer.toString(bundles.length)),
                new Value("Active bundles", Long.toString(Arrays.stream(bundles)
                    .filter(bundle -> bundle.getState() == Bundle.ACTIVE).count()))
            )),
            new Group("OSGi bundle inventory", Arrays.stream(bundles)
                .filter(bundle -> bundle.getSymbolicName() != null)
                .sorted(Comparator.comparing(Bundle::getSymbolicName).thenComparing(Bundle::getVersion))
                .map(bundle -> new Value(bundle.getSymbolicName(), bundle.getVersion() + " · " + state(bundle)))
                .toList())
        );
    }

    private static String sdkVersion() {
        var matcher = SDK.matcher(System.getProperty("java.class.path", ""));
        if (matcher.find()) {
            return matcher.group(1);
        }
        return "2026.2.24464 (configured base Docker image)";
    }

    private static String bundleVersion(Bundle[] bundles, String symbolicName) {
        return Arrays.stream(bundles).filter(bundle -> symbolicName.equals(bundle.getSymbolicName()))
            .map(Bundle::getVersion).max(Comparator.naturalOrder()).map(Object::toString).orElse("Unavailable");
    }

    private static String frameworkProperty(BundleContext context, String key) {
        String value = context == null ? null : context.getProperty(key);
        return value == null ? "Unavailable" : value;
    }

    private static String memory(MemoryUsage usage) {
        return mib(usage.getUsed()) + " / " + mib(usage.getCommitted()) + " / " + mib(usage.getMax());
    }

    private static String mib(long bytes) {
        return bytes < 0 ? "Unspecified" : (bytes / (1024 * 1024)) + " MiB";
    }

    private static String state(Bundle bundle) {
        return switch (bundle.getState()) {
            case Bundle.ACTIVE -> "Active";
            case Bundle.INSTALLED -> "Installed";
            case Bundle.RESOLVED -> "Resolved";
            case Bundle.STARTING -> "Starting";
            case Bundle.STOPPING -> "Stopping";
            default -> "Uninstalled";
        };
    }

    record Value(String name, String value) {}
    record Group(String title, List<Value> values) {}
}
