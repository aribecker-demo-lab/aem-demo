(() => {
    const { createElement: h, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } = window.React;

    function createTrace() {
        let rows = [];
        const origin = performance.now();
        const listeners = new Set();
        return {
            getSnapshot: () => rows,
            subscribe(listener) {
                listeners.add(listener);
                return () => listeners.delete(listener);
            },
            add(stage, detail) {
                rows = [...rows, {
                    id: (rows.at(-1)?.id ?? 0) + 1,
                    time: (performance.now() - origin).toFixed(1),
                    stage, detail,
                }].slice(-100);
                listeners.forEach(listener => listener());
            },
        };
    }

    function useRenderTrace(trace, value, label, node) {
        const previous = useRef(null);
        useLayoutEffect(() => {
            const current = node.current;
            trace.add("Render result", 'Committed snapshot: state value=' + value + ', prop label="' + label + '".');
            trace.add("React element", 'Committed description: <output>' + value + '</output>.');
            trace.add("Commit / DOM",
                'DOM text is "' + current.textContent + '". ' +
                (previous.current === current ? "The same DOM node was reused." : "A DOM node was mounted."));
            previous.current = current;
            trace.add("useLayoutEffect", "Ran after the DOM update and before the browser paints this commit.");
        }, [trace, value, label, node]);

        useEffect(() => {
            trace.add("useEffect", "Ran after commit. This callback alone does not confirm a paint.");
            let nextFrame;
            const frame = requestAnimationFrame(() => {
                trace.add("Animation frame", "The browser called requestAnimationFrame before painting.");
                nextFrame = requestAnimationFrame(() => {
                    trace.add("Next frame", "A paint opportunity passed. This is not a paint measurement.");
                });
            });
            return () => {
                cancelAnimationFrame(frame);
                cancelAnimationFrame(nextFrame);
            };
        }, [trace, value]);
    }

    function Counter({ trace, label }) {
        const [value, setValue] = useState(0);
        const node = useRef(null);
        useRenderTrace(trace, value, label, node);
        function increment() {
            trace.add("Click", "The event handler sees state value=" + value + ".");
            trace.add("Update requested", "Calling setValue(previous => previous + 1).");
            setValue(previous => previous + 1);
        }
        return h("section", { "aria-label": "Counter" },
            h("p", null, label + ": ", h("output", { ref: node, "data-trace-value": true }, value)),
            h("button", { type: "button", onClick: increment }, "Increment"));
    }

    function TraceLog({ trace }) {
        const rows = useSyncExternalStore(trace.subscribe, trace.getSnapshot);
        return h("section", { "aria-label": "Event log" },
            h("h2", null, "Event log"),
            h("p", null, "Render results are shown when committed. Fiber reconciliation and discarded renders are not exposed by these hooks."),
            h("div", { className: "wknd-trace__log", tabIndex: 0 },
                h("table", null,
                    h("thead", null, h("tr", null, ["#", "Time (ms)", "Stage", "Observation"]
                        .map(label => h("th", { key: label, scope: "col" }, label)))),
                    h("tbody", { "aria-live": "polite" }, rows.map(row =>
                        h("tr", { key: row.id },
                            h("td", null, row.id), h("td", null, row.time),
                            h("th", { scope: "row" }, row.stage), h("td", null, row.detail)))))));
    }

    document.querySelectorAll("[data-render-trace-demo]:not([data-render-trace-ready])").forEach(panel => {
        panel.dataset.renderTraceReady = "true";
        const trace = createTrace();
        window.ReactDOM.createRoot(panel).render(h(window.React.Fragment, null,
            h("h1", null, "React Render Trace"),
            h("p", null, "Follow a state update from a button click to the DOM and browser frame callbacks."),
            h(Counter, { trace, label: "Value" }), h(TraceLog, { trace })));
    });
})();
