function getTimestamp()	{
	return new Date().toISOString().replace(/[:.]/g,"-");
}
	