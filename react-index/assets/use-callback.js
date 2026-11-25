(() => {
    const { createElement: h, memo, useCallback, useLayoutEffect, useRef, useState } = window.React;

    const CounterChild = memo(function CounterChild({ onIncrement }) {
        const figures = useRef({ references: new WeakSet(), distinct: 0, renders: 0 });
        const output = useRef(null);

        useLayoutEffect(() => {
            const stats = figures.current;
            stats.renders += 1;
            if (!stats.references.has(onIncrement)) {
                stats.references.add(onIncrement);
                stats.distinct += 1;
            }
            output.current.textContent = stats.distinct + " distinct references · " + stats.renders + " child renders";
        });

        return h(window.React.Fragment, null,
            h("button", { type: "button", onClick: onIncrement }, "Increment"),
            h("output", { ref: output, className: "wknd-callback__stats", "aria-live": "polite" }));
    });

    function Comparison() {
        const [count, setCount] = useState(0);
        const withoutHook = () => setCount(value => value + 1);
        const withHook = useCallback(() => setCount(value => value + 1), []);

        return h(window.React.Fragment, null,
            h("p", null, "Either button increments the same parent counter. Each memoized child receives only its callback."),
            h("p", { className: "wknd-callback__count" },
                "Parent count: ", h("strong", { "data-parent-count": true }, count)),
            h("div", { className: "wknd-callback__grid" },
                h("section", { "aria-label": "Without useCallback" },
                    h("h2", null, "Without useCallback"),
                    h(CounterChild, { onIncrement: withoutHook })),
                h("section", { "aria-label": "With useCallback" },
                    h("h2", null, "With useCallback"),
                    h(CounterChild, { onIncrement: withHook }))),
            h("p", null, "The counters start at 1 for the initial render. They track callback references delivered to the child, not function allocations."));
    }

    document.querySelectorAll("[data-use-callback-demo]:not([data-use-callback-ready])").forEach(panel => {
        panel.dataset.useCallbackReady = "true";
        window.ReactDOM.createRoot(panel).render(h(Comparison));
    });
})();
