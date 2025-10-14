//Read and parse CSV file using TagUI native command
load OUT/Prompts.csv to csv_content

js begin
  // Parse CSV content
  var lines = csv_content.split('\n');
  var prompts = [];
  
  // Skip header line and extract prompts  
  for (var i = 1; i < lines.length; i++) {
    var line = lines[i].trim();
    if (line) {
      // Remove outer quotes if present
      var prompt = line.replace(/^"/, '').replace(/"$/, '');
      // Replace double quotes with single quotes for CSV escaping
      prompt = prompt.replace(/""/g, '"');
      if (prompt) {
        prompts.push(prompt);
      }
    }
  }
  
  total_prompts = prompts.length;
  prompt_array = prompts;
js finish

echo ============================================================================
echo Encontrados `total_prompts` prompts para procesar
echo ============================================================================

//Loop through each prompt
for prompt_index from 0 to total_prompts-1
{
  js begin
    current_prompt = prompt_array[prompt_index];
    prompt_number = prompt_index + 1;
  js finish
  
  echo ============================================================================
  echo Procesando prompt `prompt_number` de `total_prompts`
  echo ============================================================================
  
  //Enter website URL
  https://chat.deepseek.com/
  
  //write in textarea
  type //*[@id="root"]/div/div/div[2]/div[3]/div/div/div[2]/div[2]/div/div/div[1]/textarea as `current_prompt`

  //click send button
  click //*[@id="root"]/div/div/div[2]/div[3]/div/div/div[2]/div[2]/div/div/div[2]/div/div[2]

  //wait for response to be generated (adjust time as needed)
  wait 120

  //extract the complete response from the specific location
  read //*[@id="root"]/div/div/div[2]/div[3]/div/div[2]/div/div[2]/div[1]/div[2] to deepseek_response

  //clean up the response and process JSON for WhatsApp
  js begin
    // DEBUG: Log raw response info
    debug_response_length = deepseek_response ? deepseek_response.length : 0;
    debug_response_preview = deepseek_response ? deepseek_response.substring(0, 200) + '...' : 'No response';
    
    // Remove HTML tags and convert to plain text
    var cleanResponse = deepseek_response.replace(/<[^>]*>/g, '');
    
    // Replace HTML entities
    cleanResponse = cleanResponse.replace(/&nbsp;/g, ' ');
    cleanResponse = cleanResponse.replace(/&amp;/g, '&');
    cleanResponse = cleanResponse.replace(/&lt;/g, '<');
    cleanResponse = cleanResponse.replace(/&gt;/g, '>');
    cleanResponse = cleanResponse.replace(/&quot;/g, '"');
    
    // Clean up extra whitespace and normalize spaces
    cleanResponse = cleanResponse.replace(/\s+/g, ' ').trim();
    
    // DEBUG: Log cleaned response info
    debug_clean_length = cleanResponse ? cleanResponse.length : 0;
    debug_clean_preview = cleanResponse ? cleanResponse.substring(0, 300) + '...' : 'No clean response';
    
    // Try to extract JSON from the response
    var papers = [];
    debug_json_processing = 'Starting JSON processing...';
    try {
      // First, remove the problematic prefix
      var cleanedResponse = cleanResponse.replace(/^jsonCopyDownload\s*/, '');
      debug_json_processing = 'Removed jsonCopyDownload prefix';
      
      // Look for JSON pattern in the response - more robust regex
      var jsonMatch = cleanedResponse.match(/\{[\s\S]*"papers"[\s\S]*\}/);
      if (jsonMatch) {
        debug_json_processing = 'JSON match found, length: ' + jsonMatch[0].length;
        var jsonText = jsonMatch[0];
        
        // DEBUG: Log potentially problematic characters before cleaning
        debug_json_preview = jsonText.substring(0, 200) + '...';
        
        // Simple cleanup - just remove trailing commas
        jsonText = jsonText.replace(/,\s*\]/, ']'); // Fix trailing commas in arrays
        jsonText = jsonText.replace(/,\s*\}/, '}'); // Fix trailing commas in objects
        
        debug_json_processing = 'Attempting JSON.parse after basic cleanup...';
        var jsonData = JSON.parse(jsonText);
        debug_json_processing = 'JSON.parse successful! Papers found: ' + (jsonData.papers ? jsonData.papers.length : 0);
        
        // Process each paper from the JSON
        if (jsonData.papers && Array.isArray(jsonData.papers)) {
          debug_papers_count = jsonData.papers.length;
          for (var i = 0; i < jsonData.papers.length; i++) {
            var paper = jsonData.papers[i];
            
            // Format the paper for WhatsApp
            var formattedPaper = '';
            if (paper.titulo_español) {
              formattedPaper += paper.titulo_español + '\n\n';
            }
            if (paper.categoria) {
              formattedPaper += paper.categoria + '\n\n';
            }
            if (paper.resumen) {
              formattedPaper += paper.resumen + '\n\n';
            }
            if (paper.puntos_clave) {
              formattedPaper += paper.puntos_clave + '\n\n';
            }
            if (paper.enlace) {
              formattedPaper += paper.enlace;
            }
            
            // Add to papers array
            papers.push(formattedPaper.trim());
          }
        } else {
          debug_json_processing = 'No papers array found in parsed JSON';
          debug_papers_count = 0;
        }
      } else {
        debug_json_processing = 'No JSON pattern match found in response';
        debug_papers_count = 0;
      }
    } catch (e) {
      // If JSON parsing fails, create an error message
      debug_json_processing = 'JSON parsing failed: ' + e.message;
      debug_papers_count = 0;
      papers = ['Error al procesar la respuesta JSON: ' + e.message + '\n\nRespuesta original:\n' + cleanResponse];
    }
    
    // Fallback: if no papers found, add the original response
    if (papers.length === 0) {
      papers = ['No se encontraron papers en formato JSON.\n\nRespuesta original:\n' + cleanResponse];
    }
    
    // Store papers array and total count for the for loop
    paper_messages = papers;
    total_papers = papers.length;
    
    // For debugging - show first paper as whatsapp_content
    whatsapp_content = papers.length > 0 ? papers[0] : 'No papers found';
  js finish

  echo ============================================================================
  echo DEBUG - Response length: `debug_response_length` chars
  echo DEBUG - Response preview: `debug_response_preview`
  echo ============================================================================
  echo DEBUG - Clean length: `debug_clean_length` chars  
  echo DEBUG - Clean preview: `debug_clean_preview`
  echo ============================================================================
  echo DEBUG - JSON processing: `debug_json_processing`
  echo DEBUG - Papers count: `debug_papers_count`
  echo ============================================================================
  echo `whatsapp_content`
  echo ============================================================================
  echo Total papers found: `total_papers`

  // Open WhatsApp Web
  https://web.whatsapp.com/

  wait 10

  // Click in the group chat name to open it
  click Papper News 9129324123

  // Send each paper to WhatsApp
  for paper_index from 0 to total_papers-1
  {
    js begin
      current_paper = paper_messages[paper_index];
      debug_paper_index = paper_index + 1;
      debug_paper_length = current_paper ? current_paper.length : 0;
      debug_paper_preview = current_paper ? current_paper.substring(0, 100) + '...' : 'No paper content';
    js finish
    
    echo ============================================================================
    echo Enviando paper `debug_paper_index` de `total_papers` - Length: `debug_paper_length` chars
    echo Preview: `debug_paper_preview`
    echo ============================================================================
    
    // Click the message input box, type the current paper, and send
    click //*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3]
    type //*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3] as `current_paper`

    //Press send button (With the xpath in diferent pc, sometimes the xpath changes)
    dom document.querySelector("span[data-icon='wds-ic-send-filled']").click()
  }

  // Final wait and completion message
  wait 5

  echo ============================================================================
  echo Todos los papers del prompt `prompt_number` han sido enviados exitosamente!
  echo Total de papers procesados: `total_papers`
  echo ============================================================================

  // This is the end of loop for each prompt
}

echo ============================================================================
echo PROCESAMIENTO COMPLETO - Todos los `total_prompts` prompts han sido procesados!
echo ============================================================================