(() => {
    // createElement (h) creates React elements from a type, props and children.
    // memo wraps a component so React can skip re-rendering it when its props are unchanged.
    // useCallback reuses a function reference while its dependencies remain unchanged.
    // useEffect runs after a commit for work such as fetching. Cleanup can cancel that work.
    // useLayoutEffect runs after DOM updates and before paint, so it can update the visible counters.
    // useRef keeps a mutable value or DOM reference between renders. Changing it does not schedule a render.
    // useState stores reactive state. Its setter queues an update for a later render.
    const { createElement: h, memo, useCallback, useEffect, useLayoutEffect, useRef, useState } = window.React;

    const sourceUrl = document.currentScript.src;

    function pulseBackground(element, pulse, color) {
        pulse.current?.cancel();
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            pulse.current = element.animate(
                [{ backgroundColor: color }, { backgroundColor: "transparent" }],
                { duration: 450, easing: "ease-out" });
        }
    }

    // memo skips re-rendering this child when its callback prop keeps the same reference.
    const CounterChild = memo(function CounterChild({ onIncrement }) {
        // useRef retains the metrics across renders. Updating them does not trigger another render.
        const figures = useRef({ references: new WeakSet(), distinct: 0, renders: 0 });
        // useRef holds the DOM node that displays how many callback references the child received.
        const references = useRef(null);
        // useRef holds the DOM node that displays the number of committed child renders.
        const renders = useRef(null);
        // useRef retains the current animation so a new increment can restart the pulse.
        const pulse = useRef(null);

        // useLayoutEffect updates the metrics after each child commit, before the browser paints.
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

    function highlightSource(source) {
        const tokens = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\n]*|<\/?[A-Za-z][\w]*|\b(?:const|function|return|if|else|new|let|null|true|false|throw)\b|\b(?:memo|useState|useCallback|useEffect|useLayoutEffect|useRef|setCount|createRoot)\b|\b\d+\b|=>)/g;
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
                else if (part.startsWith("//")) kind = "comment";
                else if (part.startsWith('"') || part.startsWith("'")) kind = "string";
                else if (/^(const|function|return|if|else|new|let|null|true|false|throw)$/.test(part)) kind = "keyword";
                else if (/^\d+$/.test(part)) kind = "number";
                else if (part === "=>") kind = "operator";
                else if (part === "useCallback") kind = "hook";
                return h("span", { key: tokenIndex, className: "wknd-callback__token--" + kind }, part);
            }), "\n");
        });
    }

    function CounterPanel({ title, count, onIncrement, example }) {
        // useRef gives the effect access to the count label for the green pulse.
        const counter = useRef(null);
        // useRef retains the current animation so a new increment can restart the pulse.
        const pulse = useRef(null);

        // useLayoutEffect starts the green pulse before paint when this panel’s count changes.
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
                h("code", null, highlightSource(example + "\n\n" + childExample))));
    }

    function WithoutCallback() {
        // useState stores this panel’s independent count and schedules a render when it changes.
        const [count, setCount] = useState(0);
        // Left version without useCallback. A fresh function reference reaches the memoized child on every render.
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
        // useState stores this panel’s independent count and schedules a render when it changes.
        const [count, setCount] = useState(0);
        // Right version with useCallback. React reuses the reference. The updater reads the latest count, so [] is enough.
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

    function FullSource() {
        // useState stores the JavaScript fetched for the complete source viewer.
        const [source, setSource] = useState("");
        // useState records a fetch failure so the viewer can display an error message.
        const [error, setError] = useState(false);

        // useEffect fetches the deployed source after mount and cancels the request on unmount.
        useEffect(() => {
            const request = new AbortController();
            fetch(sourceUrl, { signal: request.signal })
                .then(response => {
                    if (!response.ok) throw new Error("Source unavailable");
                    return response.text();
                })
                .then(setSource)
                .catch(() => {
                    if (!request.signal.aborted) setError(true);
                });
            return () => request.abort();
        }, []);

        return h("section", { className: "wknd-callback__full-source" },
            h("h2", null, "Complete JavaScript"),
            h("p", null, "The full component source, including render tracking, visual feedback and initialization."),
            source
                ? h("pre", { className: "wknd-callback__code", tabIndex: 0 },
                    h("code", null, highlightSource(source.trimEnd())))
                : h("p", { role: "status" }, error ? "The source could not be loaded." : "Loading source…"));
    }

    function Comparison() {
        return h(window.React.Fragment, null,
            h("p", null, "Each button increments the counter in its own example. Each memoized child receives only its callback."),
            h("div", { className: "wknd-callback__grid" }, h(WithoutCallback), h(WithCallback)),
            h("p", null, "The reference and render counters include the initial render."),
            h(FullSource));
    }

    document.querySelectorAll("[data-use-callback-demo]:not([data-use-callback-ready])").forEach(panel => {
        panel.dataset.useCallbackReady = "true";
        // createRoot creates a React root in the AEM container. render mounts the comparison there.
        window.ReactDOM.createRoot(panel).render(h(Comparison));
    });
})();
