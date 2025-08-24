// tagui csv_iterator.tag in/search.csv

searchInputXPath = '//*[@id="cb1-edit"]'
searchBtnXPath = '//button[@type="submit"]'
firstElementResult = '//li[@class="ui-search-layout__item"][1]'

echo Iteration: `iteration`
if iteration equals to 1
    // Create 'out' folder if it does not exist
    run cmd /c "mkdir out"
    
    // Open Site
    https://www.mercadolibre.com.ar/

    // Maximize Chrome window
    click in/maximizeBtn.png

echo Searching for: `search text`

// Clear and type the search text
type `searchInputXPath` as [clear]`search text`

// Click the search button
click `searchBtnXPath`

// Wait for search results to load
wait 5

tagui handle_result.tag
