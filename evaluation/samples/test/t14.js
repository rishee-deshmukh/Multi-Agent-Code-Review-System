function showSearchTerm() {
    const params = new URLSearchParams(window.location.search);
    const term = params.get("q") || "";
    document.getElementById("results-title").innerHTML = "Results for " + term;
    document.title = "Search: " + term.length + " characters";
}

document.addEventListener("DOMContentLoaded", showSearchTerm);
