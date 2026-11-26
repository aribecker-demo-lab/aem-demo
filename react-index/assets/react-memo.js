(() => {
    const { createElement: h, memo, useLayoutEffect, useRef, useState } = window.React;

    function Child({ value, optimized }) {
        const renders = useRef(0);
        const output = useRef(null);
        const indicator = useRef(null);
        const pulse = useRef(null);
        useLayoutEffect(() => {
            renders.current += 1;
            output.current.textContent = renders.current;
            if (renders.current > 1) {
                const badge = indicator.current;
                badge.classList.add(optimized ? "wknd-callback__count-value--increased" :
                    "wknd-callback__renders--increased");
                pulse.current?.cancel();
                if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                    pulse.current = badge.animate([
                        { backgroundColor: optimized ? "#a4e8bb" : "#ff9ca8" },
                        { backgroundColor: "transparent" },
                    ], { duration: 450, easing: "ease-out" });
                }
            }
        });
        return h("div", null,
            h("p", null, "Child prop (value): ", h("strong", null, value)),
            h("p", null, h("span", { ref: indicator, className: "wknd-callback__renders" },
                "Child renders: ", h("output", { ref: output, "aria-live": "polite" }))));
    }

    const MemoChild = memo(Child);

    function Example({ optimized }) {
        const [parentUpdates, setParentUpdates] = useState(0);
        const [value, setValue] = useState(0);
        const title = optimized ? "With React.memo" : "Without React.memo";
        const ChildComponent = optimized ? MemoChild : Child;

        return h("section", { "aria-label": title },
            h("h2", null, title),
            h("p", null, "Parent-only updates: ", h("strong", { "data-parent-updates": true }, parentUpdates)),
            h("button", { type: "button", onClick: () => setParentUpdates(n => n + 1) }, "Update parent only"),
            " ",
            h("button", { type: "button", onClick: () => setValue(n => n + 1) }, "Increment child prop"),
            h(ChildComponent, { value, optimized }),
            h("h3", { className: "wknd-callback__code-title" }, "JSX comparison"),
            h("pre", { className: "wknd-callback__code", tabIndex: 0 },
                h("code", null,
                    h("span", { className: "wknd-callback__diff wknd-callback__diff--" + (optimized ? "hook" : "direct") },
                        h("span", { className: "wknd-callback__token--keyword" }, "const"),
                        " ChildComponent = ",
                        optimized ? h("span", { className: "wknd-callback__token--hook" }, "memo") : "Child",
                        optimized ? "(Child);" : ";"),
                    "\n\n// Inside the parent render\n",
                    h("span", { className: "wknd-callback__token--keyword" }, "return"),
                    " ",
                    h("span", { className: "wknd-callback__token--tag" }, "<ChildComponent"),
                    " value={value} />;")));
    }

    document.querySelectorAll("[data-react-memo-demo]:not([data-react-memo-ready])").forEach(panel => {
        panel.dataset.reactMemoReady = "true";
        window.ReactDOM.createRoot(panel).render(h(window.React.Fragment, null,
            h("h1", null, "React.memo Demo"),
            h("p", null, "Update a parent without changing its child’s props, then increment the value passed to the child. Each example has its own state."),
            h("div", { className: "wknd-callback__grid" }, h(Example, { optimized: false }), h(Example, { optimized: true })),
            h("p", null, "Child renders includes the initial render.")));
    });
})();
