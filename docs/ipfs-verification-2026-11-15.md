# Publicación y resolución verificadas

La ejecución del usuario de `python3 tools/verify-metadata.py --independent-gateway filebase --record` terminó con `status: verified` y sin pendientes del verificador. El informe comenzó a las 04:53:43 UTC del 15/11/2026 y completó la prueba de Anvil a las 04:54:06 UTC. Se conserva [el JSON completo del resultado](evidence/ipfs-publication-verified-2026-11-15.json) y [el registro de publicación](ipfs-publication.json).

## Recursos y recuperación pública

| Recurso | CID del archivo individual | SHA-256 de los bytes |
| --- | --- | --- |
| `certificate.svg` | `bafkreidkykrr5euk77wd3srhwatez6bfrkre5jv775mjggz6wx6sihrhd4` | `6ac2a31e928affec3dca27b0264cf8258aa24ea6bfff58931b3eb5fd241e271f` |
| `metadata.json` | `bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4` | `e965940afe67aebb83c9d2011905d5bd69046c0caa7140af8d7dc917bcd2dd9f` |

Los dos archivos se recuperaron tanto por `gateway.pinata.cloud` como por `ipfs.filebase.io`. Las cuatro respuestas fueron HTTP 200 y sus bytes y hashes coinciden con los archivos locales. El agente volvió a comparar las cuatro copias recuperadas en el workspace. El JSON contiene únicamente `name`, `description` e `image`, conserva el carácter de demostración y referencia la imagen con su URI IPFS real, sin nominales ni IDs individuales.

Se validó la sintaxis SVG y se abrió el render de la imagen recuperada a 1200 × 800: título, textos, espiga y campos se presentan correctamente. Se conserva [la imagen de evidencia](evidence/ipfs-certificate-preview-2026-11-15.png).

La confirmación de pinning procede de las subidas públicas del usuario a Pinata: captura de `certificate.svg` en Files/Public y confirmación textual de `metadata.json` en Files/Public. Se registraron las fechas de subida con precisión de día, 15/11/2026, y las fechas de confirmación. Las descargas acreditan recuperación; la evidencia del pinning se conserva por separado. Ambos archivos deben mantenerse fijados.

El intento anterior a través de `ipfs.io` respondió HTTP 429 y no se declaró satisfactorio. [Ese resultado permanece registrado](evidence/ipfs-pinata-verified-ipfsio-429-2026-11-15.json). La ejecución satisfactoria seleccionó explícitamente Filebase como segundo operador; mantuvo los mismos CIDs.

## URI definitiva y Anvil

```text
ipfs://bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4
```

El verificador desplegó BUSD y CCNFT en un Anvil temporal, chain ID 31337 y Paris, y configuró esa cadena mediante el propietario. Se registraron 25 transacciones exitosas de despliegue, configuración y operaciones, además de las consultas. Aprobaron las cinco comprobaciones:

1. Dos NFTs vigentes devuelven exactamente la misma URI publicada.
2. La reventa cambia el propietario y conserva la URI compartida.
3. Consultar el NFT quemado revierte con `Token does not exist`.
4. Consultar el ID inexistente 999 revierte con el mismo motivo.
5. Un tercero no puede cambiar la URI: revierte con `Ownable: caller is not the owner`, y el NFT restante conserva la cadena original.

El informe incluye direcciones temporales y hashes de transacciones. No son direcciones ni transacciones de Sepolia. El proceso temporal terminó al finalizar la prueba.

El entorno registrado coincide con el fijado: Forge y Anvil 1.4.4, OpenZeppelin en `a5445b0afb8b350417b6e6ab3160554967bc151f` y forge-std en `77041d2ce690e692d6e03cc812b57d1ddaa4d505`. Los artefactos se contrastaron contra Solidity 0.8.19, optimizador habilitado con 200 runs y Paris. Se utilizaron los parámetros de demostración existentes.

## Controles generales y alcance

Después de la ejecución del usuario se repitieron los controles disponibles en la sesión del agente. La [evidencia de controles generales](evidence/contracts-checks-2026-11-15.json) registra:

- Validación local y 20 pruebas del verificador: satisfactorias.
- Formato y recompilación forzada: satisfactorios.
- Seis suites Solidity, 48 pruebas aprobadas, cero fallos y cero omisiones; incluye cuatro fuzz de 256 casos.
- Cobertura: CCNFT con 100 % de líneas, sentencias y funciones, y 97,53 % de ramas (79/81). Los dos rechazos defensivos de `trade` restantes ya están justificados en la revisión de fase 3.
- Reporte agregado de gas: satisfactorio.
- Repetición de `tools/measure-gas.py`: bloqueada al crear un socket, con `PermissionError: Operation not permitted` en la sesión del agente. No se generan nuevas cifras de esa matriz; se conserva la evidencia previa de 35 transacciones de fase 3.

La compilación terminó con advertencias de mutabilidad en dos pruebas BUSD, avisos de retornos ERC20 sin comprobar en auxiliares/pruebas y notas de estilo. No impidieron la compilación ni la verificación. No se declara una compilación sin advertencias ni se modifican contratos o reglas económicas para eliminarlas.

El resultado acreditado es **publicación y resolución verificadas** y la fase 4 queda cerrada. El usuario proporcionó los dos enlaces de GitHub Actions y confirmó que **Validar contratos** y **Verificar publicación IPFS y URI en Anvil** aparecen en verde. El resultado de CI se registra como confirmado por el usuario; el agente no pudo inspeccionar las páginas ni los logs desde esta sesión.

Ejecuciones aportadas:

- [Run 43679591874](https://github.com/FacundoBustelo/cryptocampo/actions/runs/43679591874).
- [Run 43679342774](https://github.com/FacundoBustelo/cryptocampo/actions/runs/43679342774).

La [confirmación y los enlaces originales](evidence/ci-runs-received-2026-11-15.json) conservan la procedencia del resultado. No se atribuye individualmente una URL a un workflow ni se inventan SHA, inputs o métricas de los logs remotos. Las cifras detalladas anteriores corresponden a los informes locales y del verificador del usuario; no se transcriben como cifras leídas en CI. El bloqueo de sockets fue una limitación de la sesión local del agente.

La presentación en una billetera y el despliegue en Sepolia permanecen pendientes para las fases posteriores.
