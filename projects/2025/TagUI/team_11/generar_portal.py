#!/usr/bin/env python3
"""
generar_portal.py

Generates a news portal HTML from a CSV containing processed papers.
Handles duplicated headers and produces a modern dark-themed site (YouTube Music style).

Usage:
    python generar_portal.py input.csv output.html
    python generar_portal.py OUT/ProcessedPapers.csv portal_noticias.html

"""

import csv
import argparse
import os
import sys
import html
import re
from datetime import datetime
from collections import defaultdict

def clean_text(text):
    """Clean and sanitize text for inclusion in HTML."""
    if not text:
        return ""
    
    text = html.escape(text)
    # Preserve emojis and basic formatting
    return text.strip()

def clean_url(url):
    """Clean and validate URLs to ensure they are absolute and well-formed."""
    if not url:
        return ""
    
    url = url.strip()
    
    # Remove problematic prefixes and malformed URL patterns (e.g. xn--)
    url = re.sub(r'^https?://xn--[^/]*', '', url)
    url = re.sub(r'^[^h]*https?://', 'https://', url)
    
    # Normalize duplicated protocol occurrences like "https://https://..."
    url = re.sub(r'https?://.*?https?://', 'https://', url)
    
    # Remove control characters and spaces
    url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
    url = url.replace(' ', '')
    
    # Extract a valid arXiv URL if multiple URLs are concatenated
    arxiv_match = re.search(r'arxiv\.org/[^\s"<>]*', url)
    if arxiv_match:
        clean_part = arxiv_match.group(0)
        if not clean_part.startswith('http'):
            url = 'https://' + clean_part
        else:
            url = clean_part
    
    # If it already has a valid protocol, normalize repeated slashes and return
    if url.startswith(('http://', 'https://')):
        url = re.sub(r'([^:])//+', r'\1/', url)
        return url

    # If it starts with //, add https:
    if url.startswith('//'):
        return 'https:' + url
    
    # If it's an arXiv relative path, build a full URL
    if url.startswith('/'):
        return 'https://arxiv.org' + url

    # If it contains arxiv.org but doesn't have a protocol
    if 'arxiv.org' in url and not url.startswith('http'):
        return 'https://' + url

    # For other cases, assume it needs https://
    if '.' in url and not url.startswith('http'):
        return 'https://' + url
    
    return url

def extract_emoji_from_title(title):
    """Extract emoji from the start of a title if present, otherwise return a default."""
    if not title:
        return "", title

    # Search for emoji at the start of the title
    emoji_pattern = r'^([🔬🤖💻🔒🧬🏥📊🔍🎯🌊📐💼🧠🤝💡🔧🚇📶🔬🆔🧮🎨🎵🎮🎪🎭🎨🎯🎲🎪🎭🏆🏅🏏🏀⚽🏈🎾🏸🏓🏑🏒🥅⛳🏹🎣🥊🥋🏔️⛰️🏕️🏜️🏝️🏟️🏛️🏗️🏘️🏚️🏠🏡🏢🏣🏤🏥🏦🏧🏨🏩🏪🏫🏬🏭🏮🏯🏰🗼🗽⛪🕌🕍🕎🔬🔭🔬🧪🧬⚗️🔬🧮🧲⚡🔋🔌💻⌨️🖥️🖨️🖱️💿💾💽📀🧮💾🔌⚡🔋🔬🧪🧬⚗️🔬🧮🧲⚡🔋])\s*(.*)$'
    
    match = re.match(emoji_pattern, title)
    if match:
        return match.group(1), match.group(2).strip()
    
    return "📄", title  # Default emoji

def process_csv_robust(filepath):
    """Process the CSV robustly, handling duplicated header rows and noisy data."""
    papers = []
    headers_found = set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        # Find the first row that appears to be a valid header row
        headers = None
        for row in reader:
            if len(row) >= 4 and any(col.lower() in ['titulo', 'title', 'resumen', 'summary'] for col in row):
                headers = row
                break
        
        if not headers:
            print("No se encontraron headers válidos en el CSV", file=sys.stderr)
            return []
        
        print(f"Headers encontrados: {headers}")
        
    # Map column indices by common header names
        title_idx = next((i for i, h in enumerate(headers) if h.lower() in ['titulo', 'title']), 0)
        category_idx = next((i for i, h in enumerate(headers) if h.lower() in ['categoria', 'category']), 1)
        summary_idx = next((i for i, h in enumerate(headers) if h.lower() in ['resumen', 'summary']), 2)
        points_idx = next((i for i, h in enumerate(headers) if h.lower() in ['puntos_clave', 'points', 'key_points']), 3)
        link_idx = next((i for i, h in enumerate(headers) if h.lower() in ['enlace', 'link', 'url']), 4)
        date_idx = next((i for i, h in enumerate(headers) if h.lower() in ['fecha', 'date', 'fecha_procesado']), 5)
        
        # Iterate over data rows and extract fields
        for row in reader:
            # Saltar filas que son headers duplicados
            if len(row) >= 4 and row[title_idx].lower() in ['titulo', 'title']:
                continue
            
            # Saltar filas vacías o muy cortas
            if len(row) < 4 or not any(row):
                continue
            
            # Extract fields from the row
            try:
                title = row[title_idx] if title_idx < len(row) else ""
                category = row[category_idx] if category_idx < len(row) else ""
                summary = row[summary_idx] if summary_idx < len(row) else ""
                points = row[points_idx] if points_idx < len(row) else ""
                link = row[link_idx] if link_idx < len(row) else ""
                date = row[date_idx] if date_idx < len(row) else ""
                
                # Validate that at least the title is not empty
                if not title or len(title.strip()) < 5:
                    continue
                
                # Extract emoji from title (keep for visual appeal but don't use for categorization)
                emoji, clean_title = extract_emoji_from_title(title)
                
                # Use the category directly from the CSV, clean emoji prefix if present
                if category.startswith("📂 "):
                    category = category[2:].strip()  # Remove emoji and space prefix
                elif not category.strip():
                    category = "Otros"  # Default category if empty
                
                # Debug: print cleaned URLs for problematic inputs
                original_link = link.strip()
                cleaned_link = clean_url(original_link)
                if original_link != cleaned_link:
                    print(f"URL limpiada: '{original_link}' → '{cleaned_link}'")
                
                paper = {
                    'title': clean_text(clean_title),
                    'emoji': emoji,
                    'summary': clean_text(summary),
                    'points': clean_text(points),
                    'link': cleaned_link,
                    'date': date.strip(),
                    'category': category.strip()
                }
                
                papers.append(paper)
                
            except IndexError as e:
                print(f"Error processing row: {row[:3]}... - {e}", file=sys.stderr)
                continue
    
    print(f"Procesados {len(papers)} papers válidos")
    return papers

def generate_html(papers, output_file):
    """Generate the portal HTML from the processed papers list."""
    
    # Group papers by category
    categories = defaultdict(list)
    for paper in papers:
        categories[paper['category']].append(paper)
    
    # Sort categories by number of papers (descending)
    sorted_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    
    current_date = datetime.now().strftime("%d de %B de %Y")
    total_papers = len(papers)
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Papper news</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
            color: #ffffff;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            padding: 2rem 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            border-bottom: 2px solid #333;
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 3s ease-in-out infinite;
            margin-bottom: 0.5rem;
        }}
        
        @keyframes gradientShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        
        .subtitle {{
            font-size: 1.1rem;
            color: #b3b3b3;
            font-weight: 300;
        }}
        
        .stats {{
            margin: 1.5rem 0;
            display: flex;
            gap: 2rem;
            justify-content: center;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            background: rgba(255,255,255,0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .category {{
            margin-bottom: 3rem;
        }}
        
        .category-header {{
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #333;
        }}
        
        .category-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
            margin-left: 0.5rem;
        }}
        
        .category-count {{
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-left: auto;
        }}
        
        .papers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }}
        
        .paper-card {{
            background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .paper-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
            background-size: 400% 400%;
            animation: gradientShift 3s ease-in-out infinite;
        }}
        
        .paper-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            border-color: rgba(255,255,255,0.2);
        }}
        
        .paper-emoji {{
            font-size: 2rem;
            margin-bottom: 1rem;
            display: block;
        }}
        
        .paper-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 1rem;
            line-height: 1.4;
        }}
        
        .paper-summary {{
            color: #b3b3b3;
            margin-bottom: 1rem;
            font-size: 0.95rem;
            line-height: 1.5;
        }}
        
        .paper-points {{
            color: #d4d4d4;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            background: rgba(0,0,0,0.3);
            padding: 1rem;
            border-radius: 8px;
            border-left: 3px solid #4ecdc4;
        }}
        
        .paper-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: auto;
        }}
        
        .paper-link {{
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            text-decoration: none;
            padding: 0.6rem 1.2rem;
            border-radius: 25px;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .paper-link:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(255,107,107,0.3);
        }}
        
        .paper-date {{
            color: #888;
            font-size: 0.8rem;
        }}
        
        .footer {{
            background: #1e1e1e;
            padding: 2rem;
            text-align: center;
            margin-top: 3rem;
            border-top: 2px solid #333;
        }}
        
        .footer p {{
            color: #b3b3b3;
        }}
        
        /* Filter Section Layout */
        .filter-section {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
        }}
        
        /* Filter Dropdown Styles */
        .dropdown {{
            position: relative;
            display: inline-block;
        }}
        
        .dropdown-toggle {{
            background: #2a2a2a;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 8px 16px;
            font-size: 0.9rem;
            font-weight: 500;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .dropdown-toggle:hover {{
            background: #3a3a3a;
            border-color: #505050;
        }}
        
        .dropdown-toggle::after {{
            content: "▼";
            margin-left: 8px;
            font-size: 0.7rem;
            transition: transform 0.2s ease;
        }}
        
        .dropdown.open .dropdown-toggle::after {{
            transform: rotate(180deg);
        }}
        
        .dropdown-menu {{
            position: absolute;
            top: 100%;
            left: 0;
            min-width: 200px;
            background: #2a2a2a;
            border: 1px solid #404040;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-8px);
            transition: all 0.2s ease;
            max-height: 250px;
            overflow-y: auto;
        }}
        
        .dropdown.open .dropdown-menu {{
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }}
        
        .dropdown-item {{
            display: block;
            padding: 8px 12px;
            color: #ffffff;
            text-decoration: none;
            transition: background-color 0.2s ease;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        
        .dropdown-item:hover {{
            background: #3a3a3a;
        }}
        
        .dropdown-item.active {{
            background: #3a3a3a;
            color: #ffffff;
        }}
        
        .papers-count {{
            margin: 0.5rem 0;
            color: #b3b3b3;
            font-size: 0.85rem;
            text-align: center;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .filter-section {{
                text-align: center;
                padding: 1rem;
            }}
            
            .stats {{
                gap: 1rem;
                flex-wrap: wrap;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .papers-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .scroll-top {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 1.2rem;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            opacity: 0;
            visibility: hidden;
        }}
        
        .scroll-top.visible {{
            opacity: 1;
            visibility: visible;
        }}
        
        .scroll-top:hover {{
            transform: scale(1.1);
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <h1>🔬 ArXiv Daily Portal</h1>
            <p class="subtitle">Portal de Noticias Científicas - Últimas Investigaciones</p>
            <div class="stats">
                <div class="stat-item">📊 {total_papers} Papers</div>
                <div class="stat-item">📅 {current_date}</div>
                <div class="stat-item">🏷️ {len(sorted_categories)} Categorías</div>
            </div>

        </div>
    </header>

    <section class="filter-section">
        <div class="dropdown" id="categoryDropdown">
            <button class="dropdown-toggle">
                Filtrar por categoría
            </button>
            <div class="dropdown-menu">
                <button class="dropdown-item" onclick="filterByCategory('all')">Mostrar todas</button>"""

    # Add category options to dropdown (simplified)
    for category_name, category_papers in sorted_categories:
        html_content += f"""
                <button class="dropdown-item" onclick="filterByCategory('{category_name}')">{category_name}</button>"""

    html_content += f"""
            </div>
        </div>
    </section>

    <main class="container">
"""

    # Render content for each category
    for category_name, category_papers in sorted_categories:
        # Get the most common emoji in the category
        category_emoji = get_category_emoji(category_papers)
        
        html_content += f"""
        <section class="category" data-category="{category_name}">
            <div class="category-header">
                <span style="font-size: 1.5rem;">{category_emoji}</span>
                <h2 class="category-title">{category_name}</h2>
                <span class="category-count">{len(category_papers)}</span>
            </div>
            
            <div class="papers-grid">
"""
        
        for paper in category_papers:
            # Clean and format key points for display
            points_formatted = paper['points'].replace('🎯', '').strip()
            if not points_formatted.startswith('•'):
                # Convert commas to bullets if not already present
                points_formatted = '• ' + points_formatted.replace(',', '\n• ').replace(';', '\n• ')
            
            # Ensure the link is valid for the anchor
            paper_link = clean_url(paper['link'])
            if not paper_link or not ('http' in paper_link and '.' in paper_link):
                paper_link = "#"  # Enlace placeholder si no es válido
            
            html_content += f"""
                <article class="paper-card">
                    <span class="paper-emoji">{paper['emoji']}</span>
                    <h3 class="paper-title">{paper['title']}</h3>
                    <p class="paper-summary">{paper['summary']}</p>
                    <div class="paper-points">{points_formatted}</div>
                    <div class="paper-footer">
                        <a href="{paper_link}" class="paper-link" target="_blank" rel="noopener">
                            📖 Leer Paper
                        </a>
                        <span class="paper-date">{paper['date']}</span>
                    </div>
                </article>
"""
        
        html_content += """
            </div>
        </section>
"""

    html_content += f"""
    </main>

    <footer class="footer">
        <p>🔬 Portal generado automáticamente desde arXiv • {current_date}</p>
        <p>Procesado por TagUI + DeepSeek AI</p>
    </footer>

    <button class="scroll-top" onclick="scrollToTop()">↑</button>

    <script>
        // Mostrar botón de scroll to top
        window.addEventListener('scroll', function() {{
            const scrollTop = document.querySelector('.scroll-top');
            if (window.pageYOffset > 300) {{
                scrollTop.classList.add('visible');
            }} else {{
                scrollTop.classList.remove('visible');
            }}
        }});

        // Función para scroll to top
        function scrollToTop() {{
            window.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }}

        // Animación de entrada para las tarjetas
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach((entry) => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }});

        document.querySelectorAll('.paper-card').forEach((card) => {{
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        }});

        // Dropdown functionality
        const dropdown = document.getElementById('categoryDropdown');
        const dropdownToggle = dropdown.querySelector('.dropdown-toggle');
        const categories = document.querySelectorAll('.category');
        const papersCount = document.getElementById('papersCount');
        
        dropdownToggle.addEventListener('click', function() {{
            dropdown.classList.toggle('open');
        }});

        function filterByCategory(category) {{
            const dropdownItems = document.querySelectorAll('.dropdown-item');
            dropdownItems.forEach(item => item.classList.remove('active'));
            event.target.classList.add('active');
            
            if (category === 'all') {{
                categories.forEach(cat => cat.style.display = 'block');
                dropdownToggle.textContent = 'Filtrar por categoría';
                papersCount.textContent = `Mostrando {total_papers} papers en {len(sorted_categories)} categorías`;
            }} else {{
                let visiblePapers = 0;
                categories.forEach(cat => {{
                    if (cat.dataset.category === category) {{
                        cat.style.display = 'block';
                        visiblePapers += cat.querySelectorAll('.paper-card').length;
                    }} else {{
                        cat.style.display = 'none';
                    }}
                }});
                dropdownToggle.textContent = category;
                papersCount.textContent = `Mostrando ${{visiblePapers}} papers en 1 categoría`;
            }}
            dropdown.classList.remove('open');
        }}

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {{
            if (!dropdown.contains(e.target)) {{
                dropdown.classList.remove('open');
            }}
        }});
    </script>
</body>
</html>
"""

    # Write the final HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Portal generado exitosamente: {output_file}")
    print(f"📊 {total_papers} papers procesados en {len(sorted_categories)} categorías")

def get_category_emoji(category_papers):
    """Get the most common emoji for a category based on its papers."""
    emoji_count = {}
    
    for paper in category_papers:
        title = paper.get('title', '')
        emoji, _ = extract_emoji_from_title(title)
        emoji_count[emoji] = emoji_count.get(emoji, 0) + 1
    
    if emoji_count:
        return max(emoji_count, key=emoji_count.get)
    
    # Default emojis por categoría
    category_emojis = {
        'Computer Vision': '👁️',
        'Natural Language Processing': '🗣️',
        'Machine Learning': '🤖',
        'Artificial Intelligence': '🧠',
        'Data Science': '📊',
        'Robotics': '🤖',
        'Deep Learning': '🧠',
        'Statistics': '📈',
        'Mathematics': '🔢',
    }
    
    # Try to match category name
    for category in category_papers:
        cat_name = category.get('category', '')
        if cat_name in category_emojis:
            return category_emojis[cat_name]
    
    return "📄"  # Default

def main():
    parser = argparse.ArgumentParser(description="Generate a news portal HTML from a processed CSV")
    parser.add_argument('input_csv', help='CSV file with processed papers')
    parser.add_argument('output_html', help='Output HTML file for the portal')
    
    args = parser.parse_args()
    
    if not os.path.isfile(args.input_csv):
        print(f"Error: No se encuentra el archivo CSV: {args.input_csv}", file=sys.stderr)
        sys.exit(1)
    
    try:
        papers = process_csv_robust(args.input_csv)
        
        if not papers:
            print("No se encontraron papers válidos en el CSV", file=sys.stderr)
            sys.exit(1)
        
        generate_html(papers, args.output_html)
        
    except Exception as e:
        print(f"Error al procesar el archivo: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()