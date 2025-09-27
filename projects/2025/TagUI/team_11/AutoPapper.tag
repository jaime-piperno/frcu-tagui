//Create or overwrite CSV file with headers
write `csv_row(["name", "Description", "URL", "Category"])` to OUT/AutoPapper.csv

https://arxiv.org/

// click on category from xpaths.csv
click `xpath`

//Save category in a variable
read h1 to category

//Select new submissions and change to list view
click new

//Save in a variable the number of new submissions
read //*[@id="articles"]/h3 to submissions

echo `submissions`

// Extract number from string using JavaScript 
js begin
  var s = '' + submissions;
  var matches = s.match(/\d+/);
  if (matches) {
    number_value = parseInt(matches[0], 10);
  } else {
    number_value = 0;
  }
js finish

echo Number found is `number_value`

// This if is because otherwise it takes too long to do this in each for, and since we need to check once which div it is in, it works correctly. The other way takes much longer.
if exist('/html/body/div[3]/main/div/div/div/dl[1]/dt[1]/a[2]')
    
  option = 1

else if exist('/html/body/div[2]/main/div/div/div/dl[1]/dt[1]/a[2]')

  option = 2

// Create a loop to process each submission
for i from 1 to number_value

  // Get submission details
  if option equals to 1
    
    click /html/body/div[3]/main/div/div/div/dl[1]/dt[`i`]/a[2]

  else if option equals to 2

    click /html/body/div[2]/main/div/div/div/dl[1]/dt[`i`]/a[2]

  read //*[@id="abs"]/h1/text() to name

  read #abs blockquote to description

  fetch //a[@class="abs-button download-pdf"]/@href to direction

  url = "https://arxiv.org" + direction

  echo `name` - `description` - `url` - `category`

  // Navigate back to the list of submissions
  dom window.history.back()

  // Write submission details to CSV
  write `csv_row([name, description, url, category])` to OUT/AutoPapper.csv