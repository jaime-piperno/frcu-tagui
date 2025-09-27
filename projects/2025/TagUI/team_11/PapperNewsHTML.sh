#!/bin/bash

# Getting the new papers from arXiv, first argument are the categories to search 
OPENSSL_CONF="" tagui AutoPapper.tag IN/xpaths.csv -t

# Generating the prompts for AI processing
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv

# Processing the prompts with AI to get summaries and titles
OPENSSL_CONF="" tagui AICSV.tag -t

# Creating a news portal HTML file with the processed papers
python generar_portal.py OUT/ProcessedPapers.csv OUT/portal_noticias.html

# Cleaning up intermediate files
rm OUT/Prompts.csv OUT/AutoPapper.csv OUT/ProcessedPapers.csv