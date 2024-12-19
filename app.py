import streamlit as st
import os
import glob
import sys
import importlib.util
import tempfile

VOCES_DISPONIBLES = [
    'es-ES-Journey-D (Masculino)',
    'es-ES-Journey-F (Femenino)',
    'es-ES-Journey-O (Femenino)',
    'es-ES-Neural2-A (Femenino)',
    'es-ES-Neural2-B (Masculino)',
    'es-ES-Neural2-C (Femenino)',
    'es-ES-Neural2-D (Femenino)',
    'es-ES-Neural2-E (Femenino)',
    'es-ES-Neural2-F (Masculino)',
    'es-ES-Polyglot-1 (Masculino)',
    'es-ES-Standard-A (Femenino)',
    'es-ES-Standard-B (Masculino)',
    'es-ES-Standard-C (Femenino)',
    'es-ES-Standard-D (Femenino)',
    'es-ES-Standard-E (Masculino)',
    'es-ES-Standard-F (Femenino)',
    'es-ES-Studio-C (Femenino)',
    'es-ES-Studio-F (Masculino)',
    'es-ES-Wavenet-B (Masculino)',
    'es-ES-Wavenet-C (Femenino)',
    'es-ES-Wavenet-D (Femenino)',
    'es-ES-Wavenet-E (Masculino)',
    'es-ES-Wavenet-F (Femenino)'
]

def load_module(path):
    spec = importlib.util.spec_from_file_location("video_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    st.title("Video Text Generator")

    # Input Text
    text = st.text_area("Enter Text:", height=150)

    # Video Title
    title = st.text_input("Video Title:")

    # Voice Selection
    selected_voice = st.selectbox("Select Voice:", VOCES_DISPONIBLES, index=3).split(' ')[0]

    # Source Videos Folder
    source_folder = st.text_input("Source Videos Folder:")
    
    if source_folder:
        videos = glob.glob(os.path.join(source_folder, "*.mp4"))
        video_names = [os.path.basename(video) for video in videos]
        selected_clips = st.multiselect("Available Clips (Select multiple):", video_names)
        selected_clips_paths = [os.path.join(source_folder, clip) for clip in selected_clips]
    else:
         selected_clips_paths = []
    

    # Output Video Folder
    output_folder = st.text_input("Output Video Folder:")
    
    # Generate Button
    if st.button("Generate Video"):
       
        if not text:
            st.error("Please enter text for the video.")
            return

        if not source_folder:
           st.error("Please select a source videos folder.")
           return

        if not output_folder:
            st.error("Please select an output folder.")
            return

        if not selected_clips_paths:
            st.error("Please select at least one video clip.")
            return

        output_filename = f"{title}.mp4" if title else "video_output.mp4"
        output_path = os.path.join(output_folder, output_filename)

        try:
            video_generator = load_module("video_generator.py")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            class StatusPrinter:
                 def __init__(self, status_text, progress_bar):
                     self.status_text = status_text
                     self.progress_bar = progress_bar

                 def write(self, message):
                      self.status_text.text(message)
                      if "Progreso:" in message:
                          try:
                               prog = float(message.split("Progreso:")[1].split("%")[0].strip())
                               self.progress_bar.progress(prog/100)
                          except:
                              pass


                 def flush(self):
                     pass

            old_stdout = sys.stdout
            sys.stdout = StatusPrinter(status_text, progress_bar)

            try:
                 video_generator.crear_video(
                     texto=text,
                     carpeta_videos=source_folder,
                     nombre_salida=output_path,
                     voz_seleccionada=selected_voice,
                     selected_clips=selected_clips_paths
                 )
                 st.success(f"Video generated successfully at {output_path}")
            except Exception as e:
                 st.error(f"Error: {str(e)}")
            finally:
                 sys.stdout = old_stdout
                 progress_bar.progress(0)
                 status_text.text("")
                 

            
            #Display video if it was generated successfully
            if os.path.exists(output_path):
               with open(output_path, 'rb') as file:
                   video_bytes = file.read()
               st.video(video_bytes)


        except Exception as e:
           st.error(f"Failed to load video generation module: {str(e)}")


if __name__ == "__main__":
    main()
