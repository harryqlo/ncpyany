"""
Servicio de compresión de imágenes para fotos de mantenimiento.
Optimiza fotos para almacenamiento sin perder calidad visual.
"""
import io
import os
from PIL import Image
from datetime import datetime

# Configuración de compresión
COMPRESSION_CONFIG = {
    'max_width': 1920,          # Máxima resolución en ancho
    'max_height': 1440,         # Máxima resolución en alto
    'quality': 85,              # Calidad JPEG/WebP (0-100)
    'target_format': 'webp',    # Formato objetivo (webp es más compacto)
    'target_size_kb': 500,      # Tamaño objetivo máximo
    'fallback_format': 'jpeg',  # Formato alternativo si no soporta WebP
}


class CompresorFotos:
    """Servicio para comprimir fotos de mantenimiento"""
    
    @staticmethod
    def comprimir_imagen(archivo_bytes: bytes, 
                        tipo_foto: str = 'documentacion',
                        calidad: int = None) -> dict:
        """
        Comprime una imagen al formato WebP de forma inteligente.
        
        Args:
            archivo_bytes: Bytes de la imagen original
            tipo_foto: Tipo de foto ('antes', 'durante', 'despues', 'documentacion')
            calidad: Calidad de compresión (0-100), default según config
            
        Returns:
            dict con:
                - foto_blob: Bytes comprimida
                - tamaño_original_kb: Tamaño original
                - tamaño_kb: Tamaño comprimido
                - ancho, alto: Dimensiones
                - formato: Formato final
                - ratio_reduccion: Porcentaje reducido
        """
        try:
            if calidad is None:
                calidad = COMPRESSION_CONFIG['quality']
            
            # Abrir imagen desde bytes
            imagen_original = Image.open(io.BytesIO(archivo_bytes))
            
            # Convertir a RGB si tiene transparencia
            if imagen_original.mode in ('RGBA', 'LA', 'P'):
                # Crear fondo blanco
                fondo = Image.new('RGB', imagen_original.size, (255, 255, 255))
                if imagen_original.mode == 'P':
                    imagen_original = imagen_original.convert('RGBA')
                fondo.paste(imagen_original, mask=imagen_original.split()[-1] if imagen_original.mode == 'RGBA' else None)
                imagen_original = fondo
            elif imagen_original.mode != 'RGB':
                imagen_original = imagen_original.convert('RGB')
            
            # Obtener dimensiones originales
            ancho_original, alto_original = imagen_original.size
            
            # Redimensionar si es muy grande
            ancho_max = COMPRESSION_CONFIG['max_width']
            alto_max = COMPRESSION_CONFIG['max_height']
            
            ratio = min(ancho_max / ancho_original, alto_max / alto_original)
            if ratio < 1:
                nuevo_ancho = int(ancho_original * ratio)
                nuevo_alto = int(alto_original * ratio)
                imagen_original = imagen_original.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
            
            # Guardar en memoria con compresión WebP
            buffer = io.BytesIO()
            formato_usado = COMPRESSION_CONFIG['target_format']
            
            try:
                imagen_original.save(buffer, format='WEBP', quality=calidad, method=6)
            except Exception:
                # Si WebP no está disponible, usar JPEG
                formato_usado = COMPRESSION_CONFIG['fallback_format']
                imagen_original.save(buffer, format='JPEG', quality=calidad, optimize=True)
            
            foto_comprimida = buffer.getvalue()
            
            # Calcular estadísticas
            tamaño_original_kb = len(archivo_bytes) / 1024
            tamaño_comprimido_kb = len(foto_comprimida) / 1024
            ratio_reduccion = ((tamaño_original_kb - tamaño_comprimido_kb) / tamaño_original_kb * 100) if tamaño_original_kb > 0 else 0
            
            ancho_final, alto_final = imagen_original.size
            
            return {
                'ok': True,
                'foto_blob': foto_comprimida,
                'tamaño_original_kb': round(tamaño_original_kb, 2),
                'tamaño_kb': round(tamaño_comprimido_kb, 2),
                'ancho': ancho_final,
                'alto': alto_final,
                'formato': formato_usado,
                'ratio_reduccion': round(ratio_reduccion, 1),
                'metadata': {
                    'tipo_foto': tipo_foto,
                    'fecha_procesado': datetime.now().isoformat(),
                    'calidad_configurada': calidad,
                }
            }
        
        except Exception as e:
            return {
                'ok': False,
                'error': str(e),
                'mensaje': f'Error comprimiendo imagen: {e}'
            }
    
    @staticmethod
    def comprimir_batch(lista_archivos: list) -> dict:
        """
        Comprime múltiples fotos en lote.
        
        Args:
            lista_archivos: Lista de tuples (archivo_bytes, tipo_foto)
            
        Returns:
            dict con resultados de cada compresión y estadísticas totales
        """
        resultados = []
        total_original = 0
        total_comprimido = 0
        
        for archivo_bytes, tipo_foto in lista_archivos:
            resultado = CompresorFotos.comprimir_imagen(archivo_bytes, tipo_foto)
            resultados.append(resultado)
            
            if resultado['ok']:
                total_original += resultado['tamaño_original_kb']
                total_comprimido += resultado['tamaño_kb']
        
        ratio_total = ((total_original - total_comprimido) / total_original * 100) if total_original > 0 else 0
        
        return {
            'ok': True,
            'cantidad_procesadas': len(resultados),
            'exitosas': sum(1 for r in resultados if r.get('ok')),
            'fallidas': sum(1 for r in resultados if not r.get('ok')),
            'detalles': resultados,
            'estadisticas': {
                'tamaño_original_kb': round(total_original, 2),
                'tamaño_comprimido_kb': round(total_comprimido, 2),
                'ratio_reduccion_total': round(ratio_total, 1),
            }
        }
    
    @staticmethod
    def obtener_miniatura(foto_blob: bytes, 
                         tamaño: tuple = (200, 200)) -> bytes:
        """
        Genera una miniatura de la foto comprimida para preview.
        
        Args:
            foto_blob: Bytes de la foto comprimida
            tamaño: (ancho, alto) de la miniatura
            
        Returns:
            Bytes de la miniatura WebP
        """
        try:
            imagen = Image.open(io.BytesIO(foto_blob))
            imagen.thumbnail(tamaño, Image.Resampling.LANCZOS)
            
            # Convertir a RGB si necesario
            if imagen.mode in ('RGBA', 'LA', 'P'):
                fondo = Image.new('RGB', imagen.size, (255, 255, 255))
                if imagen.mode == 'P':
                    imagen = imagen.convert('RGBA')
                fondo.paste(imagen, mask=imagen.split()[-1] if imagen.mode == 'RGBA' else None)
                imagen = fondo
            
            buffer = io.BytesIO()
            try:
                imagen.save(buffer, format='WEBP', quality=75, method=6)
            except Exception:
                imagen.save(buffer, format='JPEG', quality=75, optimize=True)
            
            return buffer.getvalue()
        
        except Exception as e:
            print(f"Error generando miniatura: {e}")
            return None


if __name__ == '__main__':
    # Test simple
    print("Módulo de compresión de fotos - Listo para importar")
    print(f"Configuración: {COMPRESSION_CONFIG}")
