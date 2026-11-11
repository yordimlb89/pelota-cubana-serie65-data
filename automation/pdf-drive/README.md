# PDF diarios de Pelota Cubana Stats

Programa de Google Apps Script, sin IA. Estado: código preparado y validado; falta instalarlo y autorizarlo en la cuenta propietaria de Drive.

## Instalación

1. Crear un proyecto privado en Google Apps Script con la cuenta propietaria de la carpeta.
2. Copiar Code.gs. En Configuración del proyecto, mostrar appsscript.json y copiar el manifiesto incluido.
3. Ejecutar instalar y completar la autorización de Google. Requiere acceso a Drive, solicitudes externas y creación de activadores. El programa limita los archivos a la carpeta configurada, aunque Google concede un permiso de Drive más amplio.
4. Verificar un único activador de sincronizarPDF cada 15 minutos y revisar estado y Ejecuciones.
5. Verificar una subida real y su checksum antes de pausar la automatización anterior de ChatGPT.

## Comportamiento

- Comprueba hoy y mañana en horario de Miami; espera el parte y todos los boxscores de la jornada anterior.
- Valida bateo/pitcheo y conciliación de carreras e hits, multihits, identidad de juego y calendario cubano.
- Descarga PDF ya generado por código en pelotacubanastats.com.
- Crea carpetas YYYY-MM-DD bajo la carpeta autorizada y conserva permisos heredados.
- Reemplaza contenidos de archivos existentes sin cambiar sus identificadores ni enlaces. No modifica permisos.
- Hasta dos PDF por ejecución, con rotación y reintento en ejecuciones posteriores. La primera tanda de ocho necesita varias ejecuciones.
- Conserva previas cuando comienza la jornada; no las regenera con estadísticas posteriores al inicio.
- Guarda hashes y estado en propiedades privadas del script. No añade manifiestos a la carpeta compartida.
- pausar detiene nuevas subidas; instalar reanuda sin duplicar el activador.

No es un servicio en tiempo real. La disponibilidad depende del parte, los datos de origen, las cuotas y el horario aproximado de los activadores de Google. Consultar PCU_ESTADO mediante estado para pendientes y errores.

Validación local: sintaxis Node y 18 comprobaciones, con boxscore real 240 y modelo 248 del 11 de noviembre de 2026. La prueba autorizada dentro de Google todavía está pendiente.
