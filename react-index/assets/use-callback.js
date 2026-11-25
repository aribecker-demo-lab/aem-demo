(() => {
    const { createElement: h, memo, useCallback, useLayoutEffect, useRef, useState } = window.React;

    function pulseBackground(element, pulse, color) {
        pulse.current?.cancel();
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            pulse.current = element.animate(
                [{ backgroundColor: color }, { backgroundColor: "transparent" }],
                { duration: 450, easing: "ease-out" });
        }
    }

    const CounterChild = memo(function CounterChild({ onIncrement }) {
        const figures = useRef({ references: new WeakSet(), distinct: 0, renders: 0 });
        const references = useRef(null);
        const renders = useRef(null);
        const pulse = useRef(null);

        useLayoutEffect(() => {
            const stats = figures.current;
            stats.renders += 1;
            if (!stats.references.has(onIncrement)) {
                stats.references.add(onIncrement);
                stats.distinct += 1;
            }
            references.current.textContent = stats.distinct + " distinct references";
            const counter = renders.current;
            counter.textContent = stats.renders + " child renders";
            if (stats.renders > 1) {
                counter.classList.add("wknd-callback__renders--increased");
                pulseBackground(counter, pulse, "#ff9ca8");
            }
        });

        return h(window.React.Fragment, null,
            h("button", { type: "button", onClick: onIncrement }, "Increment"),
            h("output", { className: "wknd-callback__stats", "aria-live": "polite" },
                h("span", { ref: references }), " · ",
                h("span", { ref: renders, className: "wknd-callback__renders" })));
    });

    const childExample = `const CounterChild = memo(function CounterChild({ onIncrement }) {
  return <button onClick={onIncrement}>Increment</button>;
});`;

    function highlightJsx(source) {
        const tokens = /(<\/?[A-Za-z][\w]*|\b(?:const|function|return)\b|\b(?:memo|useState|useCallback|setCount)\b|\b\d+\b|=>)/g;
        return source.split("\n").map((line, index) => {
            const changed = line.trimStart().startsWith("const onIncrement =");
            const variant = line.includes("useCallback(") ? "hook" : "direct";
            return h("span", {
                key: index,
                className: changed ? "wknd-callback__diff wknd-callback__diff--" + variant : undefined,
            }, line.split(tokens).map((part, tokenIndex) => {
                if (tokenIndex % 2 === 0) return part;
                let kind = "call";
                if (part.startsWith("<")) kind = "tag";
                else if (/^(const|function|return)$/.test(part)) kind = "keyword";
                else if (/^\d+$/.test(part)) kind = "number";
                else if (part === "=>") kind = "operator";
                else if (part === "useCallback") kind = "hook";
                return h("span", { key: tokenIndex, className: "wknd-callback__token--" + kind }, part);
            }), "\n");
        });
    }

    function CounterPanel({ title, count, onIncrement, example }) {
        const counter = useRef(null);
        const pulse = useRef(null);

        useLayoutEffect(() => {
            if (count > 0) pulseBackground(counter.current, pulse, "#a4e8bb");
        }, [count]);

        return h("section", { "aria-label": title },
            h("h2", null, title),
            h("p", { className: "wknd-callback__count" },
                h("span", {
                    ref: counter,
                    className: count > 0 ? "wknd-callback__count-value wknd-callback__count-value--increased" :
                        "wknd-callback__count-value",
                }, "Count: ", h("strong", { "data-parent-count": true }, count))),
            h(CounterChild, { onIncrement }),
            h("h3", { className: "wknd-callback__code-title" }, "Functional JSX"),
            h("pre", { className: "wknd-callback__code", tabIndex: 0 },
                h("code", null, highlightJsx(example + "\n\n" + childExample))));
    }

    function WithoutCallback() {
        const [count, setCount] = useState(0);
        const onIncrement = () => setCount(value => value + 1);
        return h(CounterPanel, { title: "Without useCallback", count, onIncrement, example: `function WithoutCallback() {
  const [count, setCount] = useState(0);
  const onIncrement = () => setCount(value => value + 1);

  return (
    <>
      <p>Count: {count}</p>
      <CounterChild onIncrement={onIncrement} />
    </>
  );
}` });
    }

    function WithCallback() {
        const [count, setCount] = useState(0);
        const onIncrement = useCallback(() => setCount(value => value + 1), []);
        return h(CounterPanel, { title: "With useCallback", count, onIncrement, example: `function WithCallback() {
  const [count, setCount] = useState(0);
  const onIncrement = useCallback(() => setCount(value => value + 1), []);

  return (
    <>
      <p>Count: {count}</p>
      <CounterChild onIncrement={onIncrement} />
    </>
  );
}` });
    }

    function Comparison() {
        return h(window.React.Fragment, null,
            h("p", null, "Each button increments the counter in its own example. Each memoized child receives only its callback."),
            h("div", { className: "wknd-callback__grid" }, h(WithoutCallback), h(WithCallback)),
            h("p", null, "The reference and render counters include the initial render."));
    }

    document.querySelectorAll("[data-use-callback-demo]:not([data-use-callback-ready])").forEach(panel => {
        panel.dataset.useCallbackReady = "true";
        window.ReactDOM.createRoot(panel).render(h(Comparison));
    });
})();
