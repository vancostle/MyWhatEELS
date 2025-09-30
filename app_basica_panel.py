import panel as pn

# Habilitar extensiones de Panel
pn.extension()

class AppBasica:
    """
    Aplicación básica con Panel con 2 variables numéricas dinámicas
    """
    
    def __init__(self):
        # Solo 1 variable numérica
        self.valor1 = 50.0
        
        # Leer parámetros de la URL si existen
        self.leer_parametros_url()
        
        self.crear_interfaz()
    
    def leer_parametros_url(self):
        """Leer parámetros de la URL y aplicarlos a los sliders"""
        try:
            if hasattr(pn.state, 'location') and pn.state.location:
                params = pn.state.location.query_params
                if 'valores' in params:
                    valores_str = params['valores'][0]  # Obtener el primer valor
                    # Remover paréntesis y dividir por coma
                    valores_str = valores_str.strip('()')
                    min_val, max_val = map(float, valores_str.split(','))
                    
                    print(f"Parámetros URL encontrados: valores=({min_val}, {max_val})")
                    
                    # Actualizar valores iniciales del primer slider
                    self.valor1 = (min_val + max_val) / 2
                    
                    # Guardar valores para aplicar más tarde al slider
                    self.valores_iniciales_slider1 = (min_val, max_val)
                else:
                    self.valores_iniciales_slider1 = None
            else:
                self.valores_iniciales_slider1 = None
        except Exception as e:
            print(f"Error leyendo parámetros URL: {e}")
            self.valores_iniciales_slider1 = None
    
    def crear_interfaz(self):
        """Crear la interfaz de usuario"""
        
        # Range slider para valor1
        valor_inicial1 = self.valores_iniciales_slider1 if self.valores_iniciales_slider1 else (self.valor1-10, self.valor1+10)
        self.slider_valor1 = pn.widgets.RangeSlider(
            name="Valor 1", 
            start=0, end=100, 
            value=valor_inicial1,  # Usar valores de URL si existen
            step=0.1,
            width=300
        )
        
        # Panel HTML invisible para ejecutar JavaScript
        self.js_executor = pn.pane.HTML("", width=0, height=0)
        
        # Botón para abrir nueva ventana con parámetros
        self.boton_nueva_ventana = pn.widgets.Button(
            name="Abrir Nueva Ventana", 
            button_type="primary",
            width=200
        )
        # Usar callback Python
        self.boton_nueva_ventana.on_click(self.abrir_nueva_ventana)
        
        # Configurar callback para actualización automática
        self.slider_valor1.param.watch(self.on_valor1_change, 'value')
    
    def on_valor1_change(self, event):
        """Callback cuando cambia el range slider del valor1"""
        # El valor del range slider es una tupla (min, max)
        # Tomamos el punto medio como el nuevo valor
        min_val, max_val = event.new
        self.valor1 = (min_val + max_val) / 2
        print(f"Valor 1 cambió a: {self.valor1:.2f} (rango: {min_val:.2f} - {max_val:.2f})")
    
    def abrir_nueva_ventana(self, event):
        """Abrir nueva ventana con los valores del primer slider como parámetros"""
        try:
            # Obtener los valores actuales del primer slider
            min_val, max_val = self.slider_valor1.value
            
            # Detectar el puerto actual automáticamente
            if hasattr(pn.state, 'location') and pn.state.location:
                url_base = f"http://{pn.state.location.hostname}:{pn.state.location.port}"
            else:
                url_base = "http://localhost:5007"  # Puerto por defecto cuando se ejecuta directamente
            
            valores_tupla = f"({min_val:.2f},{max_val:.2f})"
            url_con_parametros = f"{url_base}?valores={valores_tupla}"
            
            print(f"Abriendo nueva ventana con URL: {url_con_parametros}")
            
            # Ejecutar JavaScript a través del panel invisible
            self.js_executor.object = f"""
                <script>
                    setTimeout(() => {{
                        console.log('Abriendo ventana desde Panel...');
                        window.open('{url_con_parametros}', '_blank');
                    }}, 100);
                </script>
            """
            
        except Exception as e:
            print(f"Error al abrir nueva ventana: {e}")
    
    def crear_layout(self):
        """Crear el layout principal de la aplicación"""
        
        # Layout simple con solo el slider y botón (el js_executor es invisible)
        layout = pn.Column(
            "# Range Slider App",
            self.slider_valor1,
            self.boton_nueva_ventana,
            self.js_executor,  # Invisible (width=0, height=0)
            width=400,
            margin=20
        )
        
        return layout
    
# Función principal para servir la aplicación
def crear_app():
    """Crear y retornar la aplicación"""
    app = AppBasica()
    return app.crear_layout()

# Para ejecutar la aplicación
if __name__ == "__main__":
    # Crear la aplicación
    app = AppBasica()
    layout = app.crear_layout()
    
    # Servir la aplicación con show() para ejecutar directamente
    layout.show(port=5007)
    
    # También hacer servable para panel serve
    layout.servable()