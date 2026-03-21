import os
import json
import random
import math
import numpy as np
import requests
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip, AudioFileClip

# ===============================
# ⚙️ CONFIGURATION & DATES
# ===============================
START_YEAR = date(2026, 1, 1)
END_YEAR   = date(2026, 12, 31)
TODAY      = date.today()

# Asset paths
FONT_LEXEND_PATH = "assets/Lexend-Bold.ttf"
FONT_MONO_PATH   = "assets/FiraMono-Bold.ttf"
AUDIO_PATH       = "assets/CLOCK_AUDIO.mp3"
LOGO_PATH        = "assets/logo.png"
SILUETA_PATH     = "assets/silueta_2026.png"

# Visual config
WIDTH, HEIGHT = 1080, 1920
FPS             = 30
VIDEO_DURATION  = 10
ANIMATION_DURATION = 6
FACTOR_ESCALA   = 1.5

BAR_COLOR  = (40, 120, 220, 255)
TEXT_COLOR = (255, 255, 255, 255)
COLOR_GRIS = (140, 140, 140, 255)
BG_COLOR   = (0, 0, 0, 255)

# ===============================
# 📅 DAILY ANIMATION SELECTOR
# ===============================
MODOS = [
    "RED_NEURONAL",       # Monday
    "MATRIZ_PIXELADA",    # Tuesday
    "FLUJO_CURVO",        # Wednesday
    "ONDAS_DE_RADIO",     # Thursday
    "BURBUJAS",           # Friday
    "FUEGOS_ARTIFICIALES",# Saturday
    "LINEAS_DIGITALES"    # Sunday
]
MODO_PARTICULAS = MODOS[TODAY.weekday()]

# ===============================
# 🛠️ UTILITIES
# ===============================

def send_telegram(message):
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={'chat_id': chat_id, 'text': message})
        except:
            pass

def get_dropbox_access_token():
    app_key       = os.getenv("DROPBOX_APP_KEY")
    app_secret    = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    if not all([app_key, app_secret, refresh_token]):
        raise Exception("Missing DROPBOX_APP_KEY, DROPBOX_APP_SECRET or DROPBOX_REFRESH_TOKEN")
    r = requests.post("https://api.dropbox.com/oauth2/token", data={
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     app_key,
        "client_secret": app_secret
    })
    if r.status_code != 200:
        raise Exception(f"Error getting access token: {r.text}")
    return r.json()["access_token"]

def upload_to_dropbox(file_path, dest_filename):
    token     = get_dropbox_access_token()
    dest_path = f"/2026 Uploader/{dest_filename}"
    headers = {
        "Authorization":   f"Bearer {token}",
        "Dropbox-API-Arg": json.dumps({"path": dest_path, "mode": "overwrite"}),
        "Content-Type":    "application/octet-stream"
    }
    with open(file_path, "rb") as f:
        data = f.read()
    for attempt in range(3):
        try:
            r = requests.post("https://content.dropboxapi.com/2/files/upload",
                              headers=headers, data=data, timeout=60)
            if r.status_code == 200:
                return dest_path
            raise Exception(f"Dropbox error {r.status_code}: {r.text}")
        except requests.exceptions.SSLError as e:
            if attempt < 2:
                print(f"SSL error, retrying ({attempt+1}/3)...")
            else:
                raise Exception(f"SSL error after 3 attempts: {e}")

# ===============================
# 🎬 VIDEO GENERATION
# ===============================

def generate_video():
    print(f"📅 Date: {TODAY} — Mode: {MODO_PARTICULAS}")

    # Progress calculation
    visual_progress = (TODAY - START_YEAR).days / (END_YEAR - START_YEAR).days
    visual_progress = max(0, min(visual_progress, 1))
    final_percentage = visual_progress * 100

    # Silueta scaling
    if not os.path.exists(SILUETA_PATH):
        raise FileNotFoundError(f"Not found: {SILUETA_PATH}")
    silueta_original = Image.open(SILUETA_PATH).convert("RGBA")
    nuevo_w = int(silueta_original.size[0] * FACTOR_ESCALA)
    nuevo_h = int(silueta_original.size[1] * FACTOR_ESCALA)
    silueta_img = silueta_original.resize((nuevo_w, nuevo_h), Image.LANCZOS)
    silueta_w, silueta_h = silueta_img.size

    sil_x = (WIDTH - silueta_w) // 2
    sil_y = (HEIGHT - silueta_h) // 2 + 100

    NUM_TOP_Y    = int(306 * FACTOR_ESCALA)
    NUM_BOTTOM_Y = int(924 * FACTOR_ESCALA)
    NUM_TOTAL_H  = NUM_BOTTOM_Y - NUM_TOP_Y
    MARGEN_LATERAL = int(25 * FACTOR_ESCALA)

    AREA_TOP    = sil_y + NUM_TOP_Y
    AREA_BOTTOM = sil_y + NUM_BOTTOM_Y
    AREA_LEFT   = sil_x + MARGEN_LATERAL
    AREA_RIGHT  = (sil_x + silueta_w) - MARGEN_LATERAL

    # Logo
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize(
        (int(WIDTH * 0.15), int(logo.height * ((WIDTH * 0.15) / logo.width))),
        Image.LANCZOS
    )

    # Fonts
    font_text   = ImageFont.truetype(FONT_LEXEND_PATH, 72)
    font_num    = ImageFont.truetype(FONT_MONO_PATH, 72)
    font_footer = ImageFont.truetype(FONT_LEXEND_PATH, 52)

    # Particles init
    particulas = []
    objetos_activos = []
    num_p = int(300 * FACTOR_ESCALA * 0.8) if MODO_PARTICULAS == "MATRIZ_PIXELADA" else int(100 * FACTOR_ESCALA * 0.8)

    for _ in range(num_p):
        p = {
            'x':      random.uniform(AREA_LEFT, AREA_RIGHT),
            'y':      random.uniform(AREA_TOP, AREA_BOTTOM),
            'speed':  random.uniform(2.0, 5.0),
            'drift':  random.uniform(-0.5, 0.5),
            'size':   random.randint(int(2 * FACTOR_ESCALA), int(5 * FACTOR_ESCALA)),
            'op':     random.randint(100, 200),
            'offset': random.uniform(0, 2 * math.pi)
        }
        if MODO_PARTICULAS == "RED_NEURONAL":
            p.update({
                'vx':   random.uniform(-1.0, 1.0),
                'vy':   random.uniform(-1.0, 1.0),
                'size': random.randint(int(6 * FACTOR_ESCALA), int(9 * FACTOR_ESCALA))
            })
        particulas.append(p)

    footer_l1 = "The countdown continues"
    footer_l2 = "Link in bio"

    frames = []
    total_frames = FPS * VIDEO_DURATION

    for i in range(total_frames):
        t_actual     = i / FPS
        t_normalizado = min(t_actual / ANIMATION_DURATION, 1.0)
        anim_factor  = 1 - math.pow(1 - t_normalizado, 4)
        curr_completed = visual_progress * anim_factor

        y_azul_inicio = AREA_TOP + int(NUM_TOTAL_H * curr_completed)
        y_azul_fin    = AREA_BOTTOM

        frame    = Image.new("RGBA", (WIDTH, HEIGHT), BG_COLOR)
        draw     = ImageDraw.Draw(frame)
        fx_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw_fx  = ImageDraw.Draw(fx_layer)

        if y_azul_inicio < y_azul_fin:
            draw_fx.rectangle([AREA_LEFT, y_azul_inicio, AREA_RIGHT, y_azul_fin], fill=BAR_COLOR)

            # --- PARTICLE ANIMATIONS ---
            if MODO_PARTICULAS == "LINEAS_DIGITALES":
                for p in particulas:
                    p['y'] -= p['speed']; p['x'] += p['drift']
                    if p['y'] < AREA_TOP: p['y'] = AREA_BOTTOM
                    draw_fx.rectangle([p['x'], p['y'], p['x'] + 2, p['y'] + p['size'] * 4],
                                      fill=(255, 255, 255, p['op']))

            elif MODO_PARTICULAS == "BURBUJAS":
                for p in particulas:
                    p['y'] -= p['speed']
                    x_pos = p['x'] + math.sin(t_actual * 4 + p['offset']) * 2
                    if p['y'] < AREA_TOP: p['y'] = AREA_BOTTOM
                    draw_fx.ellipse([x_pos - p['size'], p['y'] - p['size'],
                                     x_pos + p['size'], p['y'] + p['size']],
                                    outline=(255, 255, 255, p['op']), width=2)

            elif MODO_PARTICULAS == "FUEGOS_ARTIFICIALES":
                if random.random() < 0.1 and (y_azul_fin - y_azul_inicio) > 50:
                    objetos_activos.append({
                        'x': random.uniform(AREA_LEFT + 20, AREA_RIGHT - 20),
                        'y': random.uniform(y_azul_inicio, y_azul_fin),
                        'age': 0, 'max': random.randint(20, 35)
                    })
                for f in objetos_activos[:]:
                    f['age'] += 1; prg = f['age'] / f['max']
                    if prg > 1: objetos_activos.remove(f); continue
                    for s in range(8):
                        ang  = (2 * math.pi / 8) * s
                        dist = (1 - math.pow(1 - prg, 2)) * (30 * FACTOR_ESCALA)
                        px   = f['x'] + math.cos(ang) * dist
                        py   = f['y'] + math.sin(ang) * dist
                        draw_fx.ellipse([px - 2, py - 2, px + 2, py + 2],
                                        fill=(255, 255, 255, int(255 * (1 - prg))))

            elif MODO_PARTICULAS == "MATRIZ_PIXELADA":
                for p in particulas:
                    p['y'] += p['speed']
                    if p['y'] > AREA_BOTTOM: p['y'] = AREA_TOP
                    draw_fx.rectangle([p['x'], p['y'], p['x'] + 3, p['y'] + 3],
                                      fill=(255, 255, 255, p['op']))

            elif MODO_PARTICULAS == "RED_NEURONAL":
                dist_max = 70 * FACTOR_ESCALA
                for p in particulas:
                    p['x'] += p['vx']; p['y'] += p['vy']
                    if p['x'] < AREA_LEFT or p['x'] > AREA_RIGHT:   p['vx'] *= -1
                    if p['y'] < AREA_TOP  or p['y'] > AREA_BOTTOM:  p['vy'] *= -1
                    draw_fx.ellipse([p['x'] - 2, p['y'] - 2, p['x'] + 2, p['y'] + 2],
                                    fill=(255, 255, 255, 200))
                    for p2 in particulas:
                        d = math.hypot(p['x'] - p2['x'], p['y'] - p2['y'])
                        if d < dist_max:
                            draw_fx.line([p['x'], p['y'], p2['x'], p2['y']],
                                         fill=(255, 255, 255, int(100 * (1 - d / dist_max))), width=1)

            elif MODO_PARTICULAS == "ONDAS_DE_RADIO":
                if random.random() < 0.2 and (y_azul_fin - y_azul_inicio) > 50:
                    objetos_activos.append({
                        'x': random.uniform(AREA_LEFT, AREA_RIGHT),
                        'y': random.uniform(y_azul_inicio, y_azul_fin),
                        'r': 5, 'op': 255
                    })
                for o in objetos_activos[:]:
                    o['r'] += 0.8; o['op'] -= 4
                    if o['op'] <= 0 or o['r'] > (50 * FACTOR_ESCALA):
                        objetos_activos.remove(o); continue
                    draw_fx.ellipse([o['x'] - o['r'], o['y'] - o['r'],
                                     o['x'] + o['r'], o['y'] + o['r']],
                                    outline=(255, 255, 255, o['op']), width=2)

            elif MODO_PARTICULAS == "FLUJO_CURVO":
                for p in particulas:
                    p['y'] -= p['speed']
                    x_pos = p['x'] + math.sin(p['y'] * 0.02 + t_actual * 5) * 20
                    if p['y'] < AREA_TOP: p['y'] = AREA_BOTTOM
                    draw_fx.ellipse([x_pos - 3, p['y'] - 3, x_pos + 3, p['y'] + 3],
                                    fill=(255, 255, 255, p['op']))

        # Black curtain above fill + silueta + logo
        if y_azul_inicio > AREA_TOP:
            draw_fx.rectangle([AREA_LEFT, AREA_TOP, AREA_RIGHT, y_azul_inicio], fill=BG_COLOR)
        frame.alpha_composite(fx_layer)
        frame.paste(silueta_img, (sil_x, sil_y), mask=silueta_img)
        frame.alpha_composite(logo, ((WIDTH - logo.width) // 2, 120))

        # --- TOP TEXT ---
        pct_val  = curr_completed * 100
        txt_pre  = "2026 is "
        txt_num  = f"{pct_val:05.2f}"
        txt_suf  = "%"
        w_pre = draw.textlength(txt_pre, font_text)
        w_n   = draw.textlength(txt_num, font_num)
        w_s   = draw.textlength(txt_suf, font_text)
        start_x  = (WIDTH - (w_pre + w_n + w_s)) / 2
        text_y   = 320
        draw.text((start_x, text_y), txt_pre, font=font_text, fill=TEXT_COLOR, anchor="lm")
        draw.text((start_x + w_pre, text_y), txt_num, font=font_num, fill=TEXT_COLOR, anchor="lm")
        draw.text((start_x + w_pre + w_n, text_y), txt_suf, font=font_text, fill=TEXT_COLOR, anchor="lm")
        draw.text((WIDTH // 2, text_y + 80), "completed", fill=TEXT_COLOR, font=font_text, anchor="mm")

        # --- FOOTER ---
        y_f1 = AREA_BOTTOM + 80
        y_f2 = y_f1 + 65
        w_f1 = draw.textlength(footer_l1, font=font_footer)
        x_f1 = (WIDTH - w_f1) // 2
        draw.text((x_f1, y_f1), footer_l1, fill=COLOR_GRIS, font=font_footer)
        w_f2 = draw.textlength(footer_l2, font=font_footer)
        x_f2 = (WIDTH - w_f2) // 2
        draw.text((x_f2, y_f2), footer_l2, fill=COLOR_GRIS, font=font_footer)

        # --- PULSING RED DOT ---
        pulse    = (math.sin(2 * math.pi * t_actual / 1.5) + 1) / 2
        dot_size = int(22 * (1 + 0.3 * pulse))
        dot_x    = x_f1 - 50
        dot_y    = y_f1 + 28
        dot_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d_dot     = ImageDraw.Draw(dot_layer)
        d_dot.ellipse([dot_x - dot_size // 2, dot_y - dot_size // 2,
                       dot_x + dot_size // 2, dot_y + dot_size // 2],
                      fill=(255, 30, 30, int(255 - (150 * pulse))))
        frame.alpha_composite(dot_layer)

        frames.append(np.array(frame))

    # --- VIDEO & AUDIO ---
    clip = ImageSequenceClip(frames, fps=FPS)
    if os.path.exists(AUDIO_PATH):
        try:
            audio = AudioFileClip(AUDIO_PATH).subclip(0, min(VIDEO_DURATION, AudioFileClip(AUDIO_PATH).duration))
            clip  = clip.set_audio(audio)
        except Exception as e:
            print(f"Audio error: {e}")

    days_left  = (END_YEAR - TODAY).days
    months_en  = ["january", "february", "march", "april", "may", "june",
                  "july", "august", "september", "october", "november", "december"]
    date_en    = f"{TODAY.day} {months_en[TODAY.month - 1]} {TODAY.year}"
    final_name = f"{date_en} - {days_left} days left in 2026 - #2026 #newyear #countdown #progressbar #video.mp4"

    temp_name = "render_temp.mp4"
    clip.write_videofile(temp_name, codec="libx264", audio_codec="aac", fps=FPS,
                         preset="ultrafast", logger=None)
    return temp_name, final_name, final_percentage, days_left


if __name__ == "__main__":
    try:
        temp_file, final_name, p, days = generate_video()
        upload_to_dropbox(temp_file, final_name)
        send_telegram(f"✅ 2026 at {p:.2f}% — {days} days left — mode {MODO_PARTICULAS} uploaded to Dropbox.")
    except Exception as e:
        send_telegram(f"❌ ERROR: {str(e)}")
        print(e)
