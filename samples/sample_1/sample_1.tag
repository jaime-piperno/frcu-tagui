// To run this script use "tagui sample_1.tag"
// Executable cmd file was generated using "tagui sample_1.tag -d"

// Open google images
https://images.google.com/

// Wait for the page to load
wait 2

// Type in the search box
type //*[@name="q"] as borzoi

// Click the search button
click //*[@name="btnK"]

// Wait for the page to load
wait 10
