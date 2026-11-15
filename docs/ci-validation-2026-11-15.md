# Evidencia de GitHub Actions — 15/11/2026

Fuente: salidas de `forge coverage` y `forge test --gas-report` compartidas por el usuario, quien también informó que el job completo `contratos` terminó en `succeeded`. No se consultó esa ejecución de GitHub desde esta sesión ni se dispone todavía del enlace de ejecución o del hash del commit de esa ejecución.

## Resultados observados en el registro

- Compilación de 46 archivos con Solidity 0.8.19: satisfactoria.
- Seis suites, 47 pruebas aprobadas, cero fallidas y cero omitidas.
- Cuatro pruebas fuzz, con 256 casos por prueba, aprobadas.
- Ocho pruebas de metadatos aprobadas.
- Recorrido de aceptación, atomicidad de cobros y quemas, permisos, límites, redondeo, publicaciones y conservación del nominal: sus pruebas figuran como `PASS`.

| Archivo | Líneas | Sentencias | Ramas | Funciones |
| --- | --- | --- | --- | --- |
| `src/BUSD.sol` | 100 % (2/2) | 100 % (1/1) | 100 % (0/0) | 100 % (1/1) |
| `src/CCNFT.sol` | 100 % (122/122) | 100 % (116/116) | 95,06 % (77/81) | 100 % (25/25) |
| `test/CCNFTBase.sol` | 100 % (60/60) | 100 % (65/65) | 100 % (1/1) | 100 % (9/9) |
| `test/mocks/Adversaries.sol` | 100 % (52/52) | 100 % (50/50) | 62,50 % (15/24) | 100 % (9/9) |
| Total del informe | 100 % (236/236) | 100 % (232/232) | 87,74 % (93/106) | 100 % (44/44) |

El total incluye auxiliares y mocks de prueba. Para CCNFT quedan cuatro ramas sin cubrir; se debe identificar cuáles son antes de decidir si requieren nuevas pruebas o una justificación de inalcanzabilidad. La tabla agregada no identifica esas ramas.

## Advertencias y gas

Forge informó que desactivó el optimizador y `viaIR` para medir cobertura. Las cifras de gas de este registro pertenecen a esa ejecución instrumentada y a funciones completas de prueba: no se usarán como costos de transacciones del contrato desplegado.

Solidity indicó que dos pruebas de BUSD podrían declararse `view`. Son advertencias de mutabilidad de funciones de prueba; no impidieron compilar ni aprobar las pruebas.

## Reporte de gas recibido

La ejecución de `forge test --gas-report` también finalizó con 47 pruebas aprobadas, cero fallos y cero omisiones, incluidas las cuatro fuzz de 256 casos. Indicó `No files changed, compilation skipped`: reutilizó los artefactos disponibles del runner. Se transcriben las estadísticas relevantes de ese reporte, en unidades de gas:

| Función de CCNFT | Mínimo | Media | Mediana | Máximo | Llamadas |
| --- | ---: | ---: | ---: | ---: | ---: |
| `buy` | 29097 | 609940 | 386146 | 1498834 | 1343 |
| `putOnSale` | 29064 | 88334 | 99805 | 119741 | 2512 |
| `trade` | 28784 | 117947 | 121039 | 160027 | 1016 |
| `claim` | 29194 | 250370 | 223004 | 529664 | 542 |
| `setMetadataURI` | 24135 | 60364 | 68042 | 93560 | 14 |

| Despliegue | Costo informado en gas | Tamaño informado en bytes |
| --- | ---: | ---: |
| BUSD | 640696 | 3035 |
| CCNFT | 3108828 | 14317 |

Estas estadísticas corresponden a llamadas de la suite y no distinguen en la tabla los lotes, la longitud de la lista, el estado de almacenamiento o las operaciones que revierten. No se interpretan los mínimos como costos de una operación exitosa, ni los máximos como cotas garantizadas. El reporte no demuestra todavía un límite operativo seguro de listas y lotes. Las cifras no son costos en ETH; no se consultaron precios de gas.

## Estado y pendientes

La validación funcional y de metadatos y el reporte agregado de gas ya tienen evidencia de ejecución. El usuario informó éxito del workflow completo, que también ejecuta instalación, compilación y formato. Falta registrar el detalle del entorno, identificar las cuatro ramas pendientes de CCNFT y completar las mediciones de listas y lotes descritas en [la revisión de validación](validation.md). Se preparó un cambio en el workflow para registrar el commit y las revisiones de bibliotecas y emitir cobertura `summary` y `debug`; ese cambio todavía debe ejecutarse. La fase 3 permanece en revisión hasta completar esos controles.

La fase 4 tiene las ocho pruebas aprobadas y los recursos locales validados; publicación IPFS, pinning y accesibilidad real siguen pendientes.
