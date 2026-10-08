# pelota-cubana-serie65-data
Datos públicos de la Serie 65 para Pelota Cubana Stats. Actualización determinista, sin IA.

## Integridad de las actualizaciones

`audit.py` valida cada boxscore con el marcador del calendario, exige los bateadores y el pitcheo de ambos equipos y compara VB, C, H, 2B, 3B, HR y CI con los acumulados individuales cuando están todos los juegos del equipo. No suma las diferencias ni modifica anotaciones oficiales. Los lanzadores sin actividad ofensiva no requieren una fila en el acumulado de bateo.

`updateStatus.partial` y `snapshot.dataStatus` identifican consultas fallidas, equipos con datos anteriores, juegos pendientes y discrepancias. Un proceso parcial conserva los datos válidos y termina con error visible; no se declara completo solo porque pudo guardar un archivo. `teamUpdatedAt` conserva la fecha de recuperación de cada equipo. `merge.py` reemplaza bloques completos de un equipo y protege los más recientes, sin sumar acumulados ni conservar filas obsoletas de una misma tabla.

Se mantienen las consultas de 20:00, 22:00 y 02:00 en America/New_York. Las revisiones de recuperación de 20:30, 22:30 y 02:30 se ejecutan si la última actualización quedó parcial. La disponibilidad de la página oficial sigue siendo externa; los datos pendientes se muestran como tales y se reintentan. Pruebas antes de importar: `python -m unittest -v test_integrity.py`.

Revisión manual 2026-10-08: 32 juegos con resultado, 32 boxscores validados, cero diferencias en las siete estadísticas de bateo cotejadas. Recuperado el juego 27, Villa Clara 9–Mayabeque 6 (2026-10-07). Pérez Hemminges: 4 CI en Serie 65; el total previo de 97 se mantiene separado.
