#!/bin/bash

# Getting the new papers from arXiv, first argument are the categories to search
OPENSSL_CONF="" tagui AutoPapper.tag IN/xpaths.csv -t

# Generating the prompts for AI processing
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv

# Processing the prompts with AI to get summaries and titles
OPENSSL_CONF="" tagui AIOverview.tag -t

## Cleaning up intermediate files
rm OUT/Prompts.csv OUT/AutoPapper.csv