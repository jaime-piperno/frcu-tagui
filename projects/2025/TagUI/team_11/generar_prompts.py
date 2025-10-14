#!/usr/bin/env python3
"""
generar_prompts.py

Reads a CSV with columns: name, Description, URL, Category
Groups records into batches (default 10) and produces an output CSV with
a single column 'prompt' where each row contains the prompt (one line)
that will be sent to the AI to summarize those papers (max 3 lines per paper,
structure containing Title, Category, Summary and Description).

Usage:
    python generar_prompts.py input.csv output.csv
    python generar_prompts.py input.csv output.csv --batch-size 10

"""

import csv
import argparse
import os
import sys
import html
import re

def clean_text_one_line(text: str) -> str:
    """Remove line breaks and duplicate whitespace, then trim the string."""
    if text is None:
        return ""
    # Convert HTML entities if any
    text = html.unescape(text)
    # Remove LaTeX commands that can cause JavaScript issues
    text = re.sub(r'\\texttt\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    # Remove other common LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    # Replace any newline or return with a space
    text = re.sub(r'[\r\n]+', ' ', text)
    # Replace multiple spaces with one
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def build_prompt_for_batch(batch, max_per_paper_lines=3):
    """
    batch: list of dicts with keys: name, Description, URL, Category
    Returns a single-line string containing the instruction plus the formatted papers.
    """
    n = len(batch)
    instruction = (
        f"Resume los siguientes {n} papers científicos y devuelve la respuesta en formato JSON válido. "
        f"Para cada paper traduce el título al español y crea un objeto con los campos especificados. "
        "Usa emojis apropiados (🤖 para IA, 💻 para software, 🔒 para seguridad, 🧬 para investigación, etc.). "
        "IMPORTANTE: Responde ÚNICAMENTE con el JSON válido, sin texto adicional antes o después. "
        "Estructura JSON requerida: "
        '{"papers": [{"titulo_español": "🔬 [emoji apropiado] Título traducido", "categoria": "[emoji 📂] Categoría del paper", "resumen": "[emoji 📝] Resumen en máximo 3 líneas", "puntos_clave": "[emoji 🎯] Aspectos más importantes", "enlace": "[emoji 🔗] URL del paper"}, ...]} '
        "A continuación vienen los papers:"
    )

    entries = []
    for idx, row in enumerate(batch, start=1):
        title = clean_text_one_line(row.get('name', '') or row.get('title', ''))
        desc = clean_text_one_line(row.get('Description', '') or row.get('abstract', ''))
        url = clean_text_one_line(row.get('URL', ''))
        category = clean_text_one_line(row.get('Category', ''))
        entry = f"{idx}. Título Original: {title} | Categoría: {category} | Descripción: {desc} | URL: {url}"
        entries.append(entry)

    # Merge everything in ONE LINE separating papers with " ||| " for clarity
    joined_entries = " ||| ".join(entries)
    prompt = instruction + " " + joined_entries
    return prompt

def read_input_csv(path):
    """Read the input CSV and return a list of rows as dicts, filtering out duplicate header rows."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Basic validation of columns (non-fatal, only warn if missing)
        expected = {'name', 'Description', 'URL', 'Category'}
        found = set(reader.fieldnames or [])
        missing = expected - found
        if missing:
            # does not break; assumes that user has columns with similar names
            print(f"Advertencia: columnas esperadas ausentes en input CSV: {missing}. Continuando...", file=sys.stderr)
        
        # Get the actual fieldnames to compare against
        fieldnames = reader.fieldnames or []
        
        for r in reader:
            # Skip rows that are duplicate headers (where values match the column names)
            is_header_row = False
            if fieldnames:
                # Check if this row contains the same values as the header
                row_values = [r.get(field, '').strip().lower() for field in fieldnames]
                header_values = [field.strip().lower() for field in fieldnames]
                
                # If row values match header names, it's a duplicate header
                if row_values == header_values:
                    print(f"Skipping duplicate header row: {list(r.values())}", file=sys.stderr)
                    is_header_row = True
            
            if not is_header_row:
                rows.append(r)
    
    return rows

def write_output_csv(prompts, out_path):
    """Write an output CSV with a single 'prompt' column."""
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['prompt'])
        for p in prompts:
            writer.writerow([p])

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst (last chunk may be smaller)."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def main():
    parser = argparse.ArgumentParser(description="Genera prompts en lotes desde un CSV de papers.")
    parser.add_argument('input_csv', help='Ruta al CSV de entrada (con columnas name, Description, URL, Category).')
    parser.add_argument('output_csv', help='Ruta al CSV de salida que contendrá la columna "prompt".')
    parser.add_argument('--batch-size', '-b', type=int, default=10, help='Cantidad de papers por prompt (default 10).')
    parser.add_argument('--max-lines', type=int, default=3, help='Máximo de renglones por resumen pedido a la IA (default 3).')
    args = parser.parse_args()

    if not os.path.isfile(args.input_csv):
        print(f"Error: no se encuentra el archivo de entrada: {args.input_csv}", file=sys.stderr)
        sys.exit(1)

    rows = read_input_csv(args.input_csv)
    if not rows:
        print("No hay registros en el CSV de entrada. Abortando.", file=sys.stderr)
        sys.exit(1)

    prompts = []
    for batch in chunk_list(rows, args.batch_size):
        prompt = build_prompt_for_batch(batch, max_per_paper_lines=args.max_lines)
        prompts.append(prompt)

    write_output_csv(prompts, args.output_csv)
    print(f"Generados {len(prompts)} prompts en {args.output_csv}")

if __name__ == '__main__':
    main()
