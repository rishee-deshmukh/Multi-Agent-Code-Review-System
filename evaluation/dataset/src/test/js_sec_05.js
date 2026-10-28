function showSearchTerm() {
    const params = new URLSearchParams(window.location.search);
    const term = params.get("q") || "";
    document.getElementById("results-title").innerHTML = "Results for " + term; // @label xss high
    document.title = "Search: " + term.length + " characters";
}

document.addEventListener("DOMContentLoaded", showSearchTerm);
