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

## Prueba posterior a la restauración

El 27 de noviembre a las 23:02:42 (America/New_York), una ejecución de sincronizarPDF iniciada desde el editor terminó con updated=[344,334], pending=[] y complete=[]. La cuota de dos PDF por ejecución explica que no marque aún toda la tanda como completa. El proceso validó los archivos restaurados y actualizó sus propiedades de seguimiento; si los bytes coinciden, no vuelve a subirlos. Se verificaron nueve PDF únicos con sus IDs originales en la carpeta del 28. La tarea paralela de ChatGPT «Guardar notas de juego en Drive» quedó pausada para evitar interferencias; el activador de Google cada 15 minutos sigue activo. No se ha cambiado el código del script.

## Horario vigente

Desde las 17:00 (America/New_York) se inicia el ciclo para las notas del día siguiente. Continúa cada 15 minutos, también después de medianoche si sigue pendiente y la jornada destinataria no ha comenzado. Conserva el avance por juego entre ejecuciones. Espera el parte y los boxscores validados de los juegos terminados. Solo cierra cuando todos los PDF esperados han sido procesados y se comprueban en Drive por ID, carpeta, MIME, tamaño y SHA-256. Un fallo no marca el ciclo completo.

Después del cierre, las invocaciones del activador retornan sin consultas al sitio o Drive hasta el ciclo de las 17:00 siguiente. El activador no se borra ni se duplica. La tarea paralela de agente permanece pausada.

Pruebas de lógica: antes de 17:00 inactivo; inicio a las 17:00; continuación después de medianoche; cierre con entrega verificada; ninguna consulta tras cierre; fallo de Drive impide cierre y permite reintento. Cambio guardado en el proyecto activo de Google y en GitHub. Las previas nunca se regeneran después de iniciarse la jornada destinataria.
