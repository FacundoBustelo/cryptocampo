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

El total incluye auxiliares y mocks de prueba. El informe detallado compartido posteriormente por el usuario identificó las cuatro ramas sin cubrir de CCNFT; se analizan a continuación. Esta tabla conserva los resultados observados antes de añadir la nueva prueba de configuración de `claim`.

## Revisión de las cuatro ramas sin cubrir

| Función | Línea de `src/CCNFT.sol` | Rama sin ejecutar | Resultado de la revisión |
| --- | ---: | --- | --- |
| `trade` | 110 | Rechazo de `fundsToken == address(0)` | Inalcanzable mediante las funciones públicas actuales; se conserva la guarda defensiva. |
| `trade` | 111 | Rechazo de `feesCollector == address(0)` | Inalcanzable mediante las funciones públicas actuales; se conserva la guarda defensiva. |
| `claim` | 129 | Rechazo de `fundsToken == address(0)` | Alcanzable en un contrato nuevo con reclamos habilitados y lote permitido. Se añadió una prueba. |
| `claim` | 130 | Rechazo de `fundsCollector == address(0)` | Alcanzable en un contrato nuevo con token configurado, reclamos habilitados y lote permitido. Se añadió una prueba. |

En `trade`, la comprobación de existencia del NFT ocurre antes de estas guardas. La única función que emite NFTs es `buy`, que exige token y ambos colectores distintos de cero antes de emitir. Sus setters rechazan direcciones cero y ninguna otra función pone esas variables en cero. Por tanto, mientras exista un NFT emitido a través de la interfaz pública actual, el token de fondos y el colector de comisiones ya serán distintos de cero. El resultado se refiere a las comprobaciones de dirección cero; no demuestra liquidez ni buen comportamiento de cualquier ERC20 que el propietario configure.

En `claim`, las guardas de configuración aparecen antes de comprobar la existencia de los IDs. Por eso no se necesita un NFT emitido para alcanzar esos rechazos: basta habilitar reclamos y configurar un tamaño de lote válido. `testClaimRequiresCompleteConfiguration` usa únicamente despliegue y funciones públicas, comprueba ambos errores y confirma que, al completar la configuración, el siguiente rechazo es por ID inexistente. También comprueba que no quedaron suministro, nominales ni fondos en el contrato nuevo.

La suite ahora tiene 48 funciones de prueba. La nueva prueba todavía debe ejecutarse en CI; los 47 resultados aprobados y el 95,06 % de ramas registrados arriba corresponden al estado anterior. Si cubre las dos ramas previstas, se espera 79/81 (97,53 %) de ramas de CCNFT, con las dos restantes justificadas por el invariante anterior. Esto es una expectativa, no una medición nueva. No se modificaron los contratos ni se manipula almacenamiento para alcanzar estados imposibles.

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

La validación funcional y de metadatos y el reporte agregado de gas ya tienen evidencia de ejecución. El usuario informó éxito del workflow completo, que también ejecuta instalación, compilación y formato, y luego aportó la salida filtrada de las cuatro ramas pendientes. Ya se identificaron y revisaron las cuatro. Falta ejecutar la nueva prueba de configuración de `claim`, registrar el detalle del entorno y completar las mediciones de listas y lotes descritas en [la revisión de validación](validation.md). La fase 3 permanece en revisión hasta completar esos controles.

La fase 4 tiene las ocho pruebas aprobadas y los recursos locales validados; publicación IPFS, pinning y accesibilidad real siguen pendientes.
