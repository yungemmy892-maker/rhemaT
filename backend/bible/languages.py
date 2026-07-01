"""
Supported display languages for the VerseID app UI.
The app currently serves English Bible text only (KJV/WEB/ASV/DRA are all
English translations). This language list controls the user's *interface*
language preference — it is stored and returned by the settings API so the
frontend can respect it for any localised strings it implements.

Languages are grouped by region. Nigerian languages are listed first since
the primary market is Nigeria, followed by other West African languages,
then broader African languages, then international options.
"""

LANGUAGES = [
    # ── Nigerian languages ──────────────────────────────────────────────
    {"code": "en", "name": "English", "native": "English", "region": "Nigeria"},
    {"code": "yo", "name": "Yoruba", "native": "Yorùbá", "region": "Nigeria"},
    {"code": "ig", "name": "Igbo", "native": "Asụsụ Igbo", "region": "Nigeria"},
    {"code": "ha", "name": "Hausa", "native": "Harshen Hausa", "region": "Nigeria"},
    {"code": "pcm", "name": "Nigerian Pidgin", "native": "Naijá", "region": "Nigeria"},
    {"code": "ful", "name": "Fulfulde", "native": "Fulfulde", "region": "Nigeria"},
    {"code": "bin", "name": "Edo (Bini)", "native": "Ẹdo", "region": "Nigeria"},
    {"code": "ijo", "name": "Ijaw", "native": "Izon", "region": "Nigeria"},
    {"code": "tiv", "name": "Tiv", "native": "Tiv", "region": "Nigeria"},
    {"code": "ibibio", "name": "Ibibio", "native": "Ibibio", "region": "Nigeria"},
    {"code": "nupe", "name": "Nupe", "native": "Nupe", "region": "Nigeria"},
    {"code": "kanuri", "name": "Kanuri", "native": "Kànùrí", "region": "Nigeria"},
    # ── West Africa ─────────────────────────────────────────────────────
    {"code": "ak", "name": "Akan (Twi)", "native": "Twi", "region": "West Africa"},
    {"code": "ee", "name": "Ewe", "native": "Eʋegbe", "region": "West Africa"},
    {"code": "ga", "name": "Ga", "native": "Gã", "region": "West Africa"},
    {"code": "bam", "name": "Bambara", "native": "Bamanankan", "region": "West Africa"},
    {"code": "wo", "name": "Wolof", "native": "Wolof", "region": "West Africa"},
    {"code": "ff", "name": "Fula", "native": "Pulaar", "region": "West Africa"},
    {"code": "kri", "name": "Krio", "native": "Krio", "region": "West Africa"},
    # ── East Africa ─────────────────────────────────────────────────────
    {"code": "sw", "name": "Swahili", "native": "Kiswahili", "region": "East Africa"},
    {"code": "am", "name": "Amharic", "native": "አማርኛ", "region": "East Africa"},
    {"code": "om", "name": "Oromo", "native": "Afaan Oromoo", "region": "East Africa"},
    {"code": "so", "name": "Somali", "native": "Soomaali", "region": "East Africa"},
    {"code": "rw", "name": "Kinyarwanda", "native": "Ikinyarwanda", "region": "East Africa"},
    {"code": "rn", "name": "Kirundi", "native": "Ikirundi", "region": "East Africa"},
    {"code": "lg", "name": "Luganda", "native": "Luganda", "region": "East Africa"},
    # ── Southern Africa ──────────────────────────────────────────────────
    {"code": "zu", "name": "Zulu", "native": "isiZulu", "region": "Southern Africa"},
    {"code": "xh", "name": "Xhosa", "native": "isiXhosa", "region": "Southern Africa"},
    {"code": "af", "name": "Afrikaans", "native": "Afrikaans", "region": "Southern Africa"},
    {"code": "st", "name": "Sesotho", "native": "Sesotho", "region": "Southern Africa"},
    {"code": "tn", "name": "Setswana", "native": "Setswana", "region": "Southern Africa"},
    {"code": "sn", "name": "Shona", "native": "chiShona", "region": "Southern Africa"},
    {"code": "nd", "name": "Ndebele", "native": "isiNdebele", "region": "Southern Africa"},
    # ── North Africa / Francophone ───────────────────────────────────────
    {"code": "ar", "name": "Arabic", "native": "العربية", "region": "North Africa"},
    {"code": "ber", "name": "Tamazight (Berber)", "native": "ⵜⴰⵎⴰⵣⵉⵖⵜ", "region": "North Africa"},
    {"code": "fr", "name": "French", "native": "Français", "region": "Francophone Africa"},
    {"code": "ln", "name": "Lingala", "native": "Lingála", "region": "Central Africa"},
    # ── International ────────────────────────────────────────────────────
    {"code": "pt", "name": "Portuguese", "native": "Português", "region": "International"},
    {"code": "es", "name": "Spanish", "native": "Español", "region": "International"},
]
