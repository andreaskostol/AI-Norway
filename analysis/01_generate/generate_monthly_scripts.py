"""Generate monthly microdata.no scripts from template."""
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent.parent.parent / 'microdata-scripts' / 'monthly' / '01_yrke4_per_aldersgruppe_TEMPLATE.mdata'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'microdata-scripts' / 'monthly' / 'generated'

# All months to generate (YYYY, MM, status_day)
# ARBLONN uses the 16th of each month
MONTHS = []
for year in range(2020, 2026):
    for month in range(1, 13):
        MONTHS.append((year, month, 16))

def generate():
    OUTPUT_DIR.mkdir(exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    
    for year, month, day in MONTHS:
        date_str = f"{year}-{month:02d}-{day:02d}"
        script = template.replace('DATEPLACEHOLDER', date_str).replace('YEARPLACEHOLDER', str(year))
        
        out_path = OUTPUT_DIR / f"01_yrke4_per_aldersgruppe_{year}_{month:02d}.mdata"
        out_path.write_text(script, encoding='utf-8')
    
    print(f"Generated {len(MONTHS)} scripts in {OUTPUT_DIR}")

if __name__ == '__main__':
    generate()
