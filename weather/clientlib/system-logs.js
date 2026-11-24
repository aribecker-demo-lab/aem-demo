(function () {
    var logTokens = new RegExp([
        /(?<time>\b(?:\d{4}-\d{2}-\d{2}[T ]|\d{2}\.\d{2}\.\d{4} |\d{2}\/[A-Za-z]{3}\/\d{4}:)?\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z| ?[+-]\d{2}:?\d{2})?\b)/,
        /(?<url>https?:\/\/[^\s<>"']+|(?<=\b(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS) )\/[^\s"']*|(?<=\[)\/(?:content|apps|libs|etc\.clientlibs)\/[^\s\]]*)/,
        /(?<level>\b(?:ERROR|FATAL|WARN(?:ING)?|INFO|DEBUG|TRACE)\b)(?=[\]*\s·:])/,
        /(?<component>\bWKND_WEATHER\b|\b(?:org|com|dev|net|io)\.(?:[\w$-]+\.)+[\w$-]+\b|\b[A-Za-z0-9_-]+\/components\/[\w/-]+)/,
        /(?<context>\b(?:trace|status|durationMs|remainingMs|provider|role|temperatureC|humidityPct|windKmh)=[^\s]+)/,
    ].map(function (pattern) { return pattern.source; }).join("|"), "g");

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

    function initialize() {
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
