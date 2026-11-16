# Validación de preparación de Sepolia — 15/11/2026

**Fase 7 completada dentro del alcance académico, con limitación visual documentada.** Se revisaron el recorrido público, ambos contratos verificados y las dos capturas originales. BUSD muestra 916 en A y red Sepolia; CCNFT muestra el ID 1 y ERC721 con la dirección abreviada esperada. MetaMask no renderiza el certificado y esa limitación se declara expresamente. Ver [resultado final y capturas](sepolia-results.md). La comprobación pública `20261115T233639275750Z` aprobó 55 controles y conserva los 26 recibos exitosos de las once etapas. Las secciones siguientes son antecedentes de preparación y correcciones.

La revisión de fase 6 volvió a comprobar sus **723 archivos originales**: ninguno falta ni difiere de su hash. BUSD y CCNFT mantienen los mismos hashes de fuente usados en aquella demostración. Se conservan las dos redes históricas con 26 recibos y 419 comprobaciones por red. El cierre histórico permanece vigente. Los scripts adaptados completaron después ambos recorridos en la ejecución del usuario descrita a continuación.

## Validación integral del usuario

Se inspeccionó directamente `.tools/validation/20261115T195559010106Z`, ejecutado por el usuario: **21/21 controles aprobados**, 49 pruebas Solidity, 57 Python, cobertura conservada, reporte de gas y **35 mediciones reales**. Los hashes de todas las fuentes coinciden con los archivos actuales. Las dos redes Anvil completaron once etapas cada una, con **52 recibos exitosos y 838 comprobaciones** en total. Ambas conservaron los deltas económicos acordados y el segundo NFT de A. Se preservaron los 747 archivos originales y se contrastaron sus hashes. Ver [revisión del resultado](evidence/sepolia-local-complete-2026-11-15/review.json) e [informe íntegro](evidence/sepolia-local-complete-2026-11-15/result.json).

Este resultado satisfizo la repetición integral local de los scripts adaptados. En ese momento, Sepolia, Etherscan y las capturas de MetaMask seguían pendientes; se completaron después y están en el resultado final. No es necesario repetir `make validate` para continuar con la preparación de los recursos.

## Antecedente: comprobaciones de la sesión restringida

Se ejecutó `python3 tools/validate-system.py --output-dir docs/evidence/sepolia-preparation-2026-11-15/final`. El [informe completo](evidence/sepolia-preparation-2026-11-15/final/result.json) registra comandos, códigos, versiones, revisiones, hashes y logs. Los controles de registro del commit y árbol se ejecutaron correctamente; el árbol contiene los cambios de esta implementación y no se creó un commit.

| Comprobación | Resultado |
| --- | --- |
| Compilación y formato | Aprobados, Solidity 0.8.19, optimizador 200, Paris |
| Pruebas Solidity | 49 aprobadas; cuatro fuzz con 256 casos cada una |
| Pruebas Python | 57 aprobadas, incluidas 18 nuevas del perfil público |
| Cobertura CCNFT | 122/122 líneas, 116/116 sentencias, 25/25 funciones, 79/81 ramas |
| Reporte agregado de gas | Aprobado; compilación optimizada restaurada después de cobertura |
| Versiones y bibliotecas | Foundry 1.4.4, OpenZeppelin 4.5.0 y forge-std 1.9.7; revisiones fijadas, bibliotecas limpias |
| Matriz de gas real en Anvil | Bloqueada por permisos de sockets; ninguna medición nueva |
| Dos demostraciones Anvil | Ambas intentadas y bloqueadas al crear socket, antes de iniciar nodo o desplegar |
| Diagnóstico Sepolia sin recursos | Rechazo esperado: enumera únicamente nombres de las doce variables pendientes |

El validador registra **19/21 controles aprobados** y estado global `failed`, porque gas-matrix y local-demo no pudieron ejecutarse. Los logs conservan `PermissionError: [Errno 1] Operation not permitted`. Esto es una limitación de esta sesión; no se transformó en un éxito ni se reemplazó por la evidencia histórica. El primer ensayo de validación también se conserva en la carpeta padre; `final/` corresponde a los archivos actuales, incluido el filtrado final de secretos y el almacenamiento privado de Forge separado de la evidencia.

Las 18 pruebas Python nuevas cubren configuración literal e incompleta, red equivocada, direcciones repetidas, claves inválidas, HTTPS, filtrado de claves/RPC/API, normalización de CREATE, interrupción antes de guardar hashes, nonces pendientes, recibos fallidos, transacciones sustituidas, reorganizaciones, prefijos confirmados, intención persistida, comprobaciones repetidas sin duplicar deltas y validación de la respuesta de Etherscan. La prueba Solidity de scripts conserva el recorrido local y añade perfil incorrecto, clave que no corresponde al firmante, nonce cambiado, bytecode de creación incorrecto, despliegues con clave de entorno y publicación de una transferencia al destino autorizado. Los dobles RPC comprueban recuperación y rechazos; no equivalen a un envío real en Sepolia.

La compilación conserva las advertencias de estilo de Foundry; el resumen de cobertura mantiene justificadas las dos guardas de `trade` inalcanzables por la interfaz pública. No se modificaron contratos ni reglas económicas.

## Próximas comprobaciones necesarias

La validación integral local ya fue completada por el usuario.

Después de completar `.env` y financiar admin, A, B y fondos con ETH de prueba:

```bash
make sepolia-doctor
make sepolia-demo
make sepolia-check
```

Ante una interrupción, usar `make sepolia-reconcile` y conservar el mismo archivo de estado antes de continuar. La guía incluye importación BUSD/CCNFT en MetaMask, capturas y enlaces requeridos.

**Cierre actualizado:** las dos capturas reales ya fueron revisadas y archivadas; la limitación visual está documentada. La fase 7 está completada dentro del alcance académico. Los recursos y sus secretos se configuran localmente; `.env.example` contiene solo los nombres.

## Corrección de comisiones del primer intento público

Se revisaron directamente el log y el plan de `20261115T211530087585Z`. La simulación pasó, pero el envío fue rechazado por una prioridad mayor que el máximo de gas. El broadcast conservado no contiene recibos ni hashes pendientes. Se corrigió el cálculo de tarifas EIP-1559 y se fijan ambas comisiones explícitamente al publicar. Pasaron **64 pruebas Python** y formato; las nuevas pruebas reproducen gas sugerido muy bajo frente a prioridad alta, comprueban los argumentos reales de Forge y la recuperación del plan sin aceptar cambios ajenos ni nonces ocupados. Los contratos y scripts Solidity conservan sus hashes; el control integral previo de 21/21 sigue siendo evidencia de la versión anterior del ejecutor.

La sesión del agente no pudo consultar `eth_chainId` por restricción de conexión. La reconciliación real y el reintento quedan para la terminal del usuario, conservando el estado. No se afirma un despliegue público exitoso. Ver [diagnóstico y pruebas](evidence/sepolia-fee-fix-2026-11-15/review.json).

## Corrección del límite de gas y recuperación explícita

El usuario aportó el recibo del segundo intento: estado fallido y 832.904 gas consumidos, idénticos al límite del broadcast. El presupuesto del ejecutor había utilizado 4.165.136 unidades estimadas por RPC. Se corrigió la publicación para que Forge 1.4.4 estime por RPC antes del envío, con multiplicador del 150 %. Se añadió `sepolia-recover-deploy FAILED_TX=...`, que verifica transacción, recibo canónico, ausencia de código, nonces y simulaciones antes de preparar un reintento. El estado anterior y el recibo se conservan; los recibos exitosos y operaciones económicas quedan fuera de esa recuperación.

Aprobaron **70 pruebas Python**, formato y `git diff --check`. Las pruebas nuevas cubren recuperación de nonces 4/5 a 5/6, idempotencia, persistencia del recibo fallido, rechazo de éxito o reorganización, nonces ocupados, código existente, cambios de fuentes y errores de estimación. Los contratos y scripts Solidity no cambiaron. El mecanismo RPC se contrastó con el código fuente de la versión fijada de Forge; no se declara un reintento público exitoso. La ejecución de recuperación desde la sesión del agente quedó bloqueada al consultar `eth_chainId`, sin modificar el estado real del usuario. Ver [evidencia](evidence/sepolia-rpc-gas-fix-2026-11-15/review.json).

## Verificación pública confirmada

La ejecución del usuario `20261115T214054458364Z` aprobó `sepolia-verify` para BUSD y CCNFT. Se inspeccionaron el informe, los logs y ambas respuestas `getsourcecode` conservadas: nombres coincidentes, compilador `v0.8.19+commit.7dd6d404`, optimización habilitada con 200 runs, EVM Paris y argumentos de constructor vacíos. Ver [evidencia preservada](evidence/sepolia-verified-2026-11-15/review.json). La configuración, el recorrido económico y las capturas de MetaMask siguen pendientes; la fase 7 permanece iniciada.

## Verificación de cierre documental

Se compararon los hashes de los dos PNG copiados con los originales proporcionados por el usuario y se reabrieron para inspección visual. Se revisaron el informe final, las once etapas, 26 recibos exitosos, verificaciones Etherscan, saldos, autorizaciones y IDs conservado/quemado. El manifiesto de las fuentes ejecutadas continúa coincidiendo: este cierre añade documentos y capturas sin cambiar contratos, scripts, parámetros ni URI. No se repitieron transacciones ni se declaró una nueva comprobación HTTP desde la sesión restringida.
