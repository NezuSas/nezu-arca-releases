# NEZU Arca · catálogo firmado — guía para agentes

## Propósito

Este repositorio distribuye releases verificables y el catálogo remoto de
plataformas. Un cambio aquí puede llegar a todos los clientes: prioriza
integridad, trazabilidad y compatibilidad.

## Estándar global

Este repositorio sigue [NEZU Engineering Standards](https://github.com/NezuSas/nezu-engineering-standards).
Las reglas de esta guía prevalecen cuando sean más específicas para releases y firma.

## Roles de trabajo

### Catálogo de plataformas

- Añade logos con `tools/add-platform.ps1` o `tools/add_platform.py`.
- Acepta solamente PNG, JPG/JPEG, WEBP o SVG legibles, de origen autorizado y con un nombre de plataforma claro.
- No edites hashes manualmente: el script calcula SHA-256 y aumenta la versión del catálogo.
- Añade varias plataformas en un solo commit cuando sea posible: una sola firma y una sola versión de catálogo.

### Seguridad y firma

- `assets/catalog.json` y `assets/catalog.json.sig` deben validarse con Ed25519.
- La clave privada vive solo en la variable de entorno `NEZU_RELEASE_PRIVATE_KEY_HEX` del equipo autorizado que firma. Nunca se guarda en Git, archivos del repositorio, logs ni conversaciones. Este repositorio no usa GitHub Actions.
- La clave pública fijada en la aplicación no se cambia sin una migración de confianza explícita.
- No publiques binarios ni metadata de actualización sin sus verificaciones criptográficas.

### Release manager

- Revisa que el repositorio esté limpio antes de modificarlo.
- Ejecuta pruebas de los scripts antes de `commit` y `push`:

  ```powershell
  python -m unittest discover -s tests -v
  ```

- Tras cualquier cambio en `assets/catalog.json` o `assets/platforms/`, firma el catálogo en local:

  ```powershell
  python .	ools\sign_catalog.py --catalog assets\catalog.json --signature assets\catalog.json.sig
  ```

- Confirma `catalog.json.sig` junto con el catálogo que firma. No declares un catálogo disponible hasta que la firma esté publicada.

### QA de distribución

- Antes de publicar, confirma que los scripts pasan pruebas, que cada recurso tiene hash y que el catálogo no contiene duplicados ni rutas inseguras.
- Tras cada push de catálogo, verifica que `assets/catalog.json.sig` corresponde al `catalog.json` publicado antes de comunicar disponibilidad.
- Para releases de la aplicación, comprueba que la metadata, firma y binario corresponden a la misma versión.

## Reglas de Git

- No sobrescribas cambios ajenos, no fuerces pushes y no elimines releases o recursos publicados.
- `commit` y `push` requieren autorización explícita del usuario.
- Sincroniza con `git pull --rebase origin main` antes de cada cambio para no pisar una firma publicada.

## Procedimiento de alta de una plataforma

1. Obtén un logo con permiso de uso y guárdalo localmente.
2. Ejecuta, por ejemplo:

   ```powershell
   .\tools\add-platform.ps1 -Name "Banco Guayaquil" -IconPath "C:\Users\ocuen\Downloads\bancoguayaquil.png"
   ```

3. Firma el catálogo con `tools/sign_catalog.py` y publica la firma.
4. Clientes con una versión compatible descargarán el catálogo firmado al tener Internet y conservarán el icono en caché para uso offline.
