"""Genera el icono de la app y las imágenes de cada voz (se ejecuta una vez)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from presets import META, PRESETS

HERE = os.path.dirname(os.path.abspath(__file__))
EMOJI = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", 109)


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w, h, c1, c2):
    a, b = hex2rgb(c1), hex2rgb(c2)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.6 + y / h * 0.4)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return img


def voice_card(name, c1, c2, emoji, W=360, H=240):
    img = gradient(W, H, c1, c2).convert("RGBA")
    # ondas decorativas
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(deco)
    for i, r in enumerate(range(60, 420, 46)):
        d.ellipse([W - 90 - r, H / 2 - r, W - 90 + r, H / 2 + r], outline=(255, 255, 255, 34 - i * 3), width=3)
    img = Image.alpha_composite(img, deco)
    # emoji con sombra
    em = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    emoji = emoji.replace("Fe0f", "")
    emoji = emoji.replace("️", "")
    ImageDraw.Draw(em).text((80, 80), emoji, font=EMOJI, embedded_color=True, anchor="mm")
    es = int(H * 0.62)
    em = em.resize((es, es), Image.LANCZOS)
    shadow = Image.new("RGBA", em.size, (0, 0, 0, 0))
    shadow.putalpha(em.getchannel("A").point(lambda v: v * 0.45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    x0 = W - es - int(H * 0.12) if W > H * 1.2 else (W - es) // 2
    img.alpha_composite(shadow, (x0 + 5, (H - es) // 2 + 15))
    img.alpha_composite(em, (x0, (H - es) // 2))
    return img.convert("RGB")


def app_icon(size=1024):
    S = size
    base = gradient(S, S, "#8b5cf6", "#06b6d4").convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.23), fill=255)
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(base, (0, 0), mask)
    # brillo superior
    gloss = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([-S * 0.3, -S * 0.75, S * 1.3, S * 0.45], fill=(255, 255, 255, 38))
    icon = Image.alpha_composite(icon, Image.composite(gloss, Image.new("RGBA", (S, S)), mask))
    d = ImageDraw.Draw(icon)
    white = (255, 255, 255, 255)
    cx = S / 2
    # micrófono
    mw, mt, mb = S * 0.17, S * 0.2, S * 0.56
    d.rounded_rectangle([cx - mw / 2, mt, cx + mw / 2, mb], radius=mw / 2, fill=white)
    lw = int(S * 0.045)
    d.arc([cx - S * 0.16, S * 0.3, cx + S * 0.16, S * 0.64], 0, 180, fill=white, width=lw)
    d.line([cx, S * 0.64, cx, S * 0.75], fill=white, width=lw)
    d.rounded_rectangle([cx - S * 0.11, S * 0.74, cx + S * 0.11, S * 0.79], radius=lw / 2, fill=white)
    # ondas de sonido a los lados
    for k, r in enumerate((0.27, 0.36)):
        a = 200 - k * 70
        col = (255, 255, 255, a)
        box = [cx - S * r, S * 0.38 - S * r * 0.0 - S * r * 0.6, cx + S * r, S * 0.38 + S * r * 0.6]
        box = [cx - S * r, S * 0.42 - S * r, cx + S * r, S * 0.42 + S * r]
        d.arc(box, -35, 35, fill=col, width=int(S * 0.035))
        d.arc(box, 145, 215, fill=col, width=int(S * 0.035))
    # insignia "2.0"
    bf = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", int(S * 0.15))
    bx0, by0, bx1, by1 = S * 0.6, S * 0.72, S * 0.97, S * 0.95
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=S * 0.06, fill=(17, 17, 34, 235))
    d.text(((bx0 + bx1) / 2, (by0 + by1) / 2), "2.0", font=bf, fill=white, anchor="mm")
    return icon


PAD_COLORS = [("#8b5cf6", "#4c1d95"), ("#06b6d4", "#155e75"), ("#f43f5e", "#881337"), ("#f59e0b", "#92400e"),
              ("#22c55e", "#14532d"), ("#ec4899", "#831843"), ("#3b82f6", "#1e3a8a"), ("#14b8a6", "#134e4a")]

MODULES = {"tono": ("🎵", "#8b5cf6", "#312e81"), "mod": ("🤖", "#06b6d4", "#0c4a6e"), "textura": ("🔥", "#f97316", "#7c2d12"),
           "filtros": ("🎚️", "#22c55e", "#14532d"), "eco": ("🏔️", "#3b82f6", "#1e3a8a"), "reverb": ("⛪", "#d4af37", "#5b4a12"),
           "salida": ("🔊", "#ec4899", "#831843")}
BANNERS = {"audio": ("🎧", "#6366f1", "#0f172a"), "atajos": ("⌨️", "#06b6d4", "#0f172a"),
           "chat": ("💬", "#8b5cf6", "#0f172a"), "info": ("🚀", "#ec4899", "#0f172a")}


def pick_colors(key):
    return PAD_COLORS[sum(map(ord, key)) % len(PAD_COLORS)]


def sound_art(path, name, emoji):
    """Imagen cuadrada para un botón del soundboard."""
    c1, c2 = pick_colors(name)
    voice_card(name, c1, c2, emoji, 300, 300).save(path, quality=88)


def custom_art(path, name):
    c1, c2 = pick_colors(name)
    voice_card(name, c1, c2, "🎛️").save(path, quality=90)


def build_all():
    out = os.path.join(HERE, "ui", "img")
    for sub in ("voces", "modulos", "ajustes", "sonidos", "personal"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    for k, (e, a, b) in MODULES.items():
        voice_card(k, a, b, e, 120, 120).save(os.path.join(out, "modulos", f"{k}.jpg"), quality=90)
    for k, (e, a, b) in BANNERS.items():
        voice_card(k, a, b, e, 760, 180).save(os.path.join(out, "ajustes", f"{k}.jpg"), quality=88)


if __name__ == "__main__":
    build_all()
    out = os.path.join(HERE, "ui", "img")
    os.makedirs(os.path.join(out, "voces"), exist_ok=True)
    for i, name in enumerate(PRESETS):
        _, emoji, c1, c2, _ = META[name]
        voice_card(name, c1, c2, emoji).save(os.path.join(out, "voces", f"{i:02d}.jpg"), quality=90)
    ic = app_icon()
    ic.resize((512, 512), Image.LANCZOS).save(os.path.join(out, "logo.png"))
    ic.save(os.path.join(HERE, "icono.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ok")
