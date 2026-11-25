package dev.wknd.demo.lifecycle;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.osgi.framework.Bundle;
import org.osgi.framework.BundleActivator;
import org.osgi.framework.BundleContext;
import org.osgi.framework.BundleEvent;
import org.osgi.framework.SynchronousBundleListener;
import org.osgi.service.component.runtime.ServiceComponentRuntime;
import org.osgi.service.component.runtime.dto.ComponentConfigurationDTO;

public final class LifecycleObserver implements BundleActivator, SynchronousBundleListener {
    private static final String WEATHER = "dev.wknd.demo.weather";
    private static final long MAX_BYTES = 512 * 1024;
    private final Path history = Path.of(System.getProperty("sling.home", "/aem/crx-quickstart"),
        "logs", "wknd-osgi-lifecycle.log");
    private final Map<Long, String> bundleStates = new HashMap<>();
    private Map<String, ComponentState> componentStates = Map.of();
    private ScheduledExecutorService sampler;

    @Override
    public void start(BundleContext context) {
        context.addBundleListener(this);
        for (Bundle bundle : context.getBundles()) {
            if (WEATHER.equals(bundle.getSymbolicName())) {
                baseline(bundle);
            }
        }
        sampler = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "wknd-lifecycle-sampler");
            thread.setDaemon(true);
            return thread;
        });
        sampler.scheduleWithFixedDelay(() -> sample(context), 0, 250, TimeUnit.MILLISECONDS);
    }

    @Override
    public void stop(BundleContext context) {
        context.removeBundleListener(this);
        sampler.shutdownNow();
    }

    private synchronized void baseline(Bundle bundle) {
        String state = bundleState(bundle.getState());
        if (bundleStates.putIfAbsent(bundle.getBundleId(), state) == null) {
            write("Bundle", WEATHER, bundle.getBundleId(), bundle.getVersion().toString(),
                "Unknown", state, "Observer baseline");
        }
    }

    @Override
    public synchronized void bundleChanged(BundleEvent event) {
        Bundle bundle = event.getBundle();
        if (!WEATHER.equals(bundle.getSymbolicName())) return;
        String next = bundleState(bundle.getState());
        String name = switch (event.getType()) {
            case BundleEvent.INSTALLED -> "INSTALLED";
            case BundleEvent.RESOLVED -> "RESOLVED";
            case BundleEvent.STARTING -> "STARTING";
            case BundleEvent.STARTED -> "STARTED";
            case BundleEvent.STOPPING -> "STOPPING";
            case BundleEvent.STOPPED -> "STOPPED";
            case BundleEvent.UNRESOLVED -> "UNRESOLVED";
            case BundleEvent.UNINSTALLED -> "UNINSTALLED";
            case BundleEvent.UPDATED -> "UPDATED";
            case BundleEvent.LAZY_ACTIVATION -> "LAZY_ACTIVATION";
            default -> "Bundle event " + event.getType();
        };
        long id = bundle.getBundleId();
        String previous = bundleStates.getOrDefault(id,
            event.getType() == BundleEvent.INSTALLED ? "Absent" : "Unknown");
        if (event.getType() == BundleEvent.UNINSTALLED) bundleStates.remove(id);
        else bundleStates.put(id, next);
        write("Bundle", WEATHER, id, bundle.getVersion().toString(), previous, next, name);
    }

    private void sample(BundleContext context) {
        try {
            var reference = context.getServiceReference(ServiceComponentRuntime.class);
            if (reference == null) return;
            var runtime = context.getService(reference);
            if (runtime == null) return;
            try {
                Map<String, ComponentState> snapshot = new HashMap<>();
                for (Bundle bundle : context.getBundles()) {
                    if (!WEATHER.equals(bundle.getSymbolicName()) || bundle.getState() == Bundle.UNINSTALLED) continue;
                    for (var description : runtime.getComponentDescriptionDTOs(bundle)) {
                        var configurations = runtime.getComponentConfigurationDTOs(description);
                        if (configurations.isEmpty()) {
                            add(snapshot, bundle, description.name, "definition",
                                runtime.isComponentEnabled(description) ? "No configuration" : "Disabled", "");
                        }
                        for (var configuration : configurations) {
                            String missing = Arrays.stream(configuration.unsatisfiedReferences)
                                .map(referenceDTO -> referenceDTO.name).sorted().collect(Collectors.joining(", "));
                            add(snapshot, bundle, description.name, Long.toString(configuration.id),
                                componentState(configuration.state), missing);
                        }
                    }
                }
                recordComponents(snapshot);
            } finally {
                context.ungetService(reference);
            }
        } catch (RuntimeException failure) {
            System.err.println("WKND OSGi lifecycle sample failed: " + failure.getClass().getSimpleName());
        }
    }

    private static void add(Map<String, ComponentState> result, Bundle bundle, String name,
                            String configuration, String state, String missing) {
        long id = bundle.getBundleId();
        result.put(id + ":" + name + ":" + configuration, new ComponentState(name, id,
            bundle.getVersion().toString(), state, "DS configuration " + configuration
                + (missing.isEmpty() ? "" : " · missing references: " + missing)));
    }

    private synchronized void recordComponents(Map<String, ComponentState> snapshot) {
        snapshot.forEach((key, current) -> {
            ComponentState previous = componentStates.get(key);
            if (!current.equals(previous)) {
                write("DS component", current.name(), current.id(), current.version(),
                    previous == null ? "Not observed" : previous.state(), current.state(), current.detail());
            }
        });
        componentStates.forEach((key, previous) -> {
            if (!snapshot.containsKey(key)) {
                write("DS component", previous.name(), previous.id(), previous.version(),
                    previous.state(), "No longer present", previous.detail());
            }
        });
        componentStates = snapshot;
    }

    private void write(String kind, String name, long id, String version, String before, String after, String event) {
        String line = String.join("\t", Instant.now().toString(), kind, name, Long.toString(id), version,
            before, after, event.replaceAll("[\\t\\r\\n]", " ")) + "\n";
        try {
            Files.createDirectories(history.getParent());
            if (Files.exists(history) && Files.size(history) >= MAX_BYTES) {
                Files.move(history, history.resolveSibling(history.getFileName() + ".1"),
                    StandardCopyOption.REPLACE_EXISTING);
            }
            Files.writeString(history, line, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException failure) {
            System.err.println("WKND OSGi lifecycle write failed: " + failure.getClass().getSimpleName());
        }
    }

    private static String bundleState(int state) {
        return switch (state) {
            case Bundle.INSTALLED -> "Installed";
            case Bundle.RESOLVED -> "Resolved";
            case Bundle.STARTING -> "Starting";
            case Bundle.ACTIVE -> "Active";
            case Bundle.STOPPING -> "Stopping";
            case Bundle.UNINSTALLED -> "Uninstalled";
            default -> "Unknown";
        };
    }

    private static String componentState(int state) {
        return switch (state) {
            case ComponentConfigurationDTO.UNSATISFIED_CONFIGURATION -> "Unsatisfied configuration";
            case ComponentConfigurationDTO.UNSATISFIED_REFERENCE -> "Unsatisfied reference";
            case ComponentConfigurationDTO.SATISFIED -> "Satisfied";
            case ComponentConfigurationDTO.ACTIVE -> "Active";
            case ComponentConfigurationDTO.FAILED_ACTIVATION -> "Failed activation";
            default -> "Unknown";
        };
    }

    private record ComponentState(String name, long id, String version, String state, String detail) {}
}
