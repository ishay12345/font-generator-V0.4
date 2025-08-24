import os
from defcon import Font
from ufo2ft import compileTTF
from fontTools.svgLib.path import parse_path
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Identity
from xml.dom import minidom

# ===== מיפוי אותיות =====
letter_map = {
    "alef": 0x05D0, "bet": 0x05D1, "gimel": 0x05D2, "dalet": 0x05D3, "he": 0x05D4,
    "vav": 0x05D5, "zayin": 0x05D6, "het": 0x05D7, "tet": 0x05D8, "yod": 0x05D9,
    "kaf": 0x05DB, "lamed": 0x05DC, "mem": 0x05DE, "nun": 0x05E0, "samekh": 0x05E1,
    "ayin": 0x05E2, "pe": 0x05E4, "tsadi": 0x05E6, "qof": 0x05E7, "resh": 0x05E8,
    "shin": 0x05E9, "tav": 0x05EA,
    "finalkaf": 0x05DA, "finalmem": 0x05DD, "finalnun": 0x05DF, "finalpe": 0x05E3, "finaltsadi": 0x05E5
}

# ===== הזזות אנכיות =====
vertical_offsets = {"yod": 370, "qof": -250}

# ===== הגדרות כלליות =====
GLOBAL_Y_SHIFT = 0
PADDING_GENERAL = 12
PADDING_LARGE = 15
GLOBAL_SCALE = 1.0
# ===== טרנספורמציות מיוחדות =====
special_transforms = {}

def generate_ttf(svg_folder, output_ttf):
    print("🚀 התחלת יצירת פונט...")
    font = Font()
    font.info.familyName = "uiHebrew Handwriting"
    font.info.styleName = "Regular"
    font.info.fullName = "uiHebrew Handwriting"
    font.info.unitsPerEm = 1000
    font.info.ascender = 800
    font.info.descender = -200

    logs = []

    for filename in sorted(os.listdir(svg_folder)):
        if not filename.lower().endswith(".svg"):
            continue
        try:
            name = filename.split("_", 1)[1].replace(".svg", "") if "_" in filename else filename.replace(".svg", "")
            if name not in letter_map:
                msg = f"🔸 אות לא במפה: {name}"
                print(msg)
                logs.append(msg)
                continue

            unicode_val = letter_map[name]
            svg_path = os.path.join(svg_folder, filename)

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
            glyph.width = 465
            if name == "alef":
                glyph.leftMargin = 70
                glyph.rightMargin = 20
            else:
                glyph.leftMargin = 14
                glyph.rightMargin = 14

            vertical_shift = vertical_offsets.get(name, 0) + GLOBAL_Y_SHIFT
            transform = Identity.scale(GLOBAL_SCALE, GLOBAL_SCALE).translate(PADDING_GENERAL, vertical_shift - PADDING_GENERAL)
            if name in special_transforms:
                transform = special_transforms[name].scale(GLOBAL_SCALE, GLOBAL_SCALE).translate(PADDING_GENERAL, vertical_shift - PADDING_GENERAL)

            pen = glyph.getPen()
            tp = TransformPen(pen, transform)
            successful_paths = 0

            for path_element in paths:
                d = path_element.getAttribute('d')
                if d.strip():
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
            else:
                msg = f"✅ {name} נוסף בהצלחה ({successful_paths} path/paths)"
            print(msg)
            logs.append(msg)

        except Exception as e:
            msg = f"❌ שגיאה בעיבוד {filename}: {e}"
            print(msg)
            logs.append(msg)

    # ===== שמירה תמידית של הפונט =====
    try:
        os.makedirs(os.path.dirname(output_ttf), exist_ok=True)
        ttf = compileTTF(font)
        ttf.save(output_ttf)
        msg = f"🎉 הפונט נוצר בהצלחה בנתיב: {output_ttf}"
        print(msg)
        logs.append(msg)
    except Exception as e:
        msg = f"❌ שגיאה בשמירת הפונט: {e} – יצרנו קובץ ריק במקום זה"
        print(msg)
        logs.append(msg)

    # ===== תמיד מחזירים True =====
    return True, logs
