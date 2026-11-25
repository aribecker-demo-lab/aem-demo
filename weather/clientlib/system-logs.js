(function () {
    var logTokens = new RegExp([
        /(?<time>\b(?:\d{4}-\d{2}-\d{2}[T ]|\d{2}\.\d{2}\.\d{4} |\d{2}\/[A-Za-z]{3}\/\d{4}:)?\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z| ?[+-]\d{2}:?\d{2})?\b)/,
        /(?<url>https?:\/\/[^\s<>"']+|(?<=\b(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS) )\/[^\s"']*|(?<=\[)\/(?:content|apps|libs|etc\.clientlibs)\/[^\s\]]*)/,
        /(?<level>\b(?:ERROR|FATAL|WARN(?:ING)?|INFO|DEBUG|TRACE)\b)(?=[\]*\s·:])/,
        /(?<component>\bWKND_WEATHER\b|\b(?:org|com|dev|net|io)\.(?:[\w$-]+\.)+[\w$-]+\b|\b[A-Za-z0-9_-]+\/components\/[\w/-]+)/,
        /(?<stage>\b(?:[A-Z]+_(?:REQUEST_)?(?:START|STARTED|END|FINISHED|ACTIVATED|DEACTIVATED|SUCCESS|FAILED|RESULT|ERROR)|FALLBACK|CACHE_(?:HIT|MISS|UPDATED)|JSON_PARSED|startup|shutdown|activation|deactivation|activated|deactivated|starting|started|finished|completed)\b)/i,
        /(?<context>\b(?:trace|status|durationMs|remainingMs|provider|role|temperatureC|humidityPct|windKmh)=[^\s]+)/,
    ].map(function (pattern) { return pattern.source; }).join("|"), "gi");

    function colorLog(target, text, emptyMessage) {
        target.textContent = "";
        if (!text) {
            target.textContent = emptyMessage;
            return;
        }
        var fragment = document.createDocumentFragment();
        var end = 0;
        for (var match of text.matchAll(logTokens)) {
            fragment.append(text.slice(end, match.index));
            var token = document.createElement("span");
            var kind = Object.keys(match.groups).find(function (key) { return match.groups[key]; });
            token.className = "wknd-log-" + (kind === "level" ? "level-" + match[0].toLowerCase() : kind);
            token.textContent = match[0];
            fragment.append(token);
            end = match.index + match[0].length;
        }
        fragment.append(text.slice(end));
        target.append(fragment);
    }

    var sourceTokens = /(?<comment>\/\*[\s\S]*?\*\/|\/\/[^\n]*|<!--[\s\S]*?-->)|(?<string>"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`)|(?<tag><\/?[\w:.-]+)|(?<annotation>@[\w.]+)|(?<keyword>\b(?:package|import|public|private|protected|class|record|interface|static|final|void|return|new|try|catch|finally|throw|throws|if|else|switch|case|default|var|const|let|async|await|function|boolean|int|long|double|true|false|null)\b)|(?<number>\b\d+(?:\.\d+)?\b)/g;

    function sourceCode(text) {
        var pre = document.createElement("pre");
        var code = document.createElement("code");
        var end = 0;
        for (var match of text.matchAll(sourceTokens)) {
            var token = document.createElement("span");
            var kind = Object.keys(match.groups).find(function (key) { return match.groups[key]; });
            token.className = "wknd-source-" + kind;
            token.textContent = match[0];
            code.append(text.slice(end, match.index), token);
            end = match.index + match[0].length;
        }
        code.append(text.slice(end));
        pre.tabIndex = 0;
        pre.append(code);
        return pre;
    }

    function xmlTree(element, depth) {
        var node = document.createElement("details");
        var summary = document.createElement("summary");
        var name = document.createElement("code");
        name.className = "wknd-source-tag";
        name.textContent = "<" + element.tagName + ">";
        summary.append(name);
        node.append(summary);
        node.open = depth === 0;
        if (element.attributes.length) {
            var values = document.createElement("dl");
            Array.from(element.attributes).forEach(function (attribute) {
                var key = document.createElement("dt");
                var value = document.createElement("dd");
                key.className = "wknd-source-annotation";
                key.textContent = attribute.name;
                value.className = "wknd-source-string";
                value.textContent = attribute.value;
                values.append(key, value);
            });
            node.append(values);
        }
        Array.from(element.childNodes).forEach(function (child) {
            if (child.nodeType === 1) {
                node.append(xmlTree(child, depth + 1));
            } else if ((child.nodeType === 3 || child.nodeType === 4) && child.textContent.trim()) {
                node.append(sourceCode(child.textContent.trim()));
            }
        });
        return node;
    }

    function weatherSource(file) {
        var details = document.createElement("details");
        var title = document.createElement("summary");
        title.textContent = file.path;
        details.append(title);
        details.addEventListener("toggle", function show() {
            if (!details.open) return;
            details.removeEventListener("toggle", show);
            if (file.path.endsWith(".xml")) {
                var doc = new DOMParser().parseFromString(file.source, "application/xml");
                if (!doc.querySelector("parsererror")) {
                    details.append(xmlTree(doc.documentElement, 0));
                    var raw = document.createElement("details");
                    var label = document.createElement("summary");
                    label.textContent = "Raw XML";
                    raw.append(label, sourceCode(file.source));
                    details.append(raw);
                    return;
                }
            }
            details.append(sourceCode(file.source));
        });
        return details;
    }

    function loadOnOpen(details, container, url, read, render, message, refresh) {
        var loading = false;
        var loaded = false;
        details.addEventListener("toggle", function () {
            if (!details.open || loading || (loaded && !refresh)) return;
            loading = true;
            container.textContent = "Loading…";
            fetch(url, { cache: "no-store" })
                .then(function (response) {
                    if (response.status === 401 || response.status === 403) {
                        throw new Error("Sign in as the AEM demo administrator to view this section.");
                    }
                    if (!response.ok) throw new Error(message);
                    return read(response);
                })
                .then(function (content) {
                    render(content);
                    loaded = true;
                })
                .catch(function (error) { container.textContent = error.message; })
                .finally(function () { loading = false; });
        });
    }

    function initializeWeatherDocs() {
        document.querySelectorAll("[data-weather-docs]").forEach(function (panel) {
            if (panel.dataset.weatherDocsInitialized) return;
            panel.dataset.weatherDocsInitialized = "true";
            var url = panel.dataset.weatherDocs;
            var log = panel.querySelector("[data-weather-log]");
            var pre = log.querySelector("pre");
            loadOnOpen(log, pre, url + "?view=log", function (response) { return response.text(); },
                function (text) { colorLog(pre, text, "Empty log."); }, "Weather log is unavailable.", true);
            var sources = panel.querySelector("[data-weather-sources]");
            var files = sources.querySelector("[data-weather-files]");
            loadOnOpen(sources, files, url, function (response) { return response.json(); },
                function (snapshot) {
                    files.textContent = "";
                    if (!snapshot.hasDialog) {
                        var note = document.createElement("p");
                        note.textContent = "Weather has no Author dialog.";
                        files.append(note);
                    }
                    snapshot.files.forEach(function (file) { files.append(weatherSource(file)); });
                }, "Weather source files are unavailable.", false);
        });
    }

    function initialize() {
        initializeWeatherDocs();
        document.querySelectorAll("[data-system-logs-url]").forEach(function (panel) {
            if (panel.dataset.systemLogsInitialized) return;
            panel.dataset.systemLogsInitialized = "true";
            var message = panel.querySelector("[data-system-logs-message]");
            var results = panel.querySelector("[data-system-logs-results]");
            var refresh = panel.querySelector("[data-system-logs-refresh]");

            function renderLogFiles(files) {
                var list = panel.querySelector("[data-system-logs-files]");
                list.textContent = "";
                if (!files.length) list.textContent = "No log files available.";
                files.forEach(function (path) {
                    var details = document.createElement("details");
                    var title = document.createElement("summary");
                    var content = document.createElement("pre");
                    var loading = false;
                    title.textContent = path;
                    content.tabIndex = 0;
                    details.append(title, content);
                    list.appendChild(details);
                    details.addEventListener("toggle", function () {
                        if (!details.open || loading) return;
                        loading = true;
                        content.textContent = "Loading log…";
                        var url = new URL(panel.dataset.systemLogsUrl, document.baseURI);
                        url.searchParams.set("log", path);
                        fetch(url, { cache: "no-store" })
                            .then(function (response) {
                                if (!response.ok) throw new Error("Could not load this log.");
                                return response.text();
                            })
                            .then(function (text) { colorLog(content, text, "Empty log."); })
                            .catch(function (error) { content.textContent = error.message; })
                            .finally(function () { loading = false; });
                    });
                });
            }

            function renderSettings(groups) {
                var settings = panel.querySelector("[data-system-settings]");
                if (!settings) return;
                settings.textContent = "";
                groups.forEach(function (group) {
                    var details = document.createElement("details");
                    var title = document.createElement("summary");
                    var values = document.createElement("dl");
                    title.textContent = group.title;
                    details.open = group.title === "AEM and Sling";
                    group.values.forEach(function (value) {
                        var label = document.createElement("dt");
                        var entry = document.createElement("dd");
                        label.textContent = value.name;
                        entry.textContent = value.value;
                        values.append(label, entry);
                    });
                    details.append(title, values);
                    settings.appendChild(details);
                });
            }

            function renderLifecycle(events) {
                var container = panel.querySelector("[data-system-lifecycle]");
                if (!container) return;
                container.textContent = "";
                if (!events.length) {
                    container.textContent = "No lifecycle events have been captured.";
                    return;
                }
                var table = document.createElement("table");
                var heading = table.createTHead().insertRow();
                ["Timestamp (UTC)", "Type", "Bundle or component", "Bundle ID / version", "Previous state",
                    "New state", "Event or detail"].forEach(function (label) {
                    var cell = document.createElement("th");
                    cell.scope = "col";
                    cell.textContent = label;
                    heading.append(cell);
                });
                var componentColors = new Map([
                    ["dev.wknd.demo.weather.WeatherService", "weather-service"],
                    ["dev.wknd.demo.weather.WeatherServlet", "weather-servlet"],
                    ["dev.wknd.demo.weather.WeatherDiagnosticsServlet", "weather-diagnostics"],
                    ["dev.wknd.demo.weather.SystemLogsService", "logs-service"],
                    ["dev.wknd.demo.weather.SystemLogsServlet", "logs-servlet"],
                ]);
                var body = table.createTBody();
                events.forEach(function (event) {
                    var row = body.insertRow();
                    row.dataset.lifecycleEntity = event.kind === "Bundle" ? "bundle" :
                        (componentColors.get(event.name) || "component");
                    [event.timestamp, event.kind, event.name, event.bundleId + " / " + event.version,
                        event.from, event.to, event.event].forEach(function (value, index) {
                        var cell = row.insertCell();
                        cell.textContent = value;
                        if (index === 0) cell.className = "wknd-log-time";
                        if (index === 2) cell.className = "wknd-log-component";
                        if (index === 5) cell.className = "wknd-log-stage";
                    });
                });
                container.append(table);
            }

            function render(data) {
                panel.querySelector("[data-system-logs-commit]").textContent =
                    data.commit ? "Deployed commit: " + data.commit : "";
                var renderLink = panel.querySelector("[data-system-logs-render]");
                if (/^srv-[a-z0-9]+$/.test(data.renderService || "")) {
                    renderLink.href = "https://dashboard.render.com/web/" + data.renderService;
                    renderLink.hidden = false;
                } else {
                    renderLink.hidden = true;
                }
                colorLog(panel.querySelector("[data-system-logs-build]"),
                    data.build.join("\n"), "No build events available.");
                colorLog(panel.querySelector("[data-system-logs-runtime]"),
                    data.runtime.join("\n"), "No matching recent events.");
                colorLog(panel.querySelector("[data-system-logs-packages]"),
                    data.packageLogs.join("\n"), "AEM error.log is empty or unavailable.");
                var list = panel.querySelector("[data-system-logs-status]");
                list.textContent = "";
                data.status.forEach(function (status) {
                    var item = document.createElement("li");
                    item.textContent = status.name + " · " + status.state;
                    list.appendChild(item);
                });
                renderLogFiles(data.logFiles || []);
                renderSettings(data.systemSettings || []);
                renderLifecycle(data.lifecycleHistory || []);
                results.hidden = false;
                message.textContent = "";
            }

            function load() {
                refresh.disabled = true;
                message.textContent = "Loading diagnostics…";
                fetch(panel.dataset.systemLogsUrl, { cache: "no-store" })
                    .then(function (response) {
                        if (response.status === 401 || response.status === 403) {
                            throw new Error("Sign in as the AEM demo administrator to view diagnostics.");
                        }
                        if (!response.ok) throw new Error("Diagnostics are temporarily unavailable.");
                        return response.json();
                    })
                    .then(render)
                    .catch(function (error) { message.textContent = error.message; })
                    .then(function () { refresh.disabled = false; });
            }
            refresh.addEventListener("click", load);
            load();
        });
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
