# Demostración local con scripts Solidity

**Fase 6 completada con evidencia real de Anvil.** Se inspeccionaron directamente los dos recorridos ejecutados por el usuario en redes nuevas: 52 recibos exitosos y 838 comprobaciones aprobadas, con los saldos y el NFT conservado previstos. La sesión del agente continúa limitada para crear sockets; el cierre se apoya en los archivos de la ejecución real del usuario. Ver [resultados y evidencia](local-demo-validation.md). Sepolia, Etherscan y MetaMask corresponden a fase 7.

## Ejecución completa

Desde la raíz de `cryptocampo/`, con Python 3, Make y el entorno instalado:

```bash
make install
make demo
# Equivalente, con ubicación explícita que todavía no debe existir:
python3 tools/demo.py --output-dir .tools/demo/mi-ejecucion
# Controles generales, cobertura, ambos reportes de gas y dos redes de demostración:
make validate
```

`make demo` crea dos procesos Anvil consecutivos en `127.0.0.1`, con puertos libres, chain ID 31337 y Paris. Cada recorrido usa una cadena nueva. Se ejecutan los scripts con `--broadcast --slow --unlocked --sender <cuenta>`, confirmando cada transacción antes de la siguiente. No se incorporan claves privadas. El ejecutor conserva el PID propio y termina únicamente ese proceso, también ante errores. Anvil arranca con `--silent` para evitar registrar las claves de desarrollo.

El administrador y los cuatro participantes se obtienen de las primeras cinco cuentas desbloqueadas de Anvil. Los scripts rechazan redes diferentes a 31337, direcciones cero, actores contrato y actores repetidos. Antes de configurar o interactuar comprueban el bytecode completo de BUSD/CCNFT y el propietario; el ejecutor comprueba además que las cinco cuentas estén desbloqueadas, el cliente sea Anvil y la génesis coincida con la registrada. Las cuentas y las direcciones desplegadas se guardan en `result.json`. Las direcciones se extraen de los recibos de creación, sin predecir direcciones ni fijar IDs.

## Etapas independientes

En una terminal, iniciar y conservar el nodo:

```bash
make anvil
```

En otra, ejecutar en orden (cada comando conserva su propia evidencia):

```bash
make deploy
make configure
make fund
make approvals  # approve-a, approve-b y approve-funds, secuencialmente
make enable
make buy
make list
make trade
make claim
```

Las variables opcionales `RPC_URL=http://127.0.0.1:8545` y `STATE=.tools/demo-state.json` se pueden pasar a cada objetivo. `STATE` es un índice mutable que conserva actores, direcciones, bloque y etapas confirmadas; los informes de evidencia siempre se escriben en directorios nuevos. Para una nueva red se debe usar otro `STATE`. Una etapa fuera de orden falla. Un fallo posterior a una publicación puede dejar transacciones parciales: revisar el informe y comenzar otra demostración en una red nueva. El ejecutor no vuelve a enviar automáticamente operaciones incompletas. Con `--rpc-url` se usa exclusivamente el nodo existente y nunca se termina su proceso. La ejecución por etapas exige ese argumento; el recorrido completo administra sus propias redes.

El comando de cada objetivo equivale a:

```bash
python3 tools/demo.py --stage configure --rpc-url http://127.0.0.1:8545 --state .tools/demo-state.json
```

`DemoBase.sol` comparte las constantes económicas, la URI definitiva y las guardas. `Deploy.s.sol` despliega; `Configure.s.sol` configura sin habilitar; `Prepare.s.sol` financia, aprueba y habilita; `Operations.s.sol` compra, publica, revende y reclama. Todos heredan de `Script` mediante la base y cada operación tiene `run`, `startBroadcast` y `stopBroadcast`. Los scripts reciben `DEMO_ADMIN`, `DEMO_A`, `DEMO_B`, `DEMO_FUNDS`, `DEMO_FEES`, `DEMO_BUSD`, `DEMO_CCNFT` y, para aprobaciones, `DEMO_APPROVER`. El ejecutor los establece a partir del estado registrado; no hace falta editar `.env`.

## Parámetros y comprobaciones

Los nominales son 100 y 500 BUSD; compra 2 %, reventa 1 %, beneficio 5 %, lote máximo 10 y límite nominal 10.000 BUSD. La URI compartida es `ipfs://bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4`, contrastada con el registro de publicación. Python lee las constantes de `DemoBase.sol` para verificar las etapas.

Se distribuyen 1.000 BUSD a A, 1.000 a B y 10 al colector. Cada remitente aprueba su importe exacto: A 204 BUSD, B 121,2 y colector 105. Las habilitaciones se publican solo después de comprobar configuración, financiación y las tres aprobaciones.

El recorrido compra dos certificados de 100, descubre sus IDs por enumeración, publica el primero a 120, lo revende a B y B reclama. El segundo permanece en A. Después de cada etapa se consulta con Cast el propietario, código de contratos, saldos, autorizaciones, parámetros, habilitaciones, suministro, nominal vigente y lista de ventas. Tras emitir también se consultan enumeración, propietarios, nominales y metadatos. Tras la reventa se exige la publicación limpia. El reclamo debe quemar el ID vendido y limpiar nominal/publicación, y las consultas de propietario y URI de ese ID deben revertir.

| Participante | Saldo tras financiación | Saldo final esperado | Variación del recorrido |
| --- | ---: | ---: | ---: |
| A | 1.000 | 916 | −84 BUSD |
| B | 1.000 | 983,8 | −16,2 BUSD |
| Fondos | 10 | 105 | +95 BUSD |
| Comisiones | 0 | 5,2 | +5,2 BUSD |

Se exige un solo NFT en A y `totalValue = 100 BUSD`. Las tres autorizaciones se consumen por completo. Los 105 BUSD restantes permiten financiar el eventual reclamo del NFT conservado, con una nueva aprobación exacta de 105 BUSD por el colector.

Para consultar manualmente, usar las direcciones del informe:

```bash
.tools/bin/cast chain-id --rpc-url http://127.0.0.1:8545
.tools/bin/cast call <CCNFT> 'owner()(address)' --rpc-url http://127.0.0.1:8545
.tools/bin/cast call <CCNFT> 'tokenOfOwnerByIndex(address,uint256)(uint256)' <A> 0 --rpc-url http://127.0.0.1:8545
.tools/bin/cast call <CCNFT> 'totalValue()(uint256)' --rpc-url http://127.0.0.1:8545
.tools/bin/cast call <BUSD> 'allowance(address,address)(uint256)' <fondos> <CCNFT> --rpc-url http://127.0.0.1:8545
```

## Evidencia y aceptación

Cada recorrido conserva `result.json`, comandos y códigos de salida, logs, versiones de Forge/Cast/Anvil, commit/diff, revisiones y estado de dependencias, hashes de fuentes (incluidos scripts y Makefile), actores, direcciones, hashes de transacciones, recibos completos, archivos de broadcast y comparaciones entre estado observado y esperado. Si Forge falla después de publicar, se intenta conservar igualmente el broadcast y sus recibos parciales. Un fallo devuelve código distinto de cero y mantiene los resultados obtenidos; los directorios existentes se rechazan para proteger la evidencia anterior.

`tools/validate-system.py` ejecuta la demostración además de compilación, formato, pruebas Solidity/Python, cobertura y ambos informes de gas. El workflow `contracts.yml` conserva todo bajo el artefacto `contracts-validation-<run_id>-<run_attempt>` incluso ante fallos. La aceptación exige revisar `result.json` y `run-{1,2}/result.json` de la demostración, obtenida localmente o bajo `ci/demo/` en el artefacto remoto: ambos recorridos deben pasar, con 26 recibos exitosos cada uno, todas las verificaciones aprobadas y las variaciones finales acordadas. El cierre local del 15/11/2026 satisface este criterio; la configuración de CI mantiene la misma exigencia para ejecuciones posteriores. Un resultado de simulación o un estado global verde sin revisar estos informes no reemplaza esa comprobación.

La prueba de scripts agrupa 15 escenarios con snapshots de estado: configuración, cadena/actores/código/propietario incorrectos, financiación/aprobaciones/etapas faltantes, repeticiones y composición del recorrido. Se agrupan en una prueba porque `vm.setEnv` modifica el entorno global del proceso; ejecutarlos por separado en paralelo produce interferencias. Las pruebas Python verifican la conservación de fallos, el ciclo de vida de procesos, las restricciones del RPC, recibos parciales y detección de estados finales incorrectos. La cobertura exigida sigue siendo la de CCNFT: 100 % de líneas, sentencias y funciones y al menos 79/81 ramas, con las dos guardas inalcanzables ya justificadas en fase 5.

## Fundamento académico

Se releyeron los apuntes locales del módulo 3: tema 8 para despliegue con scripts y análisis de transacciones; tema 9 para consultas con `cast call`; tema 14 para `Script`, `run`, `startBroadcast` y `stopBroadcast`; tema 21 para agrupar despliegues e interacciones mediante Makefile. Las cuentas desbloqueadas de Anvil permiten aplicar esos conceptos sin copiar claves privadas en comandos ni archivos. El apunte escribe «Mikefile»; el archivo correcto es `Makefile`. IPFS conserva los metadatos fuera de la cadena. La publicación real se acredita mediante recibos y consultas al nodo; una ejecución local de Forge por sí sola no cierra esta fase.
