import flet as ft
import logging
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import os
import asyncio
import time
import subprocess
import platform # Import platform to detect OS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class VideoDownloader:
    def __init__(self, page: ft.Page):
        self.page = page
        self.carpeta_descargas = self.obtener_carpeta_descargas()
        self.videos_cache = None
        self.archivos_cache = []
        self.videos_filtrados = []
        self.search_query = ""
        
        # Main components
        self.setup_components()
        
    def setup_components(self):
        # Top bar with logo and theme button
        self.theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            tooltip="Cambiar tema",
            on_click=self.toggle_theme,
            style=ft.ButtonStyle(
                color=ft.Colors.RED_500,
                bgcolor=ft.Colors.TRANSPARENT,
            )
        )
        
        # Modern download fields
        self.url_field = ft.TextField(
            label="URL del video",
            hint_text="Pega aquí el enlace del video...",
            prefix_icon=ft.Icons.LINK,
            expand=True,
            filled=True,
            border_radius=12,
            content_padding=ft.Padding(15, 15, 15, 15)
        )
        
        self.name_field = ft.TextField(
            label="Nombre del archivo",
            hint_text="Ej: Mi video favorito",
            prefix_icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
            expand=True,
            filled=True,
            border_radius=12,
            content_padding=ft.Padding(15, 15, 15, 15)
        )
        
        # Modern action buttons
        self.download_button = ft.ElevatedButton(
            "Descargar Video",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.iniciar_descarga,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
                padding=ft.Padding(20, 15, 20, 15),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            height=50
        )
        
        self.clear_button = ft.TextButton(
            "Limpiar",
            icon=ft.Icons.CLEAR,
            on_click=self.limpiar_campos,
            style=ft.ButtonStyle(
                padding=ft.Padding(20, 15, 20, 15),
                shape=ft.RoundedRectangleBorder(radius=12),
            )
        )
        
        # Modern progress bar
        self.progress_bar = ft.ProgressBar(
            width=None,
            height=6,
            visible=False,
            color=ft.Colors.RED_500,
            bgcolor=ft.Colors.RED_100,
            border_radius=3
        )
        
        self.status_text = ft.Text(
            size=14,
            weight=ft.FontWeight.W_500
        )
        
        # Video search field
        self.search_field = ft.TextField(
            hint_text="Buscar en mis videos...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.buscar_videos, # Keep on_change for dynamic filtering
            filled=True,
            border_radius=25,
            content_padding=ft.Padding(20, 12, 20, 12),
            expand=True
        )
        
        # Scrollable video list
        self.lista_videos = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        # Bottom navigation
        self.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.DOWNLOAD_OUTLINED, 
                    selected_icon=ft.Icons.DOWNLOAD,
                    label="Descargar"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.VIDEO_LIBRARY_OUTLINED, 
                    selected_icon=ft.Icons.VIDEO_LIBRARY,
                    label="Mis Videos"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, 
                    selected_icon=ft.Icons.SETTINGS,
                    label="Configuración"
                ),
            ],
            on_change=self.cambiar_vista,
            selected_index=0,
            bgcolor=ft.Colors.SURFACE,
            height=70,
            animation_duration=300
        )

    def obtener_carpeta_descargas(self) -> Path:
        carpeta = Path.home() / "Videos"
        if not carpeta.exists():
            carpeta = Path.home() / "Downloads"
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def listar_videos(self):
        return sorted([f for f in self.carpeta_descargas.glob("*.*") 
                      if f.suffix.lower() in ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv']], 
                     key=lambda x: x.stat().st_mtime, reverse=True)

    def buscar_videos(self, e):
        # If the search field is empty, show all videos
        if not e.control.value.strip():
            self.search_query = ""
        else:
            self.search_query = e.control.value.lower()
        self.actualizar_videos_async()

    def filtrar_videos(self, videos):
        if not self.search_query:
            return videos
        return [v for v in videos if self.search_query in v.name.lower()]

    def toggle_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_button.icon = ft.Icons.DARK_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_button.icon = ft.Icons.LIGHT_MODE
        self.page.update()

    def cambiar_vista(self, e):
        index = e.control.selected_index
        if index == 0:
            self.mostrar_vista_descarga()
        elif index == 1:
            self.mostrar_vista_videos()
        elif index == 2:
            self.mostrar_vista_configuracion()

    def crear_barra_superior(self):
        return ft.Container(
            content=ft.Row([
                ft.Text("YDExplorer", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_500),
                ft.Container(expand=True),
                self.theme_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(20, 15, 20, 15),
            bgcolor=ft.Colors.SURFACE,
            border_radius=ft.BorderRadius(0, 0, 12, 12)
        )

    def crear_card_video(self, archivo: Path):
        # Get file information
        stats = archivo.stat()
        tamaño = self.formatear_tamaño(stats.st_size)
        fecha = time.strftime('%d/%m/%Y', time.localtime(stats.st_mtime))
        
        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    leading=ft.Container(
                        content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, size=40, color=ft.Colors.RED_500), # Icon for playing video
                        width=60,
                        height=60,
                        border_radius=8,
                        bgcolor=ft.Colors.RED_50,
                        alignment=ft.alignment.center
                    ),
                    title=ft.Text(
                        archivo.stem,
                        size=16,
                        weight=ft.FontWeight.W_500,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    subtitle=ft.Column([
                        ft.Text(f"Tamaño: {tamaño}", size=12, color=ft.Colors.GREY_600),
                        ft.Text(f"Fecha: {fecha}", size=12, color=ft.Colors.GREY_600)
                    ], spacing=2),
                    trailing=ft.PopupMenuButton(
                        items=[
                            ft.PopupMenuItem(
                                text="Reproducir",
                                icon=ft.Icons.PLAY_ARROW,
                                on_click=lambda e, path=archivo: self.abrir_reproductor(path) # Option to play video
                            ),
                            ft.PopupMenuItem(
                                text="Abrir carpeta",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e, path=archivo: self.abrir_carpeta(path) # Option to open folder
                            ),
                        ]
                    ),
                    on_click=lambda e, path=archivo: self.abrir_reproductor(path) # Click on card plays video
                ),
                padding=ft.Padding(10, 10, 10, 10)
            ),
            elevation=2,
            margin=ft.Margin(0, 4, 0, 4)
        )

    def formatear_tamaño(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"

    def abrir_carpeta(self, archivo: Path):
        # Open the folder containing the file
        if platform.system() == "Windows":
            subprocess.run(f'explorer /select,"{archivo}"', shell=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", "-R", str(archivo)])
        else:  # Linux
            subprocess.run(["xdg-open", str(archivo.parent)])

    def abrir_reproductor(self, archivo: Path):
        # Open the video file with the default system player
        try:
            if platform.system() == "Windows":
                os.startfile(archivo)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(archivo)])
            else:  # Linux
                subprocess.run(["xdg-open", str(archivo)])
        except Exception as e:
            self.mostrar_error(f"No se pudo abrir el reproductor: {e}")

    def mostrar_vista_descarga(self):
        vista = ft.Column([
            self.crear_barra_superior(),
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Descargar Video", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"Los videos se guardan en: {self.carpeta_descargas}",
                                size=14,
                                color=ft.Colors.GREY_600
                            ),
                        ], spacing=8),
                        margin=ft.Margin(0, 0, 0, 30)
                    ),
                    ft.Container(
                        content=ft.Column([
                            self.url_field,
                            self.name_field,
                            ft.Row([
                                self.download_button,
                                self.clear_button
                            ], spacing=15),
                            ft.Container(
                                content=ft.Column([
                                    self.progress_bar,
                                    self.status_text
                                ], spacing=10),
                                margin=ft.Margin(0, 20, 0, 0)
                            )
                        ], spacing=20),
                        padding=ft.Padding(30, 30, 30, 30),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=16
                    )
                ], spacing=20),
                padding=ft.Padding(30, 20, 30, 20),
                expand=True
            )
        ], spacing=0, expand=True)
        
        self.actualizar_contenido_principal(vista)
        if self.page.navigation_bar:
            self.page.navigation_bar.selected_index = 0
        self.page.update()

    def mostrar_vista_videos(self):
        self.actualizar_videos_async()
        
        vista = ft.Column([
            self.crear_barra_superior(),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Mis Videos", size=28, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            text="Actualizar Videos", # Changed button text
                            icon=ft.Icons.REFRESH, # Changed button icon
                            on_click=lambda e: self.actualizar_videos_async(),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.RED_600,
                                color=ft.Colors.WHITE,
                                padding=ft.Padding(15, 10, 15, 10),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        )
                    ]),
                    ft.Container(
                        content=self.search_field,
                        margin=ft.Margin(0, 20, 0, 20)
                    ),
                    ft.Container(
                        content=self.lista_videos,
                        expand=True,
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=16,
                        padding=ft.Padding(15, 15, 15, 15)
                    )
                ], spacing=0),
                padding=ft.Padding(30, 20, 30, 20),
                expand=True
            )
        ], spacing=0, expand=True)
        
        self.actualizar_contenido_principal(vista)
        if self.page.navigation_bar:
            self.page.navigation_bar.selected_index = 1
        self.page.update()

    def mostrar_vista_configuracion(self):
        vista = ft.Column([
            self.crear_barra_superior(),
            ft.Container(
                content=ft.Column([
                    ft.Text("Configuración", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.FOLDER, size=30),
                                title=ft.Text("Carpeta de descargas", size=16, weight=ft.FontWeight.W_500),
                                subtitle=ft.Text(str(self.carpeta_descargas), size=14),
                                trailing=ft.IconButton(
                                    icon=ft.Icons.OPEN_IN_NEW,
                                    on_click=lambda e: self.abrir_carpeta(self.carpeta_descargas)
                                )
                            ),
                            ft.Divider(),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.PALETTE, size=30),
                                title=ft.Text("Tema de la aplicación", size=16, weight=ft.FontWeight.W_500),
                                subtitle=ft.Text("Cambiar entre modo claro y oscuro", size=14),
                                trailing=ft.Switch(
                                    value=self.page.theme_mode == ft.ThemeMode.DARK,
                                    on_change=lambda e: self.toggle_theme(e)
                                )
                            ),
                            ft.Divider(),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.INFO, size=30),
                                title=ft.Text("Acerca de YTDOWNLOADER", size=16, weight=ft.FontWeight.W_500),
                                subtitle=ft.Text("Descarga de videos moderno con Flet y yt-dlp", size=14),
                            )
                        ], spacing=0),
                        padding=ft.Padding(20, 20, 20, 20),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=16
                    )
                ], spacing=30),
                padding=ft.Padding(30, 20, 30, 20),
                expand=True
            )
        ], spacing=0, expand=True)
        
        self.actualizar_contenido_principal(vista)
        if self.page.navigation_bar:
            self.page.navigation_bar.selected_index = 2
        self.page.update()

    def actualizar_contenido_principal(self, contenido):
        # Clear and update the main content
        if not hasattr(self, 'contenido_principal'):
            self.contenido_principal = ft.Container(expand=True)
            self.page.add(self.contenido_principal) # Ensure the main container is on the page
        self.contenido_principal.content = contenido
        self.page.update()

    def actualizar_videos_async(self):
        def tarea():
            archivos = self.listar_videos()
            self.videos_filtrados = self.filtrar_videos(archivos)
            self.actualizar_lista_videos()
        
        self.page.run_thread(tarea)

    def actualizar_lista_videos(self):
        self.lista_videos.controls.clear()
        
        if not self.videos_filtrados:
            self.lista_videos.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.VIDEO_LIBRARY_OUTLINED, size=80, color=ft.Colors.GREY_400),
                        ft.Text("No hay videos", size=18, color=ft.Colors.GREY_600),
                        ft.Text("Descarga algunos videos para verlos aquí", size=14, color=ft.Colors.GREY_500)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    height=200
                )
            )
        else:
            for archivo in self.videos_filtrados:
                self.lista_videos.controls.append(self.crear_card_video(archivo))
        
        self.page.update()

    def opciones_yt_dlp(self, ruta_salida: Path) -> dict:
        return {
            'format': 'bv*+ba/b',
            'outtmpl': str(ruta_salida),
            'noplaylist': True,
            'progress_hooks': [self.progreso_descarga],
        }

    def progreso_descarga(self, d):
        if d['status'] == 'finished':
            self.status_text.value = "✅ Descarga completada exitosamente"
            self.progress_bar.value = 1.0
            self.progress_bar.color = ft.Colors.GREEN_500
        elif d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').replace('%', '')
            try:
                percent_float = float(percent)
                speed = d.get('_speed_str', '...')
                eta = d.get('_eta_str', '...')
                self.status_text.value = f"Descargando: {percent}% • Velocidad: {speed} • ETA: {eta}"
                self.progress_bar.value = percent_float / 100
                self.progress_bar.color = ft.Colors.RED_500
            except ValueError: # Catch ValueError if percent is not a valid float
                self.status_text.value = "Descargando..."
                
        self.progress_bar.visible = True
        self.page.update()

    def iniciar_descarga(self, e):
        url = self.url_field.value.strip()
        nombre = self.name_field.value.strip()

        if not url:
            self.mostrar_error("Por favor, ingresa una URL válida")
            return
        if not nombre:
            self.mostrar_error("Por favor, ingresa un nombre para el archivo")
            return

        ruta = self.carpeta_descargas / f"{nombre}.%(ext)s"
        opciones = self.opciones_yt_dlp(ruta)

        def tarea():
            try:
                self.estado_controles(False)
                self.status_text.value = "Iniciando descarga..."
                self.progress_bar.visible = True
                self.page.update()
                
                with YoutubeDL(opciones) as ydl:
                    ydl.download([url])
                    
                self.status_text.value = "🎉 ¡Descarga completada exitosamente!"
                self.progress_bar.value = 1.0
                self.progress_bar.color = ft.Colors.GREEN_500
                
                # Clear fields after successful download
                self.page.run_task(self.limpiar_tras_descarga)
                
            except DownloadError as e:
                self.status_text.value = f"❌ Error de descarga: {str(e)[:100]}..."
                self.progress_bar.value = 0
                self.progress_bar.color = ft.Colors.RED_500
            except Exception as ex:
                self.status_text.value = f"❌ Error inesperado: {str(ex)[:100]}..."
                self.progress_bar.value = 0
                self.progress_bar.color = ft.Colors.RED_500
            finally:
                self.estado_controles(True)
                self.page.update()

        self.page.run_thread(tarea)

    async def limpiar_tras_descarga(self):
        await asyncio.sleep(3)  # Wait 3 seconds
        self.url_field.value = ""
        self.name_field.value = ""
        self.page.update()

    def mostrar_error(self, mensaje):
        self.status_text.value = f"❌ {mensaje}"
        self.status_text.color = ft.Colors.RED_500
        self.page.update()

    def limpiar_campos(self, e):
        self.url_field.value = ""
        self.name_field.value = ""
        self.status_text.value = ""
        self.progress_bar.visible = False
        self.page.update()

    def estado_controles(self, habilitar: bool):
        self.url_field.disabled = not habilitar
        self.name_field.disabled = not habilitar
        self.download_button.disabled = not habilitar
        self.page.update()

    def crear_layout_principal(self):
        # Main content that will change based on navigation
        self.contenido_principal = ft.Container(expand=True)
        
        # Main layout only contains the content area, navigation bar is assigned to page.navigation_bar
        layout = ft.Column([
            self.contenido_principal
        ], expand=True, spacing=0)
        
        return layout

async def main(page: ft.Page):
    page.title = "YouTube Download"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 0
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 600
    
    # Custom colors inspired by YouTube
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.RED_500,
        visual_density=ft.VisualDensity.COMFORTABLE
    )

    downloader = VideoDownloader(page)
    
    # Assign the navigation bar to the page's navigation_bar property
    page.navigation_bar = downloader.navigation_bar

    # Create and display the main layout
    layout_principal = downloader.crear_layout_principal()
    page.add(layout_principal)
    
    # Show initial view (download)
    downloader.mostrar_vista_descarga()

ft.app(target=main)
