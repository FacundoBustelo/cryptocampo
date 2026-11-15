# Publicar y comprobar los metadatos

Estado al 15/11/2026: **publicación y resolución verificadas**. El usuario ejecutó `python3 tools/verify-metadata.py --independent-gateway filebase --record` y obtuvo `status: verified`, con cuatro respuestas HTTP 200 y las cinco comprobaciones de Anvil aprobadas. El agente contrastó las copias recuperadas con los archivos locales y revisó el render del SVG. Ver [el resultado y sus límites](ipfs-verification-2026-11-15.md), [el informe completo](evidence/ipfs-publication-verified-2026-11-15.json) y [el manifiesto](ipfs-publication.json).

El pinning de ambos archivos se conserva documentado mediante la captura y la confirmación de las subidas públicas del usuario a Pinata. Las fechas se registraron con precisión de día cuando no se conocía la hora. Los hashes SHA-256, los CIDs y las URIs definitivas están registrados. El fallo anterior de `ipfs.io` por HTTP 429 permanece como evidencia histórica y no se convirtió en éxito.

Los contratos y sus reglas económicas se conservan. La presentación en una billetera y Sepolia quedan para fases posteriores. La repetición remota de ambos workflows de GitHub Actions permanece pendiente de registrar; seleccionar `filebase` como operador independiente en el verificador manual.

## 1. Validar antes de subir

Desde la raíz de `cryptocampo/`:

```bash
python3 tools/verify-metadata.py --local-only
python3 -m unittest discover -s tools -p 'test_verify_metadata.py' -v
sha256sum assets/certificate.svg assets/metadata.json
```

`--local-only` valida los hashes registrados, la sintaxis SVG y las tres claves del JSON sin acceder a la red ni ejecutar Foundry. Si ya hay un CID de imagen registrado, exige también que `image` sea su URI IPFS y que la descripción no mencione pruebas locales. Código 0 significa que pasó esta comprobación local; el estado de publicación sigue siendo `pending`.

## 2. Subir primero la imagen

Desde la cuenta del usuario en Pinata, subir **solo** `assets/certificate.svg` seleccionando **IPFS público**, como archivo individual y sin carpeta contenedora. Compartir únicamente su CID público y la confirmación de que figura fijado en Pinata. El agente no necesita tokens ni credenciales. Ver [subidas públicas de Pinata](https://docs.pinata.cloud/files/uploading-files).

Completar `resources.image` del manifiesto con datos reales:

| Campo | Valor que se registra |
| --- | --- |
| `cid` | CID entregado por Pinata para el archivo individual. |
| `uri` | `ipfs://` seguido de ese CID, sin nombre de archivo ni ruta. |
| `published_at` | Fecha y hora reales de subida, en ISO 8601 con zona horaria, si se conocen. |
| `published_on` | Fecha `YYYY-MM-DD` cuando la evidencia solo muestra el día; dejar `published_at` en `null`. |
| `pinning.status` | `confirmed_by_user` solo después de la confirmación del usuario. |
| `pinning.confirmed_at` | Fecha de la confirmación, en ISO 8601 con zona horaria. |
| `pinning.evidence` | Declaración del usuario o ruta de una captura pública que confirme el pin. |

Se admiten los CIDs usuales de Pinata: CIDv0 o CIDv1 base32 con SHA-256 y codec raw/dag-pb. Un CID de carpeta no sirve para este procedimiento: el verificador recupera el CID sin añadir rutas y exige los bytes exactos del SVG.

```bash
python3 tools/verify-metadata.py --image-only --record
```

Este paso comprueba la imagen mediante [el gateway público de Pinata](https://knowledge.pinata.cloud/en/articles/6297294-public-gateways-vs-dedicated-gateways) y [`ipfs.io`](https://docs.ipfs.tech/concepts/public-utilities/), que tiene un operador independiente. Ambos deben devolver exactamente el archivo local. Los enlaces efectivamente comprobados, fecha, estado HTTP, URL tras redirecciones y SHA-256 se guardan en `verification.resources.image.gateways`.

Código 0 en este modo acredita solo la recuperación de la imagen y la confirmación registrada de pinning; `image_publication` será `verified` y el estado global continuará `pending`. Código 1 identifica el recurso afectado. No se sustituye un CID ni se omite un gateway si falla. Un HTTP 429 se registra con su código y, si el servidor lo proporciona, `Retry-After`; el script no insiste automáticamente.

## 3. Revisar la imagen recuperada y finalizar el JSON

Abrir `.tools/metadata-verification/0/certificate.svg` y comprobar que el título, el texto de demostración y la imagen se presentan correctamente. Usar el archivo recién descargado por el verificador; la revisión del SVG local no acredita recuperación pública.

Registrar en `visual_review`:

- `status`: `verified` tras la revisión efectiva.
- `reviewed_by`: persona o agente que revisó la imagen.
- `reviewed_at`: fecha ISO 8601 con zona horaria.
- `sha256`: hash de la imagen recuperada, igual al de `resources.image`.
- `evidence`: descripción de lo observado y, si existe, ruta de la captura.

Actualizar `assets/metadata.json` conservando el nombre y esta descripción:

> Certificado de demostración del proyecto académico CryptoCampo NFT. Ficha común a todos los NFTs; no acredita existencias físicas verificadas. El nominal y la propiedad se consultan en el contrato.

Establecer `image` como `ipfs://` seguido del CID real y comprobado de la imagen. Mantener solo `name`, `description` e `image`, sin IDs ni nominales individuales. Actualizar `resources.metadata.sha256` con el resultado real de `sha256sum assets/metadata.json`; no reutilizar el hash del borrador.

Volver a ejecutar `--local-only` antes de subir el JSON. Si el verificador muestra diferencias de hash, comprobar qué archivo cambió antes de actualizar el registro.

## 4. Publicar el JSON definitivo

Subir `assets/metadata.json` a Pinata también como archivo individual, en IPFS público y sin carpeta contenedora. Registrar su CID, URI, fecha y confirmación de pinning en `resources.metadata`, con los mismos campos que la imagen.

**Mantener fijados ambos archivos.** Publicar o fijar el JSON no sustituye el pinning de la imagen enlazada mediante una cadena `ipfs://`. Una descarga satisfactoria tampoco prueba el pinning de la cuenta; esa confirmación procede del usuario. Ver [persistencia mediante pinning](https://docs.ipfs.tech/how-to/pin-files/).

## 5. Comprobar la URI definitiva en Anvil

```bash
bash tools/setup.sh
python3 tools/verify-metadata.py --record
```

El verificador descarga imagen y JSON por ambos gateways, compara los cuatro resultados byte por byte con los archivos locales, comprueba hashes, sintaxis y la referencia `image`. La comprobación de la URI compila con Forge e inicia un Anvil temporal, aunque un gateway haya fallado, vinculado a `127.0.0.1`, en un puerto disponible, chain ID 31337 y Paris. No usa RPC externo ni claves privadas del usuario. El proceso temporal se termina incluso si falla una comprobación.

Despliega BUSD y CCNFT, configura nominales de 100 y 500 BUSD, lote máximo 10, límite 10.000 BUSD, comisiones de 2 % y 1 % y beneficio de 5 %. Distribuye saldo a los dos compradores y configura autorizaciones ERC20 para compradores y colector. El administrador establece exactamente la URI publicada del JSON, y se comprueba:

1. Dos NFTs vigentes devuelven esa misma URI, sin sufijos ni IDs añadidos.
2. Tras publicar uno por 120 BUSD y revenderlo, cambia su propietario y ambos conservan la URI.
3. Tras reclamar y quemar el NFT revendido, `tokenURI(0)` revierte con `Token does not exist`.
4. `tokenURI(999)` revierte con el mismo motivo.
5. Un tercero no puede modificar la URI: la llamada revierte con `Ownable: caller is not the owner` y el NFT restante conserva la cadena publicada.

El informe conserva direcciones temporales, hashes de transacciones, versiones, revisiones de bibliotecas y comprobaciones realizadas. Los rechazos se verifican mediante `eth_call` y su motivo ABI exacto; un fallo de conexión no cuenta como reversión correcta. Las direcciones y transacciones de esta prueba pertenecen exclusivamente al Anvil efímero.

El modo completo devuelve código 0 y estado `verified` solo si pasan las comprobaciones públicas y de Anvil, consta el pinning de ambos archivos y está registrada la revisión visual de la imagen recuperada. La evidencia de billetera permanece pendiente y no condiciona ese resultado de esta fase.

La falta de una fecha de publicación se registra como pendiente sin impedir descargar un CID válido. Si falta un CID, falla un gateway, cambia un archivo, falta pinning o hay un error en Anvil, devuelve código 1 y estado `pending`, con el recurso o comprobación afectado. No reutiliza un éxito anterior. `--record` actualiza `verification` con el último intento, también cuando falla. No modifica los archivos publicados ni inventa CIDs, fechas o confirmaciones.

Para comprobar explícitamente otro operador cuando `ipfs.io` devuelve 429:

```bash
python3 tools/verify-metadata.py --independent-gateway filebase --record
```

Esta opción conserva Pinata como primer gateway y selecciona el [gateway público de Filebase](https://filebase.com/docs/ipfs/concepts/what-is-an-ipfs-gateway) como segundo operador. Mantiene los mismos CIDs y exige dos descargas coincidentes para cada recurso; no realiza fallback automático. La evidencia anterior de `ipfs.io` con HTTP 429 permanece versionada. No sustituir `ipfs.io` por `dweb.link` como solución a ese límite: [comparten infraestructura y límites](https://docs.ipfs.tech/concepts/public-utilities/).

Para completar únicamente la prueba del contrato, sin nuevas solicitudes IPFS:

```bash
python3 tools/verify-metadata.py --anvil-only --record
```

Valida los archivos locales y las dos referencias IPFS registradas antes de ejecutar Anvil. Guarda el informe en `.tools/metadata-verification/anvil/result.json` y `anvil_verification` del manifiesto. Conserva `verification` y las descargas anteriores. Código 0 significa que pasó la prueba de Anvil; el estado global continúa `pending` porque este modo no verifica disponibilidad ni pinning. El modo completo también intenta Anvil aunque un gateway falle, y conserva ese fallo como pendiente de publicación.

## 6. Ejecutar los workflows y conservar evidencia

El workflow habitual **Validar contratos** conserva compilación, formato, pruebas unitarias/fuzz, cobertura, reporte de gas y medición por escenarios. Añade la validación local y las pruebas sin red del verificador. Las pruebas Solidity siguen usando referencias locales.

Con los cambios publicados en GitHub y el manifiesto completo, ejecutar también **Verificar publicación IPFS y URI en Anvil** desde Actions → Run workflow. Este segundo workflow permite elegir explícitamente `ipfs.io` o `filebase` como operador independiente y solo tiene `workflow_dispatch`; no descarga recursos IPFS en cada push o PR. Adjunta `metadata-verification-<run_id>` con el informe y los archivos recuperados, incluso si el verificador falla. No escribe al repositorio ni altera la confirmación de pinning. Descargar el artefacto y registrar el enlace del run observado en la evidencia final.

Para repetir localmente los controles de contratos, una vez instalado el entorno:

```bash
.tools/bin/forge build
.tools/bin/forge fmt --check
.tools/bin/forge test -vv
.tools/bin/forge coverage --report summary --report debug --color never
.tools/bin/forge test --gas-report
.tools/bin/forge build --force
python3 tools/measure-gas.py
```

La [evidencia local de esta implementación](metadata-validation-2026-11-15.json) distingue pruebas del verificador de comprobaciones reales pendientes. La instalación inicial del agente falló por DNS y la primera compilación por restricciones de escritura. El usuario instaló después el entorno y ejecutó satisfactoriamente el verificador completo. Los controles generales posteriores pasaron salvo la repetición de gas por escenarios, bloqueada por permisos de sockets en la sesión del agente. La ejecución EVM de la URI sí está acreditada por el informe completo del usuario. La nueva ejecución remota de CI sigue pendiente; ver [resultado y límites actuales](ipfs-verification-2026-11-15.md).
