import streamlit as st
import os
import json
import logging
import time
from google.cloud import texttospeech
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, VideoFileClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import requests
from io import BytesIO
import itertools

logging.basicConfig(level=logging.INFO)

# Cargar credenciales de GCP desde secrets
credentials = dict(st.secrets.gcp_service_account)
with open("google_credentials.json", "w") as f:
    json.dump(credentials, f)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

# Configuración de voces
VOCES_DISPONIBLES = {
    'es-ES-Journey-D': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Journey-F': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Journey-O': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-A': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-B': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Neural2-C': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-D': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-E': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-F': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Polyglot-1': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Standard-A': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Standard-B': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Standard-C': texttospeech.SsmlVoiceGender.FEMALE
}

# Función de creación de texto
def create_text_image(text, size=(1280, 360), font_size=30, line_height=40):
    img = Image.new('RGB', size, 'black')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)

    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        left, top, right, bottom = draw.textbbox((0, 0), test_line, font=font)
        if right > size[0] - 60:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))

    total_height = len(lines) * line_height
    y = (size[1] - total_height) // 2

    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        x = (size[0] - (right - left)) // 2
        draw.text((x, y), line, font=font, fill="white")
        y += line_height

    return np.array(img)

# Nueva función para crear la imagen de suscripción
def create_subscription_image(logo_url,size=(1280, 720), font_size=60):
    img = Image.new('RGB', size, (255, 0, 0))  # Fondo rojo
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)

    # Cargar logo del canal
    try:
        response = requests.get(logo_url)
        response.raise_for_status()
        logo_img = Image.open(BytesIO(response.content)).convert("RGBA")
        logo_img = logo_img.resize((100,100), resample=Image.Resampling.LANCZOS)
        logo_position = (20,20)
        img.paste(logo_img,logo_position,logo_img)
    except Exception as e:
        logging.error(f"Error al cargar el logo: {str(e)}")
        
    text1 = "¡SUSCRÍBETE A LECTOR DE SOMBRAS!"
    left1, top1, right1, bottom1 = draw.textbbox((0, 0), text1, font=font)
    x1 = (size[0] - (right1 - left1)) // 2
    y1 = (size[1] - (bottom1 - top1)) // 2 - (bottom1 - top1) // 2 - 20
    draw.text((x1, y1), text1, font=font, fill="white")
    
    font2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size//2)
    text2 = "Dale like y activa la campana 🔔"
    left2, top2, right2, bottom2 = draw.textbbox((0, 0), text2, font=font2)
    x2 = (size[0] - (right2 - left2)) // 2
    y2 = (size[1] - (bottom2 - top2)) // 2 + (bottom1 - top1) // 2 + 20
    draw.text((x2,y2), text2, font=font2, fill="white")

    return np.array(img)

# Función de creación de video
def create_simple_video(texto, nombre_salida, voz, logo_url, videos_fondo):
    archivos_temp = []
    clips_audio = []
    clips_finales = []
    video_fondo_clips = []
    
    try:
        logging.info("Iniciando proceso de creación de video...")
        frases = [f.strip() + "." for f in texto.split('.') if f.strip()]
        client = texttospeech.TextToSpeechClient()
        
        tiempo_acumulado = 0
        
        # Agrupamos frases en segmentos
        segmentos_texto = []
        segmento_actual = ""
        for frase in frases:
          if len(segmento_actual) + len(frase) < 300:
            segmento_actual += " " + frase
          else:
            segmentos_texto.append(segmento_actual.strip())
            segmento_actual = frase
        segmentos_texto.append(segmento_actual.strip())
        
        # Cargar los clips de video de fondo
        if videos_fondo:
            for video_file in videos_fondo:
                video_clip = VideoFileClip(video_file)
                video_fondo_clips.append(video_clip)
        
        video_clip_cycle = itertools.cycle(video_fondo_clips) if video_fondo_clips else None
        
        for i, segmento in enumerate(segmentos_texto):
            logging.info(f"Procesando segmento {i+1} de {len(segmentos_texto)}")
            
            synthesis_input = texttospeech.SynthesisInput(text=segmento)
            voice = texttospeech.VoiceSelectionParams(
                language_code="es-ES",
                name=voz,
                ssml_gender=VOCES_DISPONIBLES[voz]
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            retry_count = 0
            max_retries = 3
            
            while retry_count <= max_retries:
              try:
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
                break
              except Exception as e:
                  logging.error(f"Error al solicitar audio (intento {retry_count + 1}): {str(e)}")
                  if "429" in str(e):
                    retry_count +=1
                    time.sleep(2**retry_count)
                  else:
                    raise
            
            if retry_count > max_retries:
                raise Exception("Maximos intentos de reintento alcanzado")
            
            temp_filename = f"temp_audio_{i}.mp3"
            archivos_temp.append(temp_filename)
            with open(temp_filename, "wb") as out:
                out.write(response.audio_content)
            
            audio_clip = AudioFileClip(temp_filename)
            clips_audio.append(audio_clip)
            duracion = audio_clip.duration
            
            text_img = create_text_image(segmento)
            txt_clip = (ImageClip(text_img)
                      .set_start(tiempo_acumulado)
                      .set_duration(duracion)
                      .set_position('center'))
            
            if video_clip_cycle:
                # Seleccionar el clip de video actual
                video_fondo_clip = next(video_clip_cycle)
                # Ajustar el tamaño del video de fondo al tamaño del video resultante
                resized_video_clip = video_fondo_clip.resize(text_img.shape[1]/video_fondo_clip.w)
                video_clip_con_audio = resized_video_clip.subclip(tiempo_acumulado, min(tiempo_acumulado + duracion, video_fondo_clip.duration))
                if (video_clip_con_audio.duration < duracion):
                   video_clip_con_audio = resized_video_clip.subclip(0, min(duracion, video_fondo_clip.duration))
                   video_clip_con_audio = video_clip_con_audio.set_start(tiempo_acumulado)

                
                video_segment =  (video_clip_con_audio.set_audio(audio_clip.set_start(tiempo_acumulado))
                                .set_mask(txt_clip.set_opacity(0.8))
                                )
            else:
                video_segment = txt_clip.set_audio(audio_clip.set_start(tiempo_acumulado))
            clips_finales.append(video_segment)
            
            tiempo_acumulado += duracion
            time.sleep(0.2)

        # Añadir clip de suscripción
        subscribe_img = create_subscription_image(logo_url) # Usamos la función creada
        duracion_subscribe = 5
        
        if video_clip_cycle:
            video_fondo_clip = next(video_clip_cycle)
            resized_video_clip = video_fondo_clip.resize(subscribe_img.shape[1]/video_fondo_clip.w)
            subscribe_video_clip = resized_video_clip.subclip(tiempo_acumulado,min(tiempo_acumulado + duracion_subscribe, video_fondo_clip.duration))
            if (subscribe_video_clip.duration < duracion_subscribe):
               subscribe_video_clip = resized_video_clip.subclip(0, min(duracion_subscribe, video_fondo_clip.duration))
               subscribe_video_clip = subscribe_video_clip.set_start(tiempo_acumulado)
            subscribe_clip = (subscribe_video_clip.set_mask(
                         ImageClip(subscribe_img).set_opacity(1).set_duration(duracion_subscribe).set_start(tiempo_acumulado))
                        )
        else:
            subscribe_clip = (ImageClip(subscribe_img)
                            .set_start(tiempo_acumulado)
                            .set_duration(duracion_subscribe)
                            .set_position('center'))

        clips_finales.append(subscribe_clip)
        
        video_final = concatenate_videoclips(clips_finales, method="compose")
        
        video_final.write_videofile(
            nombre_salida,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=4
        )
        
        video_final.close()
        for video_clip in video_fondo_clips:
            video_clip.close()
        
        for clip in clips_audio:
            clip.close()
        
        for clip in clips_finales:
            clip.close()
            
        for temp_file in archivos_temp:
            try:
                if os.path.exists(temp_file):
                    os.close(os.open(temp_file, os.O_RDONLY))
                    os.remove(temp_file)
            except:
                pass
        
        return True, "Video generado exitosamente"
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        for video_clip in video_fondo_clips:
            try:
                video_clip.close()
            except:
                pass
                
        for clip in clips_audio:
            try:
                clip.close()
            except:
                pass
                
        for clip in clips_finales:
            try:
                clip.close()
            except:
                pass
                
        for temp_file in archivos_temp:
            try:
                if os.path.exists(temp_file):
                    os.close(os.open(temp_file, os.O_RDONLY))
                    os.remove(temp_file)
            except:
                pass
        
        return False, str(e)


def main():
    st.title("Creador de Videos Automático")
    
    uploaded_file = st.file_uploader("Carga un archivo de texto", type="txt")
    voz_seleccionada = st.selectbox("Selecciona la voz", options=list(VOCES_DISPONIBLES.keys()))
    logo_url = "https://yt3.ggpht.com/pBI3iT87_fX91PGHS5gZtbQi53nuRBIvOsuc-Z-hXaE3GxyRQF8-vEIDYOzFz93dsKUEjoHEwQ=s176-c-k-c0x00ffffff-no-rj"
    
    video_fondos = st.file_uploader("Carga uno o varios videos de fondo", type=["mp4", "avi", "mov"], accept_multiple_files=True)
    video_fondo_paths = []
    if video_fondos:
      for video_fondo in video_fondos:
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(video_fondo.name)[1], delete=False) as temp_file:
          temp_file.write(video_fondo.read())
          video_fondo_paths.append(temp_file.name)

    if uploaded_file:
        texto = uploaded_file.read().decode("utf-8")
        nombre_salida = st.text_input("Nombre del Video (sin extensión)", "video_generado")
        
        if st.button("Generar Video"):
            with st.spinner('Generando video...'):
                nombre_salida_completo = f"{nombre_salida}.mp4"
                success, message = create_simple_video(texto, nombre_salida_completo, voz_seleccionada, logo_url, video_fondo_paths)
                if success:
                  st.success(message)
                  st.video(nombre_salida_completo)
                  with open(nombre_salida_completo, 'rb') as file:
                    st.download_button(label="Descargar video",data=file,file_name=nombre_salida_completo)
                    
                  st.session_state.video_path = nombre_salida_completo
                else:
                  st.error(f"Error al generar video: {message}")

        if st.session_state.get("video_path"):
            st.markdown(f'<a href="https://www.youtube.com/upload" target="_blank">Subir video a YouTube</a>', unsafe_allow_html=True)
    
    if video_fondo_paths:
        for video_path in video_fondo_paths:
          try:
            if os.path.exists(video_path):
                os.close(os.open(video_path, os.O_RDONLY))
                os.remove(video_path)
          except:
              pass

if __name__ == "__main__":
    # Inicializar session state
    if "video_path" not in st.session_state:
        st.session_state.video_path = None
    main()
