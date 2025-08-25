// Create a timestamp for the screenshot filename

// Function getTimestamp is defined in tagui_local.js
// Variable firstElementResult is defined in case_3.tag
// Variable output folder is a column header in in/search.csv
// Take a screenshot of the element and store it in the output folder
snap `firstElementResult` to out/`output folder`/`getTimestamp()`.png

// This is an alternative option with inline javascript
// js timestamp = new Date().toISOString().replace(/[:.]/g,"-")
// snap `firstElementResult` to out/`output folder`/`timestamp`.png