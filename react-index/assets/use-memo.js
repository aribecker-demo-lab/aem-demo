(() => {
    const { createElement: h, useLayoutEffect, useMemo, useRef, useState } = window.React;
    const items = Array.from({ length: 4000 }, (_, index) => ({
        name: "Item " + (index + 1), category: index % 3 === 0 ? "Books" : "Games",
    }));
    const filterItems = category => items.filter(item => item.category === category);

    function CalculationCount({ results }) {
        const count = useRef(0);
        const output = useRef(null);
        useLayoutEffect(() => {
            count.current += 1;
            output.current.textContent = count.current;
        }, [results]);
        return h("p", null, "Filter results produced: ",
            h("output", { ref: output, "aria-live": "polite", "data-calculation-count": true }));
    }

    function source(memoized) {
        const expression = memoized ? "useMemo(() => filterItems(category), [category])" : "filterItems(category)";
        const code = `const [clicks, setClicks] = useState(0);
const [category, setCategory] = useState("Books");

const results = ${expression};

return (
  <>
    <button onClick={() => setClicks(n => n + 1)}>
      Unrelated clicks: {clicks}
    </button>
    <select value={category}
      onChange={event => setCategory(event.target.value)}>
      <option>Books</option>
      <option>Games</option>
    </select>
    <p>Matches: {results.length}</p>
  </>
);`;
        return code.split("\n").map((line, index) => {
            const changed = line.startsWith("const results =");
            return h("span", { key: index, className: changed
                ? "wknd-callback__diff wknd-callback__diff--" + (memoized ? "hook" : "direct")
                : undefined },
            line.split(/("(?:Books|Games)"|<\/?[A-Za-z]+|\b(?:const|return|useState|useMemo|filterItems)\b|\b\d+\b)/g)
                .map((part, token) => token % 2 === 0 ? part : h("span", {
                    key: token, className: "wknd-callback__token--" + (
                        part === "useMemo" ? "hook" : part.startsWith("<") ? "tag" :
                            /^(const|return)$/.test(part) ? "keyword" : /^\d+$/.test(part) ? "number" : "call"),
                }, part)), "\n");
        });
    }

    function Panel({ memoized, clicks, setClicks, category, setCategory, results }) {
        const title = memoized ? "With useMemo" : "Without useMemo";
        return h("section", { "aria-label": title },
            h("h2", null, title),
            h("button", { type: "button", onClick: () => setClicks(n => n + 1) }, "Increment unrelated count"),
            h("p", null, "Unrelated count: ", h("strong", { "data-clicks": true }, clicks)),
            h("label", null, "Category ", h("select", {
                value: category,
                onChange: event => setCategory(event.target.value),
            }, h("option", null, "Books"), h("option", null, "Games"))),
            h("p", null, "Matches: ", h("strong", { "data-matches": true }, results.length)),
            h(CalculationCount, { results }),
            h("h3", { className: "wknd-callback__code-title" }, "Functional JSX"),
            h("pre", { className: "wknd-callback__code", tabIndex: 0 }, h("code", null, source(memoized))));
    }

    function WithoutMemo() {
        const [clicks, setClicks] = useState(0);
        const [category, setCategory] = useState("Books");
        const results = filterItems(category);
        return h(Panel, { memoized: false, clicks, setClicks, category, setCategory, results });
    }

    function WithMemo() {
        const [clicks, setClicks] = useState(0);
        const [category, setCategory] = useState("Books");
        const results = useMemo(() => filterItems(category), [category]);
        return h(Panel, { memoized: true, clicks, setClicks, category, setCategory, results });
    }

    document.querySelectorAll("[data-use-memo-demo]:not([data-use-memo-ready])").forEach(panel => {
        panel.dataset.useMemoReady = "true";
        window.ReactDOM.createRoot(panel).render(h(window.React.Fragment, null,
            h("p", null, "Both examples filter the same 4,000 items. Increment the unrelated count, then change the category to see when each filter runs."),
            h("div", { className: "wknd-callback__grid" }, h(WithoutMemo), h(WithMemo)),
            h("p", null, "Filter results produced counts new arrays committed to the page, including the initial result.")));
    });
})();
