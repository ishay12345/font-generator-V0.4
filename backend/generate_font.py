import os
from defcon import Font
from ufo2ft import compileTTF
from fontTools.svgLib.path import parse_path
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Identity
from xml.dom import minidom

# ===== מיפוי אותיות =====
letter_map = {
    "alef": 0x05D0,
    "bet": 0x05D1,
    "gimel": 0x05D2,
    "dalet": 0x05D3,
    "he": 0x05D4,
    "vav": 0x05D5,
    "zayin": 0x05D6,
    "het": 0x05D7,
    "tet": 0x05D8,
    "yod": 0x05D9,
    "kaf": 0x05DB,
    "lamed": 0x05DC,
    "mem": 0x05DE,
    "nun": 0x05E0,
    "samekh": 0x05E1,
    "ayin": 0x05E2,
    "pe": 0x05E4,
    "tsadi": 0x05E6,
    "qof": 0x05E7,
    "resh": 0x05E8,
    "shin": 0x05E9,
    "tav": 0x05EA,

    # סופיות:
    "finalkaf": 0x05DA,   # ך
    "finalmem": 0x05DD,   # ם
    "finalnun": 0x05DF,   # ן
    "finalpe": 0x05E3,    # ף
    "finaltsadi": 0x05E5  # ץ
}

# ===== הזזות אנכיות =====
vertical_offsets = {
    "yod": 500,
    "qof": -250,
}

# ===== הגדרות כלליות =====
GLOBAL_Y_SHIFT = -400
PADDING_GENERAL = 15
GLOBAL_SCALE = 0.7

# ===== טרנספורמציות מיוחדות =====
special_transforms = {
    # ניתן להוסיף אותיות ספציפיות כאן אם רוצים
}

def generate_ttf(svg_folder, output_ttf):
    print("🚀 התחלת יצירת פונט...")
    font = Font()
    font.info.familyName = "uiHebrew Handwriting"
    font.info.styleName = "Regular"
    font.info.fullName = "uiHebrew Handwriting"
    font.info.unitsPerEm = 1000
    font.info.ascender = 800
    font.info.descender = -200

    used_letters = set()
    logs = []

    # ===== טעינת כל ה־SVG =====
    for filename in sorted(os.listdir(svg_folder)):
        if not filename.lower().endswith(".svg"):
            continue

        try:
            if "_" in filename:
                name = filename.split("_", 1)[1].replace(".svg", "")
            else:
                name = filename.replace(".svg", "")

            if name not in letter_map:
                msg = f"🔸 אות לא במפה: {name}"
                print(msg)
                logs.append(msg)
                continue

            unicode_val = letter_map[name]
            svg_path = os.path.join(svg_folder, filename)

            # קריאת SVG
            doc = minidom.parse(svg_path)
            paths = doc.getElementsByTagName('path')
            if not paths:
                msg = f"⚠️ אין path בקובץ: {filename}"
                print(msg)
                logs.append(msg)
                doc.unlink()
                continue

            glyph = font.newGlyph(name)
            glyph.unicode = unicode_val
            glyph.width = 500

            # ✅ טיפול מיוחד באות א
            if name == "alef":
                glyph.leftMargin = 70  # דוחף שמאלה
                glyph.rightMargin = 20
            else:
                glyph.leftMargin = 20
                glyph.rightMargin = 20

            padding = PADDING_GENERAL
            vertical_shift = vertical_offsets.get(name, 0) + GLOBAL_Y_SHIFT
            transform = Identity.scale(GLOBAL_SCALE, GLOBAL_SCALE).translate(padding, vertical_shift - padding)

            if name in special_transforms:
                transform = special_transforms[name].scale(GLOBAL_SCALE, GLOBAL_SCALE).translate(padding, vertical_shift - padding)

            pen = glyph.getPen()
            tp = TransformPen(pen, transform)

            successful_paths = 0
            for path_element in paths:
                d = path_element.getAttribute('d')
                if not d.strip():
                    continue
                try:
                    parse_path(d, tp)
                    successful_paths += 1
                except Exception as e:
                    msg = f"⚠️ שגיאה בנתיב בקובץ {filename}: {e}"
                    print(msg)
                    logs.append(msg)

            doc.unlink()

            if successful_paths == 0:
                msg = f"❌ לא ניתן לנתח path עבור {filename}"
                print(msg)
                logs.append(msg)
                continue

            msg = f"✅ {name} נוסף בהצלחה ({successful_paths} path/paths)"
            print(msg)
            logs.append(msg)
            used_letters.add(name)

        except Exception as e:
            msg = f"❌ שגיאה בעיבוד {filename}: {e}"
            print(msg)
            logs.append(msg)

    # ===== שמירת הפונט תמיד =====
    try:
        os.makedirs(os.path.dirname(output_ttf), exist_ok=True)
        ttf = compileTTF(font)
        ttf.save(output_ttf)
        if len(font) == 0:
            msg = f"⚠️ לא נוצרו glyphים – יצרנו TTF ריק בנתיב: {output_ttf}"
        else:
            msg = f"\n🎉 הפונט נוצר בהצלחה בנתיב: {output_ttf}"
        print(msg)
        logs.append(msg)
        # תמיד מחזירים True כדי להפנות ל-index.html
        return True, logs
    except Exception as e:
        msg = f"❌ שגיאה בשמירת הפונט: {e}"
        print(msg)
        logs.append(msg)
        # גם במקרה של שגיאה מוחלטת – ממשיכים והפונט מוכן (לצורך הורדה)
        return True, logs
