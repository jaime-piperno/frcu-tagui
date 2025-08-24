// Create a timestamp for the screenshot filename

// This is an alternative option with inline javascript
js timestamp = new Date().toISOString().replace(/[:.]/g,"-")
snap `firstElementResult` to out/`output folder`/`timestamp`.png

// Function getTimestamp is defined in tagui_local.js
//snap `firstElementResult` to out/`output folder`/`getTimestamp()`.png