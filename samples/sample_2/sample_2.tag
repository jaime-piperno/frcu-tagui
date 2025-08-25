// to run this script use "tagui sample_2.tag" or "tagui sample_2.tag -chrome -headless"

// Create 'out' folder if it does not exist
run cmd /c "mkdir out"

// Open coinmarketcap
https://coinmarketcap.com/currencies/bitcoin/

// Wait for the page to load
wait 5

// Get current timestamp in a safe filename format
js timestamp = new Date().toISOString().replace(/[:.]/g,"-")

// Take a screenshot and save it in the 'out' folder with the timestamp as filename
snap //*[@id="section-coin-overview"] to out/`timestamp`.png

// Note: taking screenshots this way does not work in headless mode
snap (740,300)-(1400,660) to out/chart-`timestamp`.png 