// All the functions included in this file are available on runtime, not sure how ¯\_(ツ)_/¯

// Function to get timestamp string, eg 2025-08-25T13-48-51-400Z
function getTimestamp()	{
	return new Date().toISOString().replace(/[:.]/g,"-");
}
	