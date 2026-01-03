# pages/secretaria_dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import io

from utils.google_sheets import GoogleSheetsManager
from utils.send_apoderados import ApoderadosEmailSender
from utils.email_sender import EmailManager
from utils.helpers import export_to_excel, format_porcentaje
from components.headers import render_section_header, render_metric_card
from components.modals import show_confirmation_modal, show_info_modal
from config.constants import Sede, ICONS

def show_secretaria_dashboard(sheets_manager: GoogleSheetsManager, 
                             email_manager: EmailManager,
                             apoderados_sender: ApoderadosEmailSender):
    """Dashboard para Equipo Sede."""
    
    user_sede = st.session_state.sede
    
    # Validar sede
    if user_sede == "TODAS":
        st.warning("⚠️ Usuario de Equipo Sede sin sede asignada. Contacte al administrador.")
        return
    
    render_section_header(f"📊 Panel de Equipo Sede - {user_sede}")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Cursos de Sede", 
        "📈 Reportes", 
        "📧 Comunicaciones Masivas",
        "⚙️ Configuración"
    ])
    
    with tab1:
        _show_cursos_sede_tab(sheets_manager, user_sede)
    
    with tab2:
        _show_reportes_tab(sheets_manager, user_sede)
    
    with tab3:
        _show_comunicaciones_tab(apoderados_sender, user_sede)
    
    with tab4:
        _show_configuracion_tab(sheets_manager, email_manager, user_sede)

def _show_cursos_sede_tab(sheets_manager: GoogleSheetsManager, user_sede: str):
    """Tab de visualización de cursos por sede."""
    
    st.subheader(f"📚 Cursos de la Sede: {user_sede}")
    
    try:
        with st.spinner("🔄 Cargando cursos..."):
            # Cargar cursos CON datos de asistencia
            cursos_sede = sheets_manager.load_courses_by_sede(user_sede, include_attendance=True)
        
        if not cursos_sede:
            st.info(f"ℹ️ No se encontraron cursos para la sede {user_sede}")
            return
        
        # DEBUG EXTENDIDO: Mostrar estructura COMPLETA
        with st.expander("🔍 DEBUG COMPLETO: Estructura de datos cargados", expanded=True):
            st.write(f"**Total cursos encontrados:** {len(cursos_sede)}")
            
            for i, (curso_nombre, curso_data) in enumerate(cursos_sede.items()):
                st.write(f"\n**Curso {i+1}: {curso_nombre}**")
                st.write(f"  - Profesor: {curso_data.get('profesor', 'No encontrado')}")
                st.write(f"  - Sede: {curso_data.get('sede', 'No encontrada')}")
                st.write(f"  - Asignatura: {curso_data.get('asignatura', 'No especificada')}")
                
                estudiantes = curso_data.get('estudiantes', [])
                st.write(f"  - Estudiantes ({len(estudiantes)}):")
                if estudiantes:
                    for j, estudiante in enumerate(estudiantes[:10]):  # Mostrar primeros 10
                        st.write(f"    {j+1}. {estudiante}")
                    if len(estudiantes) > 10:
                        st.write(f"    ... y {len(estudiantes)-10} más")
                
                fechas = curso_data.get('fechas', [])
                st.write(f"  - Fechas ({len(fechas)}):")
                if fechas:
                    for j, fecha in enumerate(fechas[:10]):  # Mostrar primeras 10
                        st.write(f"    {j+1}. {fecha}")
                    if len(fechas) > 10:
                        st.write(f"    ... y {len(fechas)-10} más")
                
                asistencias = curso_data.get('asistencias', {})
                st.write(f"  - Asistencias: {len(asistencias)} estudiantes con datos")
                if estudiantes and asistencias and estudiantes[0] in asistencias:
                    ejemplo = asistencias[estudiantes[0]]
                    st.write(f"  - Ejemplo asistencia para {estudiantes[0]}:")
                    if isinstance(ejemplo, dict):
                        for fecha, estado in list(ejemplo.items())[:5]:
                            st.write(f"    - {fecha}: {'✅' if estado else '❌'}")
                    elif isinstance(ejemplo, list):
                        for j, estado in enumerate(ejemplo[:10]):
                            st.write(f"    - Clase {j+1}: {'✅' if estado else '❌'}")
                
                st.write("---")
        
        # Resto del código original...
        
        # Selector de curso
        curso_seleccionado = st.selectbox(
            "Selecciona un curso para ver detalles:",
            list(cursos_sede.keys()),
            key="curso_sede_select"
        )
        
        if not curso_seleccionado:
            return
        
        curso_data = cursos_sede[curso_seleccionado]
        
        # Información del curso
        with st.expander("📋 Información del Curso", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric_card(
                    "👨‍🎓 Estudiantes",
                    len(curso_data.get("estudiantes", [])),
                    ICONS["estudiante"]
                )
            with col2:
                render_metric_card(
                    "📅 Clases",
                    len(curso_data.get("fechas", [])),
                    "📅"
                )
            with col3:
                render_metric_card(
                    "👨‍🏫 Profesor",
                    curso_data.get("profesor", "No asignado"),
                    ICONS["profesor"]
                )
            with col4:
                render_metric_card(
                    "📘 Asignatura",
                    curso_data.get("asignatura", "No especificada"),
                    "📘"
                )
        
        # Visualización de asistencia
        _show_asistencia_curso(curso_data, curso_seleccionado)
        
    except Exception as e:
        st.error(f"❌ Error cargando cursos: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.info("🔧 Verifique que la hoja de clases tenga el formato correcto.")

def _show_asistencia_curso(curso_data: Dict[str, Any], curso_nombre: str):
    """Muestra la asistencia de un curso específico."""
    
    st.subheader("📊 Asistencia por Estudiante")
    
    # DEBUG: Mostrar estructura de datos
    with st.expander("🔍 DEBUG: Ver estructura de datos crudos", expanded=False):
        st.write("**Estudiantes encontrados:**", curso_data.get("estudiantes", []))
        st.write("**Número de estudiantes:**", len(curso_data.get("estudiantes", [])))
        st.write("**Fechas encontradas:**", curso_data.get("fechas", []))
        st.write("**Número de fechas:**", len(curso_data.get("fechas", [])))
        
        if curso_data.get("asistencias"):
            st.write("**Claves en asistencias:**", list(curso_data.get("asistencias", {}).keys())[:5])
            # Mostrar ejemplo de un estudiante
            if curso_data.get("estudiantes"):
                ejemplo_est = curso_data["estudiantes"][0]
                asist_ejemplo = curso_data.get("asistencias", {}).get(ejemplo_est, {})
                st.write(f"**Asistencia para {ejemplo_est}:**", asist_ejemplo)
                if isinstance(asist_ejemplo, dict):
                    st.write(f"**Valores del dict:**", list(asist_ejemplo.values())[:5])
                elif isinstance(asist_ejemplo, list):
                    st.write(f"**Valores de la lista:**", asist_ejemplo[:5])
        else:
            st.warning("⚠️ No hay datos de asistencias")
    
    # Check si hay datos
    if not curso_data.get("estudiantes"):
        st.info("ℹ️ No hay estudiantes en este curso")
        return
    
    if not curso_data.get("fechas"):
        st.warning("⚠️ No hay fechas de clases registradas")
        return
    
    # Selector de vista
    vista = st.radio(
        "Vista:",
        ["📋 Lista Completa", "📈 Resumen Estadístico", "⚠️ Baja Asistencia (<70%)", "🏆 Excelente Asistencia (>85%)"],
        horizontal=True,
        key=f"vista_{curso_nombre}"
    )
    
    # OBTENER DATOS DE ASISTENCIA CORRECTAMENTE
    data = _calcular_datos_asistencia(curso_data)
    
    if not data:
        st.warning("⚠️ No se pudieron calcular los datos de asistencia")
        return
    
    df = pd.DataFrame(data)
    
    # Mostrar según vista seleccionada
    if vista == "📈 Resumen Estadístico":
        _show_resumen_estadistico(df)
    elif vista == "⚠️ Baja Asistencia (<70%)":
        _show_baja_asistencia(df)
    elif vista == "🏆 Excelente Asistencia (>85%)":
        _show_excelente_asistencia(df)
    else:
        _show_lista_completa(df, curso_nombre)

def _calcular_datos_asistencia(curso_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calcula los datos de asistencia según la estructura real de Google Sheets."""
    
    data = []
    
    # Obtener estudiantes del curso
    estudiantes = curso_data.get("estudiantes", [])
    fechas = curso_data.get("fechas", [])
    
    if not estudiantes or not fechas:
        return data
    
    # Obtener datos de asistencia
    asistencias = curso_data.get("asistencias", {})
    total_clases = len(fechas)
    
    for estudiante in estudiantes:
        # Obtener asistencia del estudiante
        asistencia_est = asistencias.get(estudiante, {})
        
        # Calcular presentes basado en la estructura real
        presentes = 0
        
        if isinstance(asistencia_est, dict):
            # Si es diccionario {fecha: estado}
            presentes = sum(
                1 for estado in asistencia_est.values() 
                if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE", "Sí", "sí", "SI"]
            )
        elif isinstance(asistencia_est, list):
            # Si es lista de valores
            presentes = sum(
                1 for estado in asistencia_est 
                if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE", "Sí", "sí", "SI"]
            )
        else:
            # Intentar obtener de otras formas
            try:
                # Buscar en estructura alternativa
                for fecha in fechas:
                    if fecha in asistencia_est:
                        valor = asistencia_est[fecha]
                        if valor in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE", "Sí", "sí", "SI"]:
                            presentes += 1
            except:
                presentes = 0
        
        # Calcular porcentaje
        ausentes = total_clases - presentes if total_clases > 0 else 0
        porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
        
        # Determinar estado
        if porcentaje >= 85:
            estado = "🏆 Excelente"
            icono = "✅"
        elif porcentaje >= 70:
            estado = "✅ Adecuado"
            icono = "✅"
        elif porcentaje >= 50:
            estado = "⚠️ Bajo"
            icono = "⚠️"
        else:
            estado = "❌ Crítico"
            icono = "❌"
        
        data.append({
            "Estudiante": estudiante,
            "Presente": presentes,
            "Ausente": ausentes,
            "Total Clases": total_clases,
            "Asistencia %": round(porcentaje, 1),
            "Estado": estado,
            "Icono": icono
        })
    
    return data

def _show_resumen_estadistico(df: pd.DataFrame):
    """Muestra resumen estadístico."""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg = df['Asistencia %'].mean()
        st.metric("📊 Asistencia Promedio", f"{avg:.1f}%", 
                 delta=f"{avg - 70:.1f}%" if avg else None,
                 delta_color="normal" if avg >= 70 else "inverse")
    
    with col2:
        criticos = len(df[df['Asistencia %'] < 70])
        st.metric("⚠️ < 70%", criticos, 
                 delta=f"{criticos/len(df)*100:.1f}%" if len(df) > 0 else None,
                 delta_color="inverse")
    
    with col3:
        regulares = len(df[(df['Asistencia %'] >= 70) & (df['Asistencia %'] < 85)])
        st.metric("🟡 70-84%", regulares)
    
    with col4:
        excelentes = len(df[df['Asistencia %'] >= 85])
        st.metric("🏆 ≥85%", excelentes)
    
    # Gráfico de distribución
    st.subheader("📈 Distribución de Asistencia")
    
    # Preparar datos para gráfico
    chart_df = df.copy()
    chart_df = chart_df.sort_values('Asistencia %', ascending=False)
    
    # Mostrar gráfico de barras
    chart_data = chart_df[['Estudiante', 'Asistencia %']].set_index('Estudiante')
    st.bar_chart(chart_data, height=300)

def _show_baja_asistencia(df: pd.DataFrame):
    """Muestra estudiantes con baja asistencia."""
    
    df_filtrado = df[df['Asistencia %'] < 70].copy()
    
    if len(df_filtrado) > 0:
        st.warning(f"⚠️ {len(df_filtrado)} estudiantes con baja asistencia (<70%)")
        
        # Ordenar por menor porcentaje
        df_filtrado = df_filtrado.sort_values('Asistencia %')
        
        # Mostrar tabla con colores
        st.dataframe(
            df_filtrado[['Estudiante', 'Asistencia %', 'Presente', 'Ausente', 'Total Clases']],
            use_container_width=True,
            height=400,
            column_config={
                "Estudiante": st.column_config.TextColumn(
                    "Estudiante",
                    width="medium"
                ),
                "Asistencia %": st.column_config.ProgressColumn(
                    "Asistencia %",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small"
                ),
                "Presente": st.column_config.NumberColumn(
                    "✅ Presente",
                    width="small"
                ),
                "Ausente": st.column_config.NumberColumn(
                    "❌ Ausente",
                    width="small"
                ),
                "Total Clases": st.column_config.NumberColumn(
                    "📅 Total",
                    width="small"
                )
            }
        )
        
        # Opción para exportar
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar estudiantes con baja asistencia",
            data=csv,
            file_name=f"baja_asistencia_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.success("✅ Todos los estudiantes tienen asistencia adecuada (≥70%)")

def _show_excelente_asistencia(df: pd.DataFrame):
    """Muestra estudiantes con excelente asistencia."""
    
    df_filtrado = df[df['Asistencia %'] >= 85].copy()
    
    if len(df_filtrado) > 0:
        st.success(f"🏆 {len(df_filtrado)} estudiantes con excelente asistencia (≥85%)")
        
        # Ordenar por mayor porcentaje
        df_filtrado = df_filtrado.sort_values('Asistencia %', ascending=False)
        
        # Mostrar tabla
        st.dataframe(
            df_filtrado[['Estudiante', 'Asistencia %', 'Presente', 'Total Clases']],
            use_container_width=True,
            height=400,
            column_config={
                "Estudiante": st.column_config.TextColumn(
                    "Estudiante",
                    width="medium"
                ),
                "Asistencia %": st.column_config.ProgressColumn(
                    "Asistencia %",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small"
                ),
                "Presente": st.column_config.NumberColumn(
                    "✅ Presente",
                    width="small"
                ),
                "Total Clases": st.column_config.NumberColumn(
                    "📅 Total",
                    width="small"
                )
            }
        )
    else:
        st.info("ℹ️ No hay estudiantes con asistencia excelente (≥85%)")

def _show_lista_completa(df: pd.DataFrame, curso_nombre: str):
    """Muestra lista completa de estudiantes."""
    
    # Selector de orden
    orden = st.selectbox(
        "Ordenar por:",
        ["Estudiante (A-Z)", "Estudiante (Z-A)", 
         "Asistencia % (Ascendente)", "Asistencia % (Descendente)",
         "Presentes (Mayor a menor)", "Ausentes (Mayor a menor)"],
        key=f"orden_{curso_nombre}"
    )
    
    # Aplicar orden
    if orden == "Estudiante (A-Z)":
        df = df.sort_values('Estudiante')
    elif orden == "Estudiante (Z-A)":
        df = df.sort_values('Estudiante', ascending=False)
    elif orden == "Asistencia % (Ascendente)":
        df = df.sort_values('Asistencia %')
    elif orden == "Asistencia % (Descendente)":
        df = df.sort_values('Asistencia %', ascending=False)
    elif orden == "Presentes (Mayor a menor)":
        df = df.sort_values('Presente', ascending=False)
    elif orden == "Ausentes (Mayor a menor)":
        df = df.sort_values('Ausente', ascending=False)
    
    # Mostrar estadísticas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Estudiantes", len(df))
    with col2:
        st.metric("Asistencia Promedio", f"{df['Asistencia %'].mean():.1f}%")
    with col3:
        st.metric("Total Clases", df['Total Clases'].iloc[0] if len(df) > 0 else 0)
    
    # Mostrar tabla con formato mejorado
    st.dataframe(
        df[['Estudiante', 'Asistencia %', 'Presente', 'Ausente', 'Total Clases', 'Estado']],
        use_container_width=True,
        height=500,
        column_config={
            "Estudiante": st.column_config.TextColumn(
                "👤 Estudiante",
                width="large",
                help="Nombre del estudiante"
            ),
            "Asistencia %": st.column_config.ProgressColumn(
                "📊 Asistencia",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width="medium",
                help="Porcentaje de asistencia"
            ),
            "Presente": st.column_config.NumberColumn(
                "✅ Presente",
                width="small",
                help="Clases presentes"
            ),
            "Ausente": st.column_config.NumberColumn(
                "❌ Ausente",
                width="small",
                help="Clases ausentes"
            ),
            "Total Clases": st.column_config.NumberColumn(
                "📅 Total",
                width="small",
                help="Total de clases programadas"
            ),
            "Estado": st.column_config.TextColumn(
                "🎯 Estado",
                width="small",
                help="🏆 ≥85% Excelente | ✅ 70-84% Adecuado | ⚠️ 50-69% Bajo | ❌ <50% Crítico"
            )
        }
    )
    
    # Botones de exportación
    st.subheader("📤 Exportar Datos")
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar CSV",
            data=csv,
            file_name=f"asistencia_completa_{curso_nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_{curso_nombre}"
        )
    
    with col_export2:
        excel_data = export_to_excel(df, f"asistencia_{curso_nombre}")
        st.download_button(
            label="📊 Descargar Excel",
            data=excel_data,
            file_name=f"asistencia_{curso_nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"excel_{curso_nombre}"
        )
    
    with col_export3:
        # Opción para imprimir
        if st.button("🖨️ Generar PDF", use_container_width=True, key=f"pdf_{curso_nombre}"):
            st.info("🔧 Función de PDF en desarrollo")

def _show_reportes_tab(sheets_manager: GoogleSheetsManager, user_sede: str):
    """Tab de generación de reportes."""
    
    st.subheader("📈 Reportes de Asistencia")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        reporte_tipo = st.selectbox(
            "Tipo de Reporte",
            [
                "📊 Resumen General", 
                "📋 Asistencia Detallada", 
                "⚠️ Estudiantes Críticos (<70%)", 
                "🏆 Top 10 Mejor Asistencia",
                "📅 Asistencia por Fecha"
            ],
            key="reporte_tipo"
        )
    
    with col2:
        periodo = st.selectbox(
            "Período",
            ["Todo el Año", "Último Mes", "Última Semana", "Personalizado"],
            key="periodo_reporte"
        )
        
        if periodo == "Personalizado":
            col_fecha1, col_fecha2 = st.columns(2)
            with col_fecha1:
                fecha_inicio = st.date_input("Desde")
            with col_fecha2:
                fecha_fin = st.date_input("Hasta")
    
    with col3:
        formato = st.selectbox(
            "Formato de salida",
            ["CSV", "Excel", "PDF", "Pantalla"],
            key="formato_reporte"
        )
    
    # Botón para generar reporte
    if st.button("🚀 Generar Reporte", type="primary", use_container_width=True):
        with st.spinner("🔄 Generando reporte..."):
            try:
                # Cargar datos primero
                cursos_sede = sheets_manager.load_courses_by_sede(user_sede, include_attendance=True)
                
                if not cursos_sede:
                    st.warning(f"ℹ️ No hay cursos para la sede {user_sede}")
                    return
                
                reporte_data = _generar_reporte(
                    reporte_tipo, 
                    user_sede, 
                    cursos_sede,
                    periodo
                )
                
                if reporte_data and len(reporte_data) > 0:
                    _mostrar_resultado_reporte(reporte_data, reporte_tipo, formato, user_sede)
                else:
                    st.warning("ℹ️ No hay datos para el reporte solicitado")
                    
            except Exception as e:
                st.error(f"❌ Error generando reporte: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

def _generar_reporte(tipo: str, sede: str, cursos_sede: Dict, periodo: str):
    """Genera diferentes tipos de reportes."""
    
    if not cursos_sede:
        return []
    
    reporte = []
    
    if tipo == "📊 Resumen General":
        for curso_nombre, curso_data in cursos_sede.items():
            total_estudiantes = len(curso_data.get("estudiantes", []))
            total_clases = len(curso_data.get("fechas", []))
            
            # Calcular asistencia promedio
            asistencias = curso_data.get("asistencias", {})
            porcentaje_promedio = 0
            
            if asistencias and total_estudiantes > 0 and total_clases > 0:
                total_presentes = 0
                for estudiante, asist_est in asistencias.items():
                    if isinstance(asist_est, dict):
                        presentes = sum(1 for estado in asist_est.values() 
                                      if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                        total_presentes += presentes
                    elif isinstance(asist_est, list):
                        presentes = sum(1 for estado in asist_est 
                                      if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                        total_presentes += presentes
                
                porcentaje_promedio = (total_presentes / (total_estudiantes * total_clases)) * 100
            
            reporte.append({
                "Curso": curso_nombre,
                "Estudiantes": total_estudiantes,
                "Clases Programadas": total_clases,
                "Asistencia Promedio": f"{porcentaje_promedio:.1f}%",
                "Profesor": curso_data.get("profesor", "N/A"),
                "Asignatura": curso_data.get("asignatura", "N/A")
            })
    
    elif tipo == "📋 Asistencia Detallada":
        for curso_nombre, curso_data in cursos_sede.items():
            for estudiante in curso_data.get("estudiantes", []):
                asistencia_est = curso_data.get("asistencias", {}).get(estudiante, {})
                total_clases = len(curso_data.get("fechas", []))
                
                # Calcular presentes
                if isinstance(asistencia_est, dict):
                    presentes = sum(1 for estado in asistencia_est.values() 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                elif isinstance(asistencia_est, list):
                    presentes = sum(1 for estado in asistencia_est 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                else:
                    presentes = 0
                
                ausentes = total_clases - presentes
                porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
                
                reporte.append({
                    "Curso": curso_nombre,
                    "Estudiante": estudiante,
                    "Clases Totales": total_clases,
                    "Presente": presentes,
                    "Ausente": ausentes,
                    "Asistencia %": round(porcentaje, 1),
                    "Estado": "🏆 Excelente" if porcentaje >= 85 else "✅ Adecuado" if porcentaje >= 70 else "⚠️ Bajo" if porcentaje >= 50 else "❌ Crítico"
                })
    
    elif tipo == "⚠️ Estudiantes Críticos (<70%)":
        for curso_nombre, curso_data in cursos_sede.items():
            for estudiante in curso_data.get("estudiantes", []):
                asistencia_est = curso_data.get("asistencias", {}).get(estudiante, {})
                total_clases = len(curso_data.get("fechas", []))
                
                # Calcular presentes
                if isinstance(asistencia_est, dict):
                    presentes = sum(1 for estado in asistencia_est.values() 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                elif isinstance(asistencia_est, list):
                    presentes = sum(1 for estado in asistencia_est 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                else:
                    presentes = 0
                
                porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
                
                if porcentaje < 70:
                    reporte.append({
                        "Curso": curso_nombre,
                        "Estudiante": estudiante,
                        "Asistencia %": f"{porcentaje:.1f}%",
                        "Presente/Ausente": f"{presentes}/{total_clases - presentes}",
                        "Profesor": curso_data.get("profesor", "N/A"),
                        "Clases Totales": total_clases
                    })
    
    elif tipo == "🏆 Top 10 Mejor Asistencia":
        # Primero recolectar todos
        todos_estudiantes = []
        for curso_nombre, curso_data in cursos_sede.items():
            for estudiante in curso_data.get("estudiantes", []):
                asistencia_est = curso_data.get("asistencias", {}).get(estudiante, {})
                total_clases = len(curso_data.get("fechas", []))
                
                # Calcular presentes
                if isinstance(asistencia_est, dict):
                    presentes = sum(1 for estado in asistencia_est.values() 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                elif isinstance(asistencia_est, list):
                    presentes = sum(1 for estado in asistencia_est 
                                  if estado in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"])
                else:
                    presentes = 0
                
                porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
                
                todos_estudiantes.append({
                    "Estudiante": estudiante,
                    "Curso": curso_nombre,
                    "Asistencia %": porcentaje,
                    "Presente": presentes,
                    "Total": total_clases
                })
        
        # Ordenar y tomar top 10
        todos_estudiantes.sort(key=lambda x: x["Asistencia %"], reverse=True)
        for i, est in enumerate(todos_estudiantes[:10], 1):
            reporte.append({
                "Posición": i,
                "Estudiante": est["Estudiante"],
                "Curso": est["Curso"],
                "Asistencia %": f"{est['Asistencia %']:.1f}%",
                "Presente/Total": f"{est['Presente']}/{est['Total']}"
            })
    
    elif tipo == "📅 Asistencia por Fecha":
        # Para cada curso, mostrar asistencia por fecha
        for curso_nombre, curso_data in cursos_sede.items():
            fechas = curso_data.get("fechas", [])
            estudiantes = curso_data.get("estudiantes", [])
            
            for fecha_idx, fecha in enumerate(fechas):
                presentes_fecha = 0
                
                for estudiante in estudiantes:
                    asistencia_est = curso_data.get("asistencias", {}).get(estudiante, {})
                    
                    # Verificar asistencia para esta fecha específica
                    if isinstance(asistencia_est, dict) and fecha in asistencia_est:
                        if asistencia_est[fecha] in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"]:
                            presentes_fecha += 1
                    elif isinstance(asistencia_est, list) and fecha_idx < len(asistencia_est):
                        if asistencia_est[fecha_idx] in [1.0, 1, "1.0", "1", True, "Presente", "presente", "PRESENTE"]:
                            presentes_fecha += 1
                
                porcentaje_fecha = (presentes_fecha / len(estudiantes) * 100) if estudiantes else 0
                
                reporte.append({
                    "Curso": curso_nombre,
                    "Fecha": fecha,
                    "Presentes": presentes_fecha,
                    "Total Estudiantes": len(estudiantes),
                    "Asistencia %": round(porcentaje_fecha, 1),
                    "Profesor": curso_data.get("profesor", "N/A")
                })
    
    return reporte

def _mostrar_resultado_reporte(reporte_data, tipo: str, formato: str, sede: str):
    """Muestra o exporta el resultado del reporte."""
    
    df = pd.DataFrame(reporte_data)
    
    st.success(f"✅ Reporte generado: {len(reporte_data)} registros")
    st.subheader(f"{tipo} - Sede {sede}")
    
    if formato == "Pantalla":
        st.dataframe(df, use_container_width=True, height=500)
    
    elif formato == "CSV":
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"reporte_{sede.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    elif formato == "Excel":
        excel_data = export_to_excel(df, f"reporte_{sede}")
        st.download_button(
            label="📊 Descargar Excel",
            data=excel_data,
            file_name=f"reporte_{sede.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    elif formato == "PDF":
        st.info("🔧 Función de PDF en desarrollo")

def _show_comunicaciones_tab(apoderados_sender: ApoderadosEmailSender, user_sede: str):
    """Tab de comunicaciones masivas usando ApoderadosEmailSender."""
    
    st.subheader("📧 Comunicaciones Masivas a Apoderados")
    st.info("💡 Envío de correos a apoderados de la sede. Personalice el mensaje según necesidad.")
    
    # Paso 1: Seleccionar filtros
    st.markdown("### Paso 1: Seleccionar Destinatarios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        filtro_curso = st.selectbox(
            "📚 Filtrar por curso:",
            ["Todos los cursos", "Curso específico"],
            key="filtro_curso_com"
        )
        
        if filtro_curso == "Curso específico":
            # Cargar cursos para el selector
            from utils.google_sheets import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager()
            cursos_sede = sheets_manager.load_courses_by_sede(user_sede)
            
            if cursos_sede:
                curso_especifico = st.selectbox(
                    "Seleccionar curso:",
                    list(cursos_sede.keys()),
                    key="curso_especifico_com"
                )
            else:
                st.warning("No hay cursos disponibles")
                return
    
    with col2:
        filtro_asistencia = st.selectbox(
            "📊 Filtrar por asistencia:",
            ["Todos los estudiantes", "Solo baja asistencia (<70%)", "Solo buena asistencia (≥85%)"],
            key="filtro_asistencia_com"
        )
    
    # Paso 2: Seleccionar plantilla
    st.markdown("### Paso 2: Seleccionar Plantilla")
    
    tipo_plantilla = st.selectbox(
        "📝 Tipo de mensaje:",
        ["Asistencia General", "Baja Asistencia", "Excelente Asistencia", "Personalizado"],
        key="tipo_plantilla"
    )
    
    # Generar plantilla base
    plantilla_base = apoderados_sender.generate_email_template(
        tipo="asistencia_general" if tipo_plantilla == "Asistencia General" 
        else "baja_asistencia" if tipo_plantilla == "Baja Asistencia"
        else "excelente_asistencia",
        sede=user_sede,
        fecha=datetime.now().strftime("%Y-%m-%d")
    )
    
    # Paso 3: Personalizar mensaje
    st.markdown("### Paso 3: Personalizar Mensaje")
    
    asunto = st.text_input(
        "📨 Asunto del email:",
        value=f"Información de Asistencia - Sede {user_sede} - {datetime.now().strftime('%Y-%m-%d')}",
        key="email_asunto_sede"
    )
    
    mensaje = st.text_area(
        "✍️ Contenido del email:",
        value=plantilla_base,
        height=300,
        key="email_contenido_sede"
    )
    
    # Variables disponibles
    with st.expander("🔤 Variables disponibles para personalización"):
        st.markdown("""
        **Variables que se reemplazarán automáticamente:**
        
        - `{{estudiante}}`: Nombre del estudiante
        - `{{apoderado}}`: Nombre del apoderado
        - `{{curso}}`: Nombre del curso
        - `{{porcentaje}}`: Porcentaje de asistencia
        - `{{total_clases}}`: Total de clases programadas
        - `{{presentes}}`: Clases presentes
        - `{{ausentes}}`: Clases ausentes
        - `{{sede}}`: Nombre de la sede
        - `{{recomendacion}}`: Recomendación según asistencia
        - `{{nivel}}`: Nivel de asistencia (CRITICO/REGULAR/EXCELENTE)
        - `{{fecha_reporte}}`: Fecha del reporte
        """)
    
    # Paso 4: Previsualización
    st.markdown("### Paso 4: Previsualizar")
    
    if st.button("👁️ Ver Previsualización", key="btn_preview_sede"):
        with st.expander("📄 Previsualización del Email", expanded=True):
            st.markdown(f"**Asunto:** {asunto}")
            
            # Datos de ejemplo para preview
            datos_ejemplo = {
                "estudiante": "Juan Pérez",
                "apoderado": "María González",
                "curso": "Matemáticas Avanzadas",
                "porcentaje": "85.5",
                "total_clases": "20",
                "presentes": "17",
                "ausentes": "3",
                "sede": user_sede,
                "recomendacion": "¡Excelente asistencia! Continúe así.",
                "nivel": "EXCELENTE",
                "fecha_reporte": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Reemplazar variables
            contenido_preview = mensaje
            for key, value in datos_ejemplo.items():
                contenido_preview = contenido_preview.replace(f"{{{{{key}}}}}", str(value))
            
            st.markdown(contenido_preview)
    
    # Paso 5: Envío
    st.markdown("### Paso 5: Confirmar y Enviar")
    
    col_test, col_send = st.columns(2)
    
    with col_test:
        if st.button("🧪 Probar Envío (Simulación)", use_container_width=True):
            with st.spinner("🧪 Probando envío..."):
                # Configurar filtros
                curso = curso_especifico if filtro_curso == "Curso específico" else None
                filtro_porc = 70 if filtro_asistencia == "Solo baja asistencia (<70%)" else 85 if filtro_asistencia == "Solo buena asistencia (≥85%)" else None
                
                # Ejecutar en modo prueba
                resultados = apoderados_sender.send_bulk_emails_to_apoderados(
                    sede=user_sede,
                    subject=asunto,
                    body_template=mensaje,
                    curso=curso,
                    filtro_porcentaje=filtro_porc,
                    test_mode=True
                )
                
                if resultados["success"]:
                    st.success(f"🧪 {resultados['message']}")
                    
                    if "preview" in resultados:
                        st.info(f"📧 Preview de primeros 3 emails:")
                        for preview in resultados["preview"]:
                            with st.expander(f"📨 {preview['estudiante']} → {preview['email']}"):
                                st.text(preview["preview"])
                else:
                    st.error(f"❌ {resultados['message']}")
    
    with col_send:
        confirmar = st.checkbox(
            "✅ Confirmo que deseo enviar estos emails",
            key="confirmar_envio_sede"
        )
        
        if confirmar and st.button("🚀 Iniciar Envío Masivo", type="primary", use_container_width=True):
            with st.spinner("📤 Enviando emails..."):
                # Configurar filtros
                curso = curso_especifico if filtro_curso == "Curso específico" else None
                filtro_porc = 70 if filtro_asistencia == "Solo baja asistencia (<70%)" else 85 if filtro_asistencia == "Solo buena asistencia (≥85%)" else None
                
                # Ejecutar envío real
                resultados = apoderados_sender.send_bulk_emails_to_apoderados(
                    sede=user_sede,
                    subject=asunto,
                    body_template=mensaje,
                    curso=curso,
                    filtro_porcentaje=filtro_porc
                )
                
                # Mostrar resultados
                if resultados["success"]:
                    st.success(f"✅ Envío completado: {resultados['sent']} enviados, {resultados['failed']} fallidos")
                    
                    # Métricas
                    col_sent, col_failed, col_total = st.columns(3)
                    with col_sent:
                        st.metric("📤 Enviados", resultados.get("sent", 0))
                    with col_failed:
                        st.metric("❌ Fallidos", resultados.get("failed", 0))
                    with col_total:
                        st.metric("📊 Total", resultados.get("total", 0))
                    
                    # Detalles de fallos
                    if resultados.get("failed", 0) > 0:
                        with st.expander("🔍 Ver detalles de fallos"):
                            for detalle in resultados.get("details", []):
                                if "Error" in detalle.get("status", "") or "Falló" in detalle.get("status", ""):
                                    st.error(f"**{detalle.get('estudiante', 'N/A')}**: {detalle.get('status', '')}")
                else:
                    st.error(f"❌ Error en envío: {resultados['message']}")

def _show_configuracion_tab(sheets_manager: GoogleSheetsManager, email_manager: EmailManager, user_sede: str):
    """Tab de configuración para equipo sede."""
    
    st.subheader("⚙️ Configuración de Sede")
    
    # Configuración de Google Sheets
    st.markdown("#### 📊 Configuración de Google Sheets")
    
    sheet_ids = sheets_manager.get_sheet_ids()
    if sheet_ids:
        col1, col2 = st.columns(2)
        with col1:
            status = "✅ Configurada" if sheet_ids.get("asistencia") else "❌ No configurada"
            st.metric("Hoja Asistencia", status)
        with col2:
            status = "✅ Configurada" if sheet_ids.get("clases") else "❌ No configurada"
            st.metric("Hoja Clases", status)
    else:
        st.warning("⚠️ No se encontraron configuraciones de Google Sheets")
    
    # Ver estructura actual de datos
    if st.button("🔍 Ver estructura de datos actual", key="btn_ver_estructura"):
        with st.spinner("🔄 Cargando datos..."):
            try:
                cursos_sede = sheets_manager.load_courses_by_sede(user_sede, include_attendance=True)
                
                if cursos_sede:
                    st.success(f"✅ {len(cursos_sede)} cursos cargados")
                    
                    for curso_nombre, curso_data in cursos_sede.items():
                        with st.expander(f"📊 {curso_nombre}"):
                            st.json(curso_data, expanded=False)
                else:
                    st.warning("ℹ️ No se cargaron cursos")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Configuración de Email
    st.markdown("#### 📧 Configuración de Email")
    
    if hasattr(email_manager, 'smtp_config') and email_manager.smtp_config:
        st.success("✅ Configuración de email activa")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Servidor:** {email_manager.smtp_config.get('server', 'N/A')}")
            st.info(f"**Puerto:** {email_manager.smtp_config.get('port', 'N/A')}")
        with col2:
            st.info(f"**Remitente:** {email_manager.smtp_config.get('sender', 'N/A')}")
        
        # Botón de prueba de email
        with st.expander("🧪 Probar Configuración de Email"):
            test_email = st.text_input("Email de prueba:", "test@example.com", key="test_email_input")
            
            if st.button("Enviar Email de Prueba", key="btn_test_email"):
                if email_manager.send_email(
                    to_email=test_email,
                    subject="Prueba de Configuración - Sistema CIMMA",
                    body="Este es un email de prueba para verificar la configuración."
                ):
                    st.success("✅ Email de prueba enviado correctamente")
                else:
                    st.error("❌ Error al enviar email de prueba")
    else:
        st.error("❌ Configuración de email no disponible")
    
    # Herramientas de mantenimiento
    st.markdown("#### 🛠️ Herramientas de Mantenimiento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Recargar Datos", use_container_width=True):
            sheets_manager.clear_cache("all")
            st.success("✅ Cache limpiado. Los datos se recargarán.")
            st.rerun()
    
    with col2:
        if st.button("📊 Probar Conexión", use_container_width=True):
            resultados = sheets_manager.test_connection()
            
            with st.expander("🔧 Resultados de la Prueba"):
                for key, value in resultados.items():
                    if key != "errors":
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                if resultados.get("errors"):
                    st.error("❌ Errores encontrados:")
                    for error in resultados["errors"]:
                        st.write(f"- {error}")