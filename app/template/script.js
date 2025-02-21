function displaySelectedHostname(select)
{
    applyEmptyURLsRule();
}

function changePage(select)
{
    window.location.href = select.value;
}

function applyExtractor(select, tableId) {
    // Values:
    // 0: clear values column
    // 1: display all extracted values separated by semicolon
    // any: display selected extractor

    let clearValuesColumn = select.value == 0;

    if (clearValuesColumn)
    {
        document.querySelectorAll(`#${tableId} .value`).forEach((cell, index) => {cell.textContent = '';});
        return;
    }
    
    let selectedValue = select.value;
    let display_all_values = selectedValue == 1

    document.querySelectorAll(`#${tableId} .value`).forEach((cell, index) => {

        let values = []
        for (let i = 2; i < select.options.length; i++)
        {
            let option = select.options[i];
            if (option.value == selectedValue || display_all_values)
            {
                let expression = option.dataset.expression;
                let group = parseInt(option.dataset.group);
                let regex = new RegExp(expression,"ig");
                let url = cell.parentNode.children[0].textContent;
                let match = url.match(regex);
                if (match == null)
                    continue;

                regex = new RegExp(expression, "i");
                for (let j = 0; j < match.length; j++)
                {
                    let extracted_value = match[j];
                    let extracted_value_match = extracted_value.match(regex);
                    if (extracted_value_match == null)
                        continue;
                    let value_to_display = extracted_value_match[group];
                    try
                    {
                        // If the URI Component is malformed, it throws an exception
                        values.push(decodeURIComponent(value_to_display));
                    }
                    catch(error)
                    {
                        values.push(value_to_display);
                        console.log("Error: " + error);
                        console.log("URL: " + url);
                        console.log("Extracted value: " + extracted_value)
                        console.log("Value to push: " + value_to_display);
                    }
                    
                }
                
            }
        }
        cell.textContent = values.join(";");
    });

    applyEmptyURLsRule();
}

function saveUrls(select) {
    
    let saveAll = false;
    let saveWithValues = false;
    let doNotSaveUrl = false;

    switch(select.value)
    {
        case 0:
            doNotSaveUrl = true;
            break;
        case "all_no_values":
            saveAll = true;
            saveWithValues = false;
            break;
        case "selected_no_values":
            saveAll = false;
            saveWithValues = false;
            break;
        case "all_with_values":
            saveAll = true;
            saveWithValues = true;
            break;
        case "selected_with_values":
            saveAll = false;
            saveWithValues = true;
            break;
    }

    if (doNotSaveUrl) return;

    let urls = [];
    let checkboxes = document.getElementsByClassName("select-rule");

    if (saveWithValues)
        urls.push("URL;Extracted values")

    for (let i = 0; i < checkboxes.length; i++)
    {
        let checkbox = checkboxes[i];
        let ruleName = checkbox.dataset.ruleName;
        if (saveAll || checkbox.checked){
            document.querySelectorAll(`#${ruleName} .url-cell`).forEach(cell => {
                let row = cell.parentNode;
            
                if (row.style.display != "none")
                {
                    if (saveWithValues)
                    {
                        let value = row.getElementsByClassName("value")[0].innerHTML;
                        value = value.replace('"','""');
                        urls.push(`${cell.title};"${value}"`);
                    }
                    else
                        urls.push(cell.title);
                }
            });
        }
    }
    
    if (urls.length == 0)
    {
        alert("There are no URLs to export");
        select.value = 0;
        return;
    }

    let extension = saveWithValues ? "csv" : "txt";
    let mimetype = saveWithValues ? "text/csv" : "text/plain";
    let blob = new Blob([urls.join("\n")], { type: mimetype });
    let a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `extracted_urls.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    select.value = 0; 
}

function toggleTheme() {
    document.body.classList.toggle("dark-mode");
    document.getElementById("themeButton").textContent = document.body.classList.contains("dark-mode") ? "🌙" : "☀️" ;
}

let hideUrlsWithoutExtractedValues = false;
function toggleEmptyURLs(e) {

    switch(e.value)
    {
        case "display":
            hideUrlsWithoutExtractedValues = false;
            applyEmptyURLsRule();
            break;
        case "hide":
            hideUrlsWithoutExtractedValues = true;
            applyEmptyURLsRule();
            break;
    }

}

function applyEmptyURLsRule()
{
    let selectedHostname = document.getElementById("display-selected-hostname").value;

    document.querySelectorAll(".value").forEach(cell => {
        let row = cell.parentNode;
        let isCellEmpty = cell.innerHTML.trim().length == 0;
        let url = row.getElementsByClassName("url-cell")[0].title;
        let parsedUrl = URL.parse(url)?.host;
        let urlCanBeShown = selectedHostname == "*" || parsedUrl == selectedHostname;

        if (!urlCanBeShown)
        {
            row.classList.add("hidden");
            return;
        }

        if (hideUrlsWithoutExtractedValues)
        {
            if (isCellEmpty)
                row.classList.add("hidden");
            else
                row.classList.remove("hidden");
        }
        else
            row.classList.remove("hidden");
    });
}

window.onload = function(){
    toggleTheme();
    let hideOrDisplayUrlsValue = document.getElementById("hide-or-display-urls").value;
    switch(hideOrDisplayUrlsValue)
    {
        // hideUrlsWithoutExtractedValues is set to "False" by default
        // but users can use config.yaml to hide rows automatically.
        // In that case, we need to know which option is selected 
        case "hide":
            hideUrlsWithoutExtractedValues = true;
            break;
        case "display":
            hideUrlsWithoutExtractedValues = false;
            break;
    }
}