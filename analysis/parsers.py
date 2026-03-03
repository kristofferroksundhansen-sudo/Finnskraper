import re

def parse_price(price_str):
    if not isinstance(price_str, str):
        return None
    num = re.sub(r'[^\d]', '', price_str)
    return int(num) if num else None

def parse_mileage(mileage_str):
    if not isinstance(mileage_str, str):
        return None
    num = re.sub(r'[^\d]', '', mileage_str)
    return int(num) if num else None

def parse_year(year_str):
    if not isinstance(year_str, str):
        return None
    num = re.sub(r'[^\d]', '', year_str)
    return int(num) if num else None

def parse_battery(battery_str):
    if not isinstance(battery_str, str):
        return None
    num = re.sub(r'[^\d]', '', battery_str)
    return int(num) if num else None

def parse_effect(effect_str):
    if not isinstance(effect_str, str):
        return None
    num = re.sub(r'[^\d]', '', effect_str)
    return int(num) if num else None

def parse_owners(owners_str):
    """Parse 'Eiere' field, e.g. '1' or '2'."""
    if not isinstance(owners_str, str):
        return None
    num = re.sub(r'[^\d]', '', owners_str)
    return int(num) if num else None

def parse_condition_flag(value_str):
    """Returns 1 if a known defect is reported (Ja), 0 if not (Nei), None if unknown."""
    if not isinstance(value_str, str):
        return None
    v = value_str.strip().lower()
    if v in ('ja', 'yes'):
        return 1
    elif v in ('nei', 'no'):
        return 0
    return None

def parse_range_km(range_str):
    """Parse rekkevidde (WLTP), f.eks. '270 km' -> 270."""
    if not isinstance(range_str, str):
        return None
    num = re.sub(r'[^\d]', '', range_str.split('km')[0] if 'km' in range_str.lower() else range_str)
    return int(num) if num and int(num) > 0 else None

def parse_warranty(garanti_str):
    """Returnerer 1 hvis bilen har garanti, 0 hvis ikke."""
    if not isinstance(garanti_str, str):
        return None
    v = garanti_str.strip().lower()
    if v in ('nei', 'no', 'ingen', '-', ''):
        return 0
    return 1

TRIM_PATTERNS = [
    # Ordnet fra høyest/mest sjelden til lavest. Vi sjekker for disse.
    (r'\be\+\b', 'e+'),
    (r'\bTekna\b', 'Tekna'),
    (r'\bN-Connecta\b', 'N-Connecta'),
    (r'\bAcenta\b', 'Acenta'),
    (r'\bVisia\b', 'Visia'),
]

def parse_trim_level(title, subtitle=None, description=None):
    """Ekstraher utstyrsnivå via hierarkisk regex search."""
    
    def find_trim(text):
        if not isinstance(text, str):
            return None
        for pattern, trim in TRIM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return trim
        return None

    # 1. Prøv tittel (mest presist hvis selger har tatt seg bryet)
    trim = find_trim(title)
    if trim: return trim
    
    # 2. Prøv underoverskrift (vanligste sted for trim i Finn for tiden)
    trim = find_trim(subtitle)
    if trim: return trim
    
    # 3. Prøv brødtekst / beskrivelse
    trim = find_trim(description)
    if trim: return trim

    return 'Ukjent'

REGION_MAP = {
    # Oslo-regionen
    'oslo': 'Oslo/Akershus', 'akershus': 'Oslo/Akershus', 'bærum': 'Oslo/Akershus',
    'asker': 'Oslo/Akershus', 'lillestrøm': 'Oslo/Akershus', 'lørenskog': 'Oslo/Akershus',
    'drammen': 'Oslo/Akershus', 'jessheim': 'Oslo/Akershus', 'ski': 'Oslo/Akershus',
    'rygge': 'Oslo/Akershus', 'tomter': 'Oslo/Akershus',
    # Vestfold/Telemark
    'sandefjord': 'Vestfold/Telemark', 'tønsberg': 'Vestfold/Telemark',
    'larvik': 'Vestfold/Telemark', 'sem': 'Vestfold/Telemark',
    'stokke': 'Vestfold/Telemark', 'holmestrand': 'Vestfold/Telemark',
    'revetal': 'Vestfold/Telemark', 'tolvsrød': 'Vestfold/Telemark',
    'melsomvik': 'Vestfold/Telemark', 'porsgrunn': 'Vestfold/Telemark',
    'skien': 'Vestfold/Telemark', 'notodden': 'Vestfold/Telemark',
    'stathelle': 'Vestfold/Telemark', 'ulefoss': 'Vestfold/Telemark',
    'bø i telemark': 'Vestfold/Telemark', 'kviteseid': 'Vestfold/Telemark',
    # Østfold
    'fredrikstad': 'Østfold', 'sarpsborg': 'Østfold', 'moss': 'Østfold',
    'halden': 'Østfold', 'askim': 'Østfold', 'mysen': 'Østfold',
    'rakkestad': 'Østfold', 'råde': 'Østfold', 'rolvsøy': 'Østfold',
    'gressvik': 'Østfold', 'kråkerøy': 'Østfold', 'greåker': 'Østfold',
    'borgenhaugen': 'Østfold', 'slitu': 'Østfold',
    'våler i østfold': 'Østfold', 'gamle fredrikstad': 'Østfold',
    # Bergen/Vestland
    'bergen': 'Vestland', 'askøy': 'Vestland', 'sotra': 'Vestland',
    'blomsterdalen': 'Vestland', 'fana': 'Vestland', 'nesttun': 'Vestland',
    'fyllingsdalen': 'Vestland', 'godvik': 'Vestland', 'bønes': 'Vestland',
    'rådal': 'Vestland', 'kokstad': 'Vestland', 'nyborg': 'Vestland',
    'os': 'Vestland', 'straume': 'Vestland', 'kleppestø': 'Vestland',
    'knarrevik': 'Vestland', 'brattholmen': 'Vestland',
    'hauglandshella': 'Vestland', 'hetlevik': 'Vestland',
    'hordvik': 'Vestland', 'lonevåg': 'Vestland', 'isdalstø': 'Vestland',
    'indre arna': 'Vestland', 'espeland': 'Vestland', 'ulset': 'Vestland',
    'øvre ervik': 'Vestland', 'førde': 'Vestland', 'vik i sogn': 'Vestland',
    # Rogaland
    'stavanger': 'Rogaland', 'sandnes': 'Rogaland', 'sola': 'Rogaland',
    'haugesund': 'Rogaland', 'bryne': 'Rogaland', 'kleppe': 'Rogaland',
    'randaberg': 'Rogaland', 'tananger': 'Rogaland', 'hafrsfjord': 'Rogaland',
    'hundvåg': 'Rogaland', 'figgjo': 'Rogaland', 'nærbø': 'Rogaland',
    'egersund': 'Rogaland', 'kopervik': 'Rogaland',
    'skudeneshavn': 'Rogaland', 'åkrehamn': 'Rogaland',
    'avaldsnes': 'Rogaland', 'karmsund': 'Rogaland', 'veavågen': 'Rogaland',
    'lye': 'Rogaland', 'ålgård': 'Rogaland', 'finnøy': 'Rogaland',
    'sirevåg': 'Rogaland', 'hjelmeland': 'Rogaland',
    'nedre vats': 'Rogaland', 'orre': 'Rogaland', 'bremnes': 'Rogaland',
    'rubbestadneset': 'Rogaland', 'stord': 'Rogaland', 'torp': 'Rogaland',
    # Trøndelag
    'trondheim': 'Trøndelag', 'stjørdal': 'Trøndelag', 'malvik': 'Trøndelag',
    # Sørlandet
    'kristiansand': 'Sørlandet', 'arendal': 'Sørlandet', 'grimstad': 'Sørlandet',
    # Nord-Norge
    'tromsø': 'Nord-Norge', 'bodø': 'Nord-Norge', 'harstad': 'Nord-Norge',
    'narvik': 'Nord-Norge', 'alta': 'Nord-Norge',
}

def parse_location(location):
    """Parser location-feltet og returnerer (by, forhandler, is_dealer, region)."""
    if not isinstance(location, str) or not location.strip():
        return '', '', 0, 'Annet'

    # Split på ∙ (Unicode middle dot brukt av Finn)
    parts = location.split('\u2219')
    if len(parts) == 1:
        parts = location.split('\u2022')
    if len(parts) == 1:
        parts = location.split('\u00b7')
    city = parts[0].strip()
    dealer_name = parts[1].strip() if len(parts) > 1 else ''

    # Sjekk om det er en forhandler
    is_dealer = 1 if dealer_name else 0

    # Finn region fra by-navnet
    city_lower = city.lower()
    region = 'Annet'
    for keyword, reg in REGION_MAP.items():
        if keyword == city_lower:
            region = reg
            break
    else:
        # Fallback: delvis match
        for keyword, reg in REGION_MAP.items():
            if keyword in city_lower:
                region = reg
                break

    return city, dealer_name, is_dealer, region
