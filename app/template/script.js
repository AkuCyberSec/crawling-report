function toggle(id, element) {
    let div = document.getElementById(id);
    // div.classList.toggle("hidden");
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
                    values.push(decodeURIComponent(extracted_value_match[group]));
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
        case "0":
            e.options.selectedIndex = hideUrlsWithoutExtractedValues ? 2 : 1;
            break;
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
    document.querySelectorAll(".value").forEach(cell => {
        let row = cell.parentNode;
        let isCellEmpty = cell.innerHTML.trim().length == 0;
        row.style.display = isCellEmpty && hideUrlsWithoutExtractedValues ? "none" : "table-row";
    });
}
toggleTheme();