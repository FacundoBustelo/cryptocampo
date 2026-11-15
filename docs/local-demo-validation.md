# Validación de la automatización local — 15/11/2026

**Fase 6 completada con evidencia real en dos redes Anvil nuevas.** La ejecución del usuario `20261115T191712781157Z` fue inspeccionada directamente: 52 recibos exitosos y 838 comprobaciones aprobadas. Ver [revisión y archivos originales conservados](evidence/local-demo-complete-2026-11-15/review.json).

 Los contratos, sus reglas económicas y las versiones fijadas se conservaron. La [nueva revisión de fase 5](evidence/phase5-recheck-2026-11-15/review.json) confirmó los 24 hashes de los archivos históricos, los 20 controles aprobados y las fuentes originales frente al commit validado, sin sobrescribir la evidencia anterior.

La comprobación inicial del agente mediante `python3 tools/validate-system.py --output-dir .tools/validation/phase6-reviewed` terminó con código 1: **19 de 21 controles aprobados**; dos controles quedaron bloqueados por permisos del entorno. Se conservó una copia completa en [el directorio de evidencia](evidence/local-demo-validation-2026-11-15/result.json), con [revisión y hashes de sus archivos](evidence/local-demo-validation-2026-11-15/review.json).

| Control | Resultado observado |
| --- | --- |
| Compilación y formato | Aprobados con Solidity 0.8.19; compilación optimizada restaurada después de cobertura. |
| Pruebas Solidity | 49 aprobadas, cero fallos/omisiones: las 48 originales y una prueba agrupada con 15 escenarios de scripts. Cuatro fuzz de 256 casos cada una. |
| Pruebas Python | 38 aprobadas: 20 de metadatos, seis de validación y 12 del ejecutor de demostración. |
| Cobertura CCNFT | 122/122 líneas, 116/116 sentencias, 25/25 funciones y 79/81 ramas. Se mantienen las dos guardas inalcanzables justificadas en fase 5. |
| Reporte agregado de gas | Aprobado. Incluye ahora la prueba de scripts; no se interpreta su gas de pruebas como un recibo de Anvil. |
| Matriz de gas | Intentada y bloqueada al crear un socket: `PermissionError: [Errno 1] Operation not permitted`. La evidencia histórica de 35 mediciones permanece intacta. |
| Demostración completa | Dos intentos independientes bloqueados al crear sockets; cero transacciones reales nuevas. Ambos conservaron versiones, revisiones, hashes, comandos, logs y errores. |
| Makefile y evidencia | Comandos por etapa revisados con `make -n`; scripts y Makefile incluidos en los hashes; fallos y recibos parciales cubiertos por pruebas Python. |

La prueba agrupada comprueba configuración y secuencia de scripts en la VM de Forge, incluida la conservación del segundo NFT y la reserva del colector. No acredita que las transacciones hayan sido publicadas en un nodo Anvil. Las pruebas del ejecutor con respuestas controladas verifican que los errores, recibos parciales y estados incorrectos se detectan y conservan; tampoco sustituyen una ejecución real.

El workflow `contracts.yml` está preparado para repetir ambos recorridos y subir los resultados incluso ante fallos. **No se ejecutó ni se inspeccionó una nueva ejecución remota de fase 6 en esta sesión.** El criterio de cierre exige dos informes reales de Anvil, locales o de CI, con 26 recibos exitosos en cada red, todas las verificaciones aprobadas, A −84, B −16,2, fondos +95 y comisiones +5,2 BUSD; un NFT de A; `totalValue = 100 BUSD` y saldo del colector de 105 BUSD. La ejecución local revisada satisface este criterio. Las autorizaciones deben quedar en cero; un futuro reclamo requiere una nueva aprobación.

Los [comandos y el fundamento académico](local-demo.md) permiten ejecutar `make demo` o cada etapa. Sepolia, Etherscan y las capturas de MetaMask permanecen en fase 7.

## Ejecución del usuario y corrección del getter vacío

Se inspeccionó directamente `.tools/validation/20261115T191247261614Z/`: **20 de 21 controles aprobados**, incluidas las 35 mediciones de gas en Anvil. En ambos intentos de demostración se confirmaron dos despliegues exitosos; el verificador detuvo el recorrido al consultar `listTokensOnSale(0)` sobre la lista vacía. Cast devolvió `error code 3: execution reverted, data: "0x"`. El verificador exigía incorrectamente `Panic(0x32)`: el getter público generado por Solidity 0.8.19 devuelve datos vacíos para ese índice.

Se corrigió exclusivamente la herramienta y sus pruebas. Ahora exige salida no exitosa, error RPC de reversión y datos exactamente `0x` para este getter. Las consultas de propietario y URI de un NFT quemado siguen exigiendo su motivo ABI exacto. Una respuesta de red, un éxito o una reversión diferente se rechazan. Las 39 pruebas Python aprobaron y las dos respuestas reales conservadas pasan la comprobación corregida. La [evidencia de la ejecución y de la corrección](evidence/local-demo-getter-fix-2026-11-15/review.json) se conserva separadamente.

Ese intento quedó pendiente de repetir `make demo` para verificar las dos secuencias completas después de la corrección. La repetición satisfactoria se revisa a continuación; los contratos y scripts Solidity no se modificaron.

## Cierre con dos demostraciones reales

El usuario ejecutó `make demo` desde su terminal normal. Se inspeccionó directamente `.tools/demo/20261115T191712781157Z/` y se conservó una copia íntegra bajo [la evidencia nueva](evidence/local-demo-complete-2026-11-15/result.json), separada de los intentos anteriores. La [revisión](evidence/local-demo-complete-2026-11-15/review.json) registra hashes de los 723 archivos originales, fuentes ejecutadas, redes, cuentas, direcciones, recibos y resultados.

Cada recorrido aprobó las once etapas, con 26 recibos exitosos y 419 comprobaciones. Se contrastaron los recibos con sus archivos de broadcast y las consultas finales con sus logs Cast originales. Los procesos Anvil tienen PID, puerto y génesis diferentes; ambos finalizaron con código 0 y el estado final coincide. Forge, Cast y Anvil son 1.4.4, con la revisión fijada; OpenZeppelin y forge-std coinciden con sus revisiones previstas y sus árboles están limpios. Los hashes de las fuentes ejecutadas coincidían con los archivos del workspace antes de actualizar esta documentación. El commit base sigue siendo `d7a17d9`; la implementación local aún contiene cambios sin commit, identificados mediante hashes y diff en la evidencia.

| Resultado | Red 1 | Red 2 |
| --- | ---: | ---: |
| Recibos exitosos | 26 | 26 |
| Comprobaciones aprobadas | 419 | 419 |
| Saldo A | 916 BUSD | 916 BUSD |
| Saldo B | 983,8 BUSD | 983,8 BUSD |
| Saldo fondos | 105 BUSD | 105 BUSD |
| Saldo comisiones | 5,2 BUSD | 5,2 BUSD |
| Variaciones A / B / fondos / comisiones | −84 / −16,2 / +95 / +5,2 BUSD | −84 / −16,2 / +95 / +5,2 BUSD |
| NFT conservado | ID 1 en A | ID 1 en A |
| NFT reclamado | ID 0 quemado | ID 0 quemado |
| Suministro / nominal vigente | 1 / 100 BUSD | 1 / 100 BUSD |

Se comprobaron las autorizaciones consumidas, lista de ventas vacía, nominal y publicación eliminados del NFT quemado, reversiones de su propietario y URI y conservación de la URI IPFS definitiva en el NFT de A. El colector conserva 105 BUSD; un futuro reclamo del NFT conservado requiere renovar su autorización exacta por 105 BUSD.

**Controles de cierre satisfechos; fase 6 completada para la demostración local.** La aceptación combina los 20 controles aprobados de la validación anterior, las 39 pruebas Python posteriores a la corrección y esta repetición independiente de las dos demostraciones. Solo cambiaron la herramienta Python y sus pruebas entre aquella validación y esta demostración; contratos, scripts y pruebas Solidity coincidían. No se presenta el intento anterior como una ejecución integral de 21/21 controles ni se afirma un nuevo workflow remoto. Sepolia, verificación en Etherscan y capturas de MetaMask continúan en fase 7.
