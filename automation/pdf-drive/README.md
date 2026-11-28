# PDF diarios de Pelota Cubana Stats

Programa de Google Apps Script, sin IA. Instalación verificada directamente en Google el 27 de noviembre de 2026: proyecto creado el 10 de noviembre, un activador de sincronizarPDF cada 15 minutos y ejecuciones programadas recientes.

Proyecto: https://script.google.com/home/projects/1Dvx1Db5kUu7uOAlUqVBA6YnRgqxlrst65gOwCNBSq3V2AhHzqWLPde9u

## Incidencia y recuperación del 27 de noviembre

Un proceso paralelo de agente movió los PDF originales a una carpeta de copias y creó archivos numerados. El script conservó sus referencias y rechazó actualizaciones con «El PDF cambió de identidad o carpeta». Se restauraron los nueve archivos originales del 28 de noviembre a su carpeta, conservando los IDs y nombres esperados y reemplazando su contenido por las versiones verificadas más recientes. Las copias numeradas quedaron archivadas.

No mover ni renombrar los archivos gestionados por este script, ni sustituirlos por archivos con otros IDs. Un estado de ejecución Completed no garantiza entrega completa: revisar updated, pending y complete en los logs/PCU_ESTADO.


## Instalación en una cuenta nueva (no repetir en el proyecto existente)

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

Validación local: sintaxis Node y 18 comprobaciones, con boxscore real 240 y modelo 248 del 11 de noviembre de 2026. Las ejecuciones programadas y su activador se comprobaron directamente en Google el 27 de noviembre. La presencia del código en GitHub no debe usarse para inferir el estado operativo: comprobar los logs del proyecto.
