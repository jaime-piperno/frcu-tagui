// To execute this script, you must enter the following command in the terminal:
// cd .\DespegarTagUI\
// tagui despegarbarato.tag in/search.csv

// XPaths of the elements to be used:
// Xpath of the origin button
buttonOrigin='//*[@id="home-tab-container"]/form/div[2]/div/div[1]/div[1]/div[2]/div[1]'
// xpath of the origin input field
searchInputOriginXPath = '//*[@id="home-tab-container"]/form/div[2]/div/div[1]/div[1]/div[2]/div[2]/div/input'
// xpath of the first result in the origin dropdown
selectInputOptionOrigin = '//*[@id="autocomplete-open"]/span/span/ul/li[1]'
// xpath of the destiny input field
searchInputDestinyXPath = '//*[@id="home-tab-container"]/form/div[2]/div/div[1]/div[3]/div[2]/div[2]/div/input'
// xpath of the first result in the destiny dropdown
selectInputOptionDestiny = '//*[@id="autocomplete-open"]/span/span/ul/li[1]/div[2]'
// xpath of the destiny button
buttonDestiny='//*[@id="home-tab-container"]/form/div[2]/div/div[1]/div[3]/div[2]/div[1]'
// xpath of the search button
searchBtnXPath ='//*[@id="home-tab-container"]/form/div[2]/div/div[4]/button'
// xpath of the one-way button
onlyWayButton='//*[@id="tt2"]'
// xpath of the date selector
selectDatesXPath = '//*[@id="home-tab-container"]/form/div[3]/div[2]/div'

https://www.turismocity.com.ar/
wait 5
echo Iteration: `iteration`
if iteration equals to 1
    keyboard [f11]
    // run cmd /c "mkdir out"
    // Open Site

echo Searching for: `origin`
// Click the one-way button
click `onlyWayButton`
// Click the date selector
click `selectDatesXPath`


// Click the origin field
click `buttonOrigin`
// Type the origin
type `searchInputOriginXPath` as [clear]`origin`
// Wait for the origin dropdown to load
wait 1
// Select the first result from the dropdown
click `selectInputOptionOrigin`


// Click the destiny field
click `buttonDestiny`
// Type the destiny
type `searchInputDestinyXPath` as [clear]`destiny`
// Wait for the destiny dropdown to load
wait 1
// Select the first result from the dropdown
click `selectInputOptionDestiny`

// Click the search button
click `searchBtnXPath`

// Wait for the results page to load
wait 3
// Here the results are processed
if iteration equals to 1
    tagui vuelos.tag

// This is done for iteration 2 as it is an international flight, so there is an extra div
if iteration equals to 2
    tagui vuelosinter.tag

// Here the price table is sent to Discord
if iteration equals to 1
    tagui envioCordoba-Salta.tag
if iteration equals to 2
    tagui envioEzeiza-Madrid.tag