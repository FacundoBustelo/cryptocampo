# Fase 5 — Requisitos, pruebas y evidencia

**Fase 5 completada el 15/11/2026 con evidencia de CI revisada.** El artefacto de la [ejecución 43748041038, intento 1](https://github.com/FacundoBustelo/cryptocampo/actions/runs/43748041038), sobre `d7a17d9b2019243c8cecddd385574c0eef22f9fb`, acredita los 20 controles aprobados: compilación, formato, 48 pruebas Solidity sin fallos ni omisiones, cuatro fuzz de 256 casos cada una, 26 pruebas Python (20 del verificador y seis de las herramientas de validación), cobertura, reporte agregado de gas y **35 mediciones exitosas en Anvil**. El recorrido termina con nominal de **100 BUSD**. CCNFT conserva 100 % de líneas, sentencias y funciones y 79/81 ramas.

El [informe de la ejecución local previa](evidence/system-validation-2026-11-15/result.json) registra comandos, códigos, tiempos UTC, plataforma, Python y hashes SHA-256 de fuentes, pruebas, herramientas, configuración, recursos y workflow. Los archivos vecinos contienen las salidas completas. Se midió el árbol de trabajo sobre `e38d9f0967abf869377cb7b3a479322fd175fcce` con los cambios identificados por diff y hashes; no se atribuye la ejecución a un commit nuevo ni a CI.

## Cierre verificado en CI

Se conservaron sin modificar los 24 archivos del ZIP `contracts-validation-43748041038-1.zip` en [el directorio de evidencia](evidence/ci-validation-43748041038-1/ci/result.json). La [revisión del artefacto](evidence/ci-validation-43748041038-1/review.json) registra el enlace, commit, intento, SHA-256 del ZIP y de cada archivo extraído, comprobaciones y límites. La validación del runner transcurrió entre **18:40:23 y 18:40:45 UTC del 15/11/2026**. El `status` final es `passed`, con los 20 códigos de salida en cero.

Se comprobaron los 23 hashes de archivos del informe contra las versiones guardadas en el commit `d7a17d9`, incluidos contratos, pruebas, herramientas, configuración, recursos y workflow. Los logs de diff, árbol de trabajo y bibliotecas están vacíos. Foundry/Forge/Anvil/Cast son 1.4.4, con revisión `05794498bf47257b144e2e2789a1d5bf8566be0e`; OpenZeppelin y forge-std coinciden con las revisiones fijadas. La compilación y la matriz verifican Solidity 0.8.19, Paris y optimizador con 200 runs.

| Control revisado en el artefacto | Resultado |
| --- | --- |
| [Pruebas Solidity](evidence/ci-validation-43748041038-1/ci/solidity-tests.txt) | 48 aprobadas, cero fallos y cero omisiones; incluye aceptación y cuatro fuzz de 256 casos. |
| [Pruebas Python](evidence/ci-validation-43748041038-1/ci/python-tests.txt) | 26 aprobadas. |
| [Cobertura y guardas pendientes](evidence/ci-validation-43748041038-1/ci/coverage-summary.txt) | CCNFT: líneas 122/122, sentencias 116/116, funciones 25/25 y ramas 79/81; mismas dos guardas inalcanzables justificadas. |
| [Reporte agregado de gas](evidence/ci-validation-43748041038-1/ci/gas-report.txt) | Aprobado después de restaurar la compilación optimizada. |
| [Matriz de gas](evidence/ci-validation-43748041038-1/ci/gas-matrix.txt) y [JSON](evidence/ci-validation-43748041038-1/ci/gas-scenarios.json) | 35 transacciones exitosas, con exactamente los escenarios esperados para listas 1/10/100 y lotes 1/10; las 35 cifras coinciden con las históricas. |

El mayor recibo sigue siendo la compra de diez NFTs, **1.475.810 gas**. El reclamo de diez publicados al final de una lista de cien consume **1.220.864 gas**. El bloqueo local de sockets queda resuelto para el cierre mediante esta ejecución remota; su registro previo permanece intacto.

La procedencia de la verificación es el ZIP aportado por el usuario, que se inspeccionó directamente. La página remota no se pudo recuperar desde esta sesión (`Cache miss`); no se afirma haber inspeccionado sus logs desde GitHub ni el estado global del workflow por API. El ID, intento y SHA proceden del informe del runner y coinciden con el enlace y el repositorio local. Esta ejecución valida metadatos locales y no repite descargas IPFS ni el escenario de URI de fase 4.

## Matriz de requisitos

Las referencias académicas corresponden al material original conservado fuera de este repositorio: `Consignas-ProyectoFinal/src/CCNFT.sol`, `Consignas-ProyectoFinal/test/CCNFT.t.sol`, `Modulo3`, `Modulo 2` y `Modulo 4`. El resumen de la materia y las reglas del TP se conservan en la carpeta académica superior. Las pruebas entregadas por la cátedra tenían cuerpos vacíos. Los escenarios adicionales se derivan de las reglas adoptadas y de los comentarios de la plantilla; no se presentan como pruebas ya resueltas en clase.

Los nombres de prueba de cada fila aparecen como `PASS` en el [log Solidity](evidence/system-validation-2026-11-15/solidity-tests.txt). Las mismas 48 pruebas se repitieron satisfactoriamente en el [log de CI](evidence/ci-validation-43748041038-1/ci/solidity-tests.txt). Cada prueba recibe contratos y actores nuevos mediante `setUp`; los pasos internos de una prueba no dependen de la ejecución de otra.

| Requisito | Fundamento de la cursada o regla adoptada | Pruebas ejecutadas | Resultado nuevo |
| --- | --- | --- | --- |
| Administración, tipos, interfaces y estado inicial | Plantilla: setters y `Ownable`; Módulo 2 temas 2–4, 8–11; Módulo 4 temas 3–9 | [CCNFTAdmin.t.sol](../test/CCNFTAdmin.t.sol): `testInitialStateAndInterfaces`, `testAllSettersAndFullProfitRange`, `testEverySetterRequiresOwner`, `testInvalidSetterInputs` | PASS: permisos de los 13 setters, límites, direcciones y tipos conservados, sin restringir el rango `uint32` del beneficio. |
| Habilitaciones y configuración | Plantilla: `canBuy`, `canTrade`, `canClaim`, token y colectores; Módulo 2 temas 3 y 8 | Administración: `testDisabledOperations`, `testBuyRequiresCompleteConfiguration`, `testClaimRequiresCompleteConfiguration` | PASS: rechazos esperados y ausencia de emisiones o pagos parciales. |
| Compra individual, lotes y límites | Plantilla: `buy`, nominal permitido y máximo; Módulo 2 temas 4 y 6; regla del TP: nominal vigente | [CCNFTOperations.t.sol](../test/CCNFTOperations.t.sol): `testAcceptanceBalancesEventsAndFinalNominal`, `testBuyAndClaimAtExactBatchAndNominalLimits`, `testInvalidBuyInputsAndZeroCap`, `testLoweringCapDoesNotPreventClaimOrChangeOutstandingNominal` | PASS: lotes 1 y 10, extremos rechazados, propiedad, capacidad y nominal. |
| Publicación y actualización sin duplicados | Plantilla: struct, mapping y lista; Módulo 2 temas 4–6, búsqueda y swap/pop | Operaciones: `testListingUpdatesWithoutDuplicatesAndSwapPopRemovesAllPositions`, `testPublicationAndTradeRejections` | PASS: precio positivo, propietario, IDs existentes, actualización y eliminación en todas las posiciones. |
| Reventa y conservación del nominal | Plantilla: `trade` y transferencia interna; regla del TP: comisión sobre precio publicado | Operaciones: aceptación, publicaciones y rechazos; [CCNFTFuzz.t.sol](../test/CCNFTFuzz.t.sol): `testFuzzTradeFormulaPreservesNominal` | PASS: cobros, dueño, limpieza y nominal; rechaza compra propia, sin publicación o por ID inexistente. |
| Reclamo individual, mixto y por lotes | Plantilla: `claim`, quema y beneficio desde colector; Módulo 4 ERC20/ERC721 | Operaciones: `testClaimMixedNominalsAndPublishedTokens`, `testBuyAndClaimAtExactBatchAndNominalLimits`, `testBurnedIdsCannotBeUsedOrReissued`; fuzz: `testFuzzClaimFormulaFullUint32Profit` | PASS: beneficio sobre suma, quema, limpieza, enumeración, IDs irrepetibles y reducción del nominal. |
| Comisiones, redondeo y contabilidad | Plantilla: puntos básicos; reglas del TP sobre totales y precio de reventa | Operaciones: `testZeroFeesAndProfit`, `testOneHundredPercentFeesAndProfitAboveOneHundredPercent`, `testRoundingUsesBatchTotalsInMinimumUnits`; fuzz: `testFuzzBuyFormula`, `testFuzzNominalConservationAcrossLifecycle` | PASS: comisión 0 y 100 %, truncamiento, beneficio superior al 100 % y conservación a lo largo del recorrido. |
| Saldo, autorización y atomicidad de pagos | Módulo 4: `approve`/`transferFrom`; plantilla y reglas: reversión completa | [CCNFTSecurity.t.sol](../test/CCNFTSecurity.t.sol): las seis pruebas de saldo/autorización de compra, reventa y reclamo, y `testFalseERC20OnBothBuyChargesAndClaim`, `testFalseERC20OnBothTradeCharges` | PASS: fallos del principal y segundo cobro restauran saldos, allowance, dueños, IDs, nominales y publicaciones. |
| Atomicidad de lotes e IDs inválidos | Módulo 2: arrays y bucles; plantilla y reglas: propietario, existencia y reversión | Operaciones: `testClaimInvalidBatchesThirdPartyAndDuplicatesAreAtomic`, `testClaimWithAnotherOwnersTokenRestoresEarlierBurn`, `testOverflowRevertsWithoutPartialState` | PASS: ID repetido, inexistente o ajeno después de una quema, lotes vacíos/excesivos y overflow no dejan cambios parciales. |
| Callbacks y reentrada | Plantilla: `ReentrancyGuard`; ampliación de pruebas para llamadas externas ERC20/ERC721 | Seguridad: `testERC20CallbacksCannotReenterAnyOperation`, `testRejectingReceiverRollsBackMintAndTrade`, `testReceiverCallbacksCannotReenterOrChangeListings`, `testPropagatedReentryFailureRollsBackOuterOperation` | PASS: las cuatro operaciones protegidas; callbacks ven propietario/valor preparados y publicación limpia; errores propagados revierten. |
| Metadatos y bloqueo de transferencias | Plantilla: tres transferencias bloqueadas; Módulo 3 temas 11 y 16–21 y Módulo 4 temas 7–10: metadatos/IPFS | [CCNFTMetadata.t.sol](../test/CCNFTMetadata.t.sol): ocho pruebas; Operaciones: `testAllPublicTransfersBlockedEvenWithApproval` | PASS: permisos, URI común, eventos, actualización, reventa, IDs quemados/inexistentes y tres variantes bloqueadas incluso con aprobación NFT. Las unitarias no descargan IPFS. |
| BUSD y financiación del ejercicio | Contrato BUSD entregado; Módulo 4 ERC20 | [BUSD.t.sol](../test/BUSD.t.sol): `testMetadata`, `testInitialSupplyBelongsToDeployer` | PASS: 18 decimales, nombre/símbolo y suministro inicial de 10 millones al desplegador. |
| Gas y tamaño de listas/lotes | Módulo 3 temas 5 y 5-1/2/3: gas y almacenamiento; plantilla: búsqueda lineal | [Reporte agregado nuevo](evidence/system-validation-2026-11-15/gas-report.txt); `tools/measure-gas.py`: listas 1/10/100 y lotes 1/10 | PASS en CI: [35 mediciones nuevas](evidence/ci-validation-43748041038-1/ci/gas-scenarios.json), coincidentes con las históricas. El [bloqueo local previo](evidence/system-validation-2026-11-15/gas-matrix.txt) se conserva como antecedente; control satisfecho para el cierre. |

`_assertAccounting` compara `totalValue` con la suma de nominales en circulación, comprueba enumeración por propietario y ausencia de custodia en CCNFT. Las pruebas críticas también comprueban saldos y autorizaciones finitas; los eventos se contrastan con emisor, campos indexados y datos.

## Recorrido económico comprobado

`testAcceptanceBalancesEventsAndFinalNominal` usa el 2 % de compra, el 1 % de reventa y el 5 % de beneficio. A compra dos NFTs de 100 BUSD por 204, publica uno a 120, B paga 121,2 y reclama 105. A conserva el segundo NFT. Las aprobaciones exactas de A (204), B (121,2) y colector (105) quedan consumidas.

| Cuenta o estado | Resultado final |
| --- | ---: |
| Variación de A | −84 BUSD |
| Variación de B | −16,2 BUSD |
| Variación del colector de fondos | +95 BUSD |
| Variación del colector de comisiones | +5,2 BUSD |
| Nominal vigente (`totalValue`) | **100 BUSD** |
| Suministro vigente | 1 NFT, propiedad de A |

Las variaciones monetarias suman cero. El beneficio sale del colector: no se genera BUSD al reclamar. El ID reclamado pierde valor/publicación y deja de existir; la enumeración conserva el otro ID.

## Cobertura y advertencias

El [resumen con localización de ramas](evidence/system-validation-2026-11-15/coverage-summary.txt) y el [reporte completo](evidence/system-validation-2026-11-15/coverage.txt) conservan CCNFT en líneas 122/122, sentencias 116/116, funciones 25/25 y ramas 79/81 (97,53 %). El control `--check-baseline` exige cobertura completa de las tres primeras métricas y al menos 79 de las 81 ramas; una variación del total obliga a revisar la justificación.

Las únicas ramas sin hits son los rechazos de `trade` en las líneas 110 y 111 por token de fondos o colector de comisiones cero. `trade` exige antes un NFT existente; solo `buy` emite y exige ambas direcciones configuradas. Sus setters impiden volver a cero. Por tanto, esos rechazos son inalcanzables mediante la interfaz pública actual. Se conservan las guardas defensivas; no se manipula almacenamiento ni se modifican contratos para forzarlas. La [revisión histórica](ci-validation-2026-11-15.md) mantiene el razonamiento original.

Se comprobaron los retornos de todas las transferencias y aprobaciones ERC20 de preparación de pruebas, incluido el receptor adversario, y las dos pruebas de consulta de BUSD se declararon `view`. La [compilación nueva](evidence/system-validation-2026-11-15/build.txt) ya no informa esas advertencias; mantiene tres notas de estilo de Forge sobre inicialización de struct y nombres en el mock. Los contratos de `src/` permanecen idénticos al commit base. El nuevo `require` del constructor del receptor agrega ramas del mock; el porcentaje total de auxiliares cambia, sin regresión de CCNFT.

## Revisión del cierre de fase 4

La [comparación nueva](evidence/phase4-recheck-2026-11-15/review.json) confirma los SHA-256 de ambos archivos, CIDs/URIs del manifiesto y coincidencia de bytes con las cuatro copias históricas conservadas. También se decodificaron ambos CIDs raw y se comprobó que sus digests SHA-256 coinciden con los archivos locales; la comparación conserva los bytes decodificados y el método. El manifiesto, los recursos y la evidencia anterior no se sobrescribieron.

Se reintentó la recuperación por Pinata y Filebase y la resolución de URI en Anvil sin `--record`, en un directorio separado. El [intento nuevo](evidence/phase4-recheck-2026-11-15/attempt/result.json) terminó con código 1: cuatro errores DNS (`Name or service not known`) y Anvil bloqueado al crear un socket (`Operation not permitted`). No hubo nuevas descargas ni nuevas comprobaciones ejecutadas en Anvil.

La fase 4 conserva su cierre histórico: [cuatro HTTP 200, bytes coincidentes y cinco comprobaciones en Anvil](evidence/ipfs-publication-verified-2026-11-15.json), más la [confirmación de ambos workflows por el usuario](evidence/ci-runs-received-2026-11-15.json). Esta revisión no inspeccionó sus logs remotos ni acredita disponibilidad IPFS actual. Los fallos nuevos corresponden al entorno y se conservan separados de los resultados históricos.

## Reproducción y alcance del cierre

Desde la raíz del repositorio, con las dependencias fijadas:

```bash
bash tools/setup.sh
python3 tools/validate-system.py
```

Cada ejecución crea un directorio nuevo bajo `.tools/validation/<fecha-UTC>/` y devuelve 1 si cualquier control falla o queda omitido por un requisito fallido. También acepta `--output-dir <directorio-nuevo>`; rechaza directorios existentes. Continúa los controles independientes después de un fallo, conserva el informe progresivamente y restaura la compilación optimizada tras cobertura y antes de medir gas. No copia una matriz anterior si falla la nueva. El `status: pending` del JSON de metadatos en modo local significa que ese modo no comprueba publicación/Anvil; su comando de validación local devuelve correctamente 0.

El workflow **Validar contratos** conserva `contracts-validation-<run_id>-<run_attempt>` con los logs de instalación y el directorio `ci/`, incluso ante fallos. Incluye pruebas, cobertura debug/resumen, reporte agregado, códigos, commit, diff, revisiones y hashes. Si la matriz termina, adjunta también su JSON. Las seis pruebas nuevas de herramientas verifican que se detecten regresiones, se conserven errores y se rechace sobrescribir evidencia. El workflow IPFS sigue siendo manual y conserva sus propios artefactos.

**Cierre de fase 5 satisfecho:** se revisó el artefacto del workflow actualizado sobre `d7a17d9`, con suite sin fallos/omisiones, cuatro fuzz de 256, umbral de cobertura aprobado y 35 transacciones exitosas con versiones/revisiones fijadas. Enlace, SHA y resultados quedan registrados arriba. No quedan controles pendientes de fase 5 dentro del alcance académico y del rango medido. El gas de búsquedas es O(publicaciones), y el reclamo alcanza O(lote × publicaciones); el lote de demostración sigue en 10. El rango medido no establece cotas para listas mayores a 100, otros ERC20 o receptores contrato.

La [nueva comprobación de fase 5](evidence/phase5-recheck-2026-11-15/review.json) confirmó los 24 hashes de evidencia, los 20 controles aprobados y las fuentes originales. La fase 6 quedó completada al revisar dos recorridos reales en redes Anvil nuevas: 52 recibos exitosos y 838 comprobaciones aprobadas. Ver [guía de demostración](local-demo.md) y [evidencia del cierre](local-demo-validation.md). Sepolia y MetaMask continúan en fase 7.
